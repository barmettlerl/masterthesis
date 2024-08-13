from typing import List, override
import logging
import requests
import datetime as dt
import numpy as np
import os

from canary_tester.types import (
    ComparisonDirection,
    GlobalConfig,
    StandardScalarMetric,
    TesterReturn,
    TesterReturnReason,
    TesterReturnType,
    VersionEnrichedStandardScalarMetric,
)
from canary_tester.version_enricher import VersionEnricher
from canary_tester.tester.alert_group_balancer import AlertGroupBalancer
from canary_tester.config_loader.schema import SingleTestConfigType
from canary_tester.tester.tester import Tester
from canary_tester.tester.statistic_tests import BaseStatisticTest
from canary_tester.helper import convert_timestamp_into_seconds

logger = logging.getLogger("root")


class UnpredictableArrivalTester(Tester):
    """
    A class that takes two groups(treatment and control) of hosts and tries to
    determine if there is a statistically significant difference between the two groups.
    It is assumed that the incoming data is unpredictable that means that the arrival
    time is not approximately uniformly distributed.
    """

    def __init__(
        self,
        version_under_test: str,
        total_peeks: int,
        control_group_versions: List[str],
        enricher: VersionEnricher,
        test_config: SingleTestConfigType,
        statistic_test: BaseStatisticTest,
        global_config: GlobalConfig,
    ):
        super().__init__(
            version_under_test=version_under_test,
            total_peeks=total_peeks,
            control_group_versions=control_group_versions,
            enricher=enricher,
            test_config=test_config,
            statistic_test=statistic_test,
            global_config=global_config,
        )

    def _fetch(
        self, previous_timestamp: int, current_timestamp: int
    ) -> dict[str, StandardScalarMetric]:
        params = {
            "query": self._test_config["query"],
            "start": previous_timestamp,
            "end": current_timestamp,
            "dedup": "true",
            "partial_response": "true",
            "max_source_resolution": "auto",
            "engine": "thanos",
            "analyze": "false",
            "step": "60",  # This seems the time window where a alert metric is send
        }

        res = requests.get(
            self._global_config.THANOS_QUERIER_ENDPOINT + "/api/v1/query_range",
            params=params,
            cookies={"_oauth2_proxy_osdp_open_ch": self._global_config.AUTH_COOKIE},
            verify=self._global_config.VERIFY_SSL,
        )

        res.raise_for_status()

        res = res.json()

        metrics: dict[str, StandardScalarMetric] = {}
        for el in res["data"]["result"]:
            # If we have ALERTS_FOR_STATE and we have as value the moment when the alert appeared
            if (
                int(el["values"][0][1]) >= previous_timestamp
                and int(el["values"][0][1]) < current_timestamp
                and hash(frozenset(el["metric"].items())) not in metrics
            ):
                metrics[hash(frozenset(el["metric"].items()))] = StandardScalarMetric(
                    int(el["values"][0][0]), el["metric"]["host"], 0
                )

            # For all other cases we assume value 1
            if (
                int(el["values"][0][1]) == 1
                and hash(frozenset(el["metric"].items())) not in metrics
            ):
                metrics[hash(frozenset(el["metric"].items()))] = StandardScalarMetric(
                    int(el["values"][0][0]), el["metric"]["host"], 0
                )

        return metrics

    def _calculate_second_diff(
        self,
        a: VersionEnrichedStandardScalarMetric,
        b: VersionEnrichedStandardScalarMetric,
    ) -> float:

        return (
            dt.datetime.fromtimestamp(a.ts) - dt.datetime.fromtimestamp(b.ts)
        ).total_seconds()

    def _apply_new_data_chunk(
        self, new_data_chunk: List[VersionEnrichedStandardScalarMetric]
    ):

        for metric in new_data_chunk:

            if metric.version == self._version_under_test:
                if self._treatment_group != []:
                    metric.value = self._calculate_second_diff(
                        metric, self._treatment_group[-1]
                    )

                self._treatment_group.append(metric)  # the first entry will be 0
            else:
                if self._control_group != []:
                    metric.value = self._calculate_second_diff(
                        metric, self._control_group[-1]
                    )

                self._control_group.append(metric)  # the first entry will be 0

    @override
    def run(
        self,
        previous_timestamp: int,
        current_timestamp: int,
        total_seconds_passed: float,
    ):
        """
        Runs the test, by fetching new data, enriching it, balancing it and then
        running the test.
        """
        current_peek = self._current_peek
        self._increase_peek()

        try:
            data = self._fetch(previous_timestamp, current_timestamp)
        except requests.exceptions.HTTPError as e:
            logging.error(e)
            return TesterReturn(
                name=self.name,
                type=TesterReturnType.CONTINUE,
                reason=TesterReturnReason.HTTP_ERROR,
            )

        enriched_data = self._enricher.enrich(list(data.values()))

        version_cleaned_data = list(
            filter(self._verify_if_in_valid_version, enriched_data)
        )

        # sort by timestamp
        version_cleaned_data.sort(key=lambda x: x.ts)

        # Unpredictable arrival needs to balance the data !!
        balanced_data = AlertGroupBalancer.balance(
            self._enricher.frequencies,
            self._version_under_test,
            self._control_group_versions,
            version_cleaned_data,
        )

        self._apply_new_data_chunk(balanced_data)

        logger.debug({
            "name": self.name,
            "control_group": len(self._control_group),
            "treatment_group": len(self._treatment_group),
        })

        if (
            len(self._treatment_group) < self._global_config.MINIMAL_SAMPLE_SIZE
            or len(self._control_group) < self._global_config.MINIMAL_SAMPLE_SIZE
        ):
            return TesterReturn(
                name=self.name,
                type=TesterReturnType.CONTINUE,
                reason=TesterReturnReason.NOT_ENOUGH_DATA,
            )

        # We want that our test group has a bigger time difference between alert message
        treatment_bucket = [
            metric.value for metric in self._treatment_group[1:]
        ]  # We skip the first element since value (ts_diff) is 0
        control_bucket = [
            metric.value for metric in self._control_group[1:]
        ]  # We skip the first element since value (ts_diff) is 0

        match ComparisonDirection.from_str(self._test_config["direction"]):
            case ComparisonDirection.Smaller:
                result = self._analyze(
                    control_bucket,
                    treatment_bucket,
                    current_timestamp,
                    current_peek,
                    total_seconds_passed,
                )
            case ComparisonDirection.Bigger:
                result = self._analyze(
                    treatment_bucket,
                    control_bucket,
                    current_timestamp,
                    current_peek,
                    total_seconds_passed,
                )

        return result
