import re
from typing import List, override
from dotenv import load_dotenv
import logging
import requests
import datetime as dt
import concurrent.futures

from canary_tester.helper import is_float_castable
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
from canary_tester.config_loader.schema import SingleTestConfigType
from canary_tester.tester.tester import Tester
from canary_tester.tester.statistic_tests import BaseStatisticTest

logger = logging.getLogger("root")

load_dotenv()


class PredictableArrivalTester(Tester):
    """
    A class that detects version changes of the hosts and then fetches the
    metrics in a range before and after the version change happened.
    Then it puts the before metrics in the control group and the after metrics
    in the treatment group and runs a statistical test on them.

    This test is intended to be used for metrics that have approximately uniform
    arrival times and are scalar values(i.e disk space, cpu usage, etc.)
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

    def _fetch_host(self, host: str, version_change_ts: float):
        before_start = (
            dt.datetime.fromtimestamp(version_change_ts)
            - dt.timedelta(
                seconds=self._global_config.PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME
                + self._global_config.PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME
            )
        ).timestamp()
        before_end = (
            dt.datetime.fromtimestamp(version_change_ts)
            - dt.timedelta(
                seconds=self._global_config.PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME
            )
        ).timestamp()

        after_start = (
            dt.datetime.fromtimestamp(version_change_ts)
            + dt.timedelta(
                seconds=self._global_config.PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME
            )
        ).timestamp()
        after_end = (
            dt.datetime.fromtimestamp(version_change_ts)
            + dt.timedelta(
                seconds=self._global_config.PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME
                + self._global_config.PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME
            )
        ).timestamp()

        try:
            before = self._avg_metric_aggregation(host, before_start, before_end)
            after = self._avg_metric_aggregation(host, after_start, after_end)
        except Exception as e:
            logger.error({
                "name": self.name,
                "host": host,
                "error": str(e),
            })
            return None, None

        return before, after

        # def _fetch(
        #     self, host_changes: list[tuple[str, float]]
        # ) -> tuple[List[StandardScalarMetric], List[StandardScalarMetric]]:
        #     old_version_metrics: list[StandardScalarMetric] = []
        #     new_version_metrics: list[StandardScalarMetric] = []

        #     with concurrent.futures.ThreadPoolExecutor() as executor:
        #         futures = [
        #             executor.submit(self._fetch_host, host, ts) for host, ts in host_changes
        #         ]
        #         for future in concurrent.futures.as_completed(futures):
        #             try:
        #                 before, after = future.result()
        #                 if before and after:
        #                     old_version_metrics.append(before)
        #                     new_version_metrics.append(after)
        #             except Exception as e:
        #                 logger.error(e)

        #     return old_version_metrics, new_version_metrics

    def _fetch(
        self, previous_timestamp, current_timestamp
    ) -> List[StandardScalarMetric]:
        params = {
            "query": self._test_config["query"],
            "dedup": "true",
            "partial_response": "false",
            "start": previous_timestamp,
            "end": current_timestamp,
            "engine": "thanos",
            "analyze": "false",
        }

        res = requests.get(
            self._global_config.THANOS_QUERIER_ENDPOINT + "/api/v1/query",
            params=params,
            cookies={"_oauth2_proxy_osdp_open_ch": self._global_config.AUTH_COOKIE},
        )

        res.raise_for_status()

        res = res.json()

        return PredictableArrivalTester._transform_to_scalar_metrics(res)

    def _avg_metric_aggregation(
        self, host: str, start: int, end: int
    ) -> StandardScalarMetric:
        """
        Requests the raw data from the thanos querier and then aggregates it to a single
        scalar value.
        """
        params = {
            "query": self._process_query(self._test_config["query"], host),
            "start": start,
            "end": end,
            "dedup": "true",
            "partial_response": "false",
            "engine": "thanos",
            "analyze": "false",
            "step": "1",
        }

        start = dt.datetime.now()

        res = requests.get(
            self._global_config.THANOS_QUERIER_ENDPOINT + "/api/v1/query_range",
            params=params,
            cookies={"_oauth2_proxy_osdp_open_ch": self._global_config.AUTH_COOKIE},
            verify=self._global_config.VERIFY_SSL,
        )

        res.raise_for_status()

        res = res.json()

        return PredictableArrivalTester._transform_to_scalar_metrics(res)

    def _process_query(self, query: str, host: str):
        """
        Select the metric on a per host basis by transforming the query.
        """
        pattern = re.compile(
            r"(\w+)\s*\((\w+(?:_\w+)*)(\{[^)]*\})?\)\s*by\s*\((\w+(?:,\s*\w+)*)\)|(\w+(?:_\w+)*)"
        )
        match = pattern.match(query)
        if match:
            if match.group(1):
                func = match.group(1)
                metric = match.group(2)
                existing_filter = match.group(3) or "{}"
                by_clause = match.group(4)

                if existing_filter == "{}":
                    return f"{func} ({metric}{{host='{host}'}}) by ({by_clause})"
                else:
                    existing_filter = existing_filter[:-1] + f", host='{host}'}}"
                    return f"{func} ({metric}{existing_filter}) by ({by_clause})"
            else:
                metric = match.group(5)
                if "{host=" in metric:
                    return query
                else:
                    return f"{metric}{{host='{host}'}}"
        else:
            return query

    # def _transform_to_scalar_metrics(json):
    #     """
    #     Takes the average of all the values in the metric and returns a
    #     StandardScalarMetric object.
    #     """
    #     metric = json["data"]["result"][0]
    #     summed_up_value = 0
    #     for e in metric["values"]:
    #         summed_up_value += float(e[1])

    #     return StandardScalarMetric(
    #         ts=int(metric["values"][-1][0]),
    #         host_name=metric["metric"]["host"],
    #         value=float(summed_up_value / len(metric["values"])),
    #     )
    def _transform_to_scalar_metrics(json):
        metrics: list[StandardScalarMetric] = []

        for el in json["data"]["result"]:
            if is_float_castable(el["value"][1]):
                metrics.append(
                    StandardScalarMetric(
                        ts=int(el["value"][0]),
                        host_name=el["metric"]["host"],
                        value=float(el["value"][1]),
                    )
                )

        return metrics

    def _apply_new_data_chunk(
        self, new_data_chunk: List[VersionEnrichedStandardScalarMetric]
    ):
        for metric in new_data_chunk:
            if metric.version == self._version_under_test:
                self._treatment_group.append(metric)
            else:
                self._control_group.append(metric)

    @override
    def run(
        self,
        previous_timestamp: float,
        current_timestamp: float,
        total_seconds_passed: float,
    ):

        current_peek = self._current_peek
        self._increase_peek()

        # start = dt.datetime.fromtimestamp(current_timestamp) - dt.timedelta(
        #     seconds=self._global_config.PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME
        #     + self._global_config.PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME
        #     + (current_timestamp - previous_timestamp)
        # )

        # end = dt.datetime.fromtimestamp(current_timestamp) - dt.timedelta(
        #     seconds=self._global_config.PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME
        #     + self._global_config.PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME
        # )

        # host_changes = self._enricher.get_host_with_changed_version_in_interval(
        #     self._version_under_test,
        #     start=start.timestamp(),
        #     end=end.timestamp(),
        # )

        try:
            data = self._fetch(previous_timestamp, current_timestamp)
        except requests.exceptions.HTTPError as e:
            logging.error(e)
            return TesterReturn(
                name=self.name,
                type=TesterReturnType.CONTINUE,
                reason=TesterReturnReason.HTTP_ERROR,
            )
        enriched_data = self._enricher.enrich(data)

        version_cleaned_data = list(
            filter(self._verify_if_in_valid_version, enriched_data)
        )

        self._apply_new_data_chunk(version_cleaned_data)

        logger.debug({
            "name": self.name,
            "control_group": len(self._control_group),
            "treatment_group": len(self._treatment_group),
        })

        if self._current_peek > self._total_peeks:
            return TesterReturn(
                name=self.name,
                type=TesterReturnType.TERMINATION,
                reason=TesterReturnReason.MAX_TIME_REACHED,
            )

        if (
            len(self._treatment_group) < self._global_config.MINIMAL_SAMPLE_SIZE
            or len(self._control_group) < self._global_config.MINIMAL_SAMPLE_SIZE
        ):
            return TesterReturn(
                name=self.name,
                type=TesterReturnType.CONTINUE,
                reason=TesterReturnReason.NOT_ENOUGH_DATA,
            )

        treatment_bucket = [metric.value for metric in self._treatment_group]
        control_bucket = [metric.value for metric in self._control_group]

        match ComparisonDirection.from_str(self._test_config["direction"]):
            case ComparisonDirection.Smaller:
                result = self._analyze(
                    treatment_bucket,
                    control_bucket,
                    current_timestamp,
                    current_peek,
                    total_seconds_passed,
                )
            case ComparisonDirection.Bigger:
                result = self._analyze(
                    control_bucket,
                    treatment_bucket,
                    current_timestamp,
                    current_peek,
                    total_seconds_passed,
                )

        return result
