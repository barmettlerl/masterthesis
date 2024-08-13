import logging
from typing import List
import scipy as sp
import numpy as np
import datetime as dt
import os

from canary_tester.config_loader.schema import SingleTestConfigType
from canary_tester.types import (
    GlobalConfig,
    TesterReturn,
    TesterReturnReason,
    TesterReturnType,
    VersionEnrichedStandardScalarMetric,
)
from canary_tester.version_enricher import VersionEnricher
from canary_tester.tester.statistic_tests import BaseStatisticTest


logger = logging.getLogger("root")


class Tester:
    """
    Base class for predictable arrival and unpredictable arrival tester.

    Parameters:
    version_under_test: str
        The patch version of the test group. The devices with the new updated loaded.
    total_peeks: int
       The total number of times we want to peek the data.
    control_group_versions: List[str]
        The list of versions that are in the control group.
    enricher: VersionEnricher
        The version enricher.
    test_config: SingleTestConfigType
        The config for the test.
    """

    __test__ = False
    _version_under_test: str
    name: str
    _test_config: SingleTestConfigType
    _current_peek: int
    _total_peeks: int
    _control_group_versions: List[str]
    _treatment_group: list[VersionEnrichedStandardScalarMetric]
    _control_group: list[VersionEnrichedStandardScalarMetric]
    _enricher: VersionEnricher
    _statistic_test: BaseStatisticTest
    _global_config: GlobalConfig

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
        self._version_under_test = version_under_test
        self._total_peeks = total_peeks
        self._enricher = enricher
        self._treatment_group = []
        self._control_group = []
        self._current_peek = 1
        self._control_group_versions = control_group_versions
        self._test_config = test_config
        self.name = test_config["name"]
        self._statistic_test = statistic_test
        self._global_config = global_config

    def run(self, previous_timestamp: int, current_timestamp: int) -> TesterReturn:
        pass

    def _select_alpha_gst_obrien_fleming(
        self, current_peek: int, total_peeks: int, alpha: float, rho: float = 0.5
    ):
        """
        Select the alpha value for the O'Brien-Fleming spending function.
        The paper to it can be found here:
        https://www.jstor.org/stable/2530245

        Parameters:
        current_peek: int
            The current peek we are at (between 1 an total_peeks)
        total_peeks: int
            The total number of peeks we want to do
        alpha: float
            The alpha value
        rho: float
            The rho value. Having rho=0.5 seems like the optimal
            https://www.jstor.org/stable/2531959
        """

        t = current_peek / total_peeks

        return 4 - 4 * sp.stats.norm.cdf(
            sp.stats.norm.ppf(1 - alpha / 4) / t ** (rho / 2)
        )

    def _analyze(
        self,
        a_bucket: list[float],
        b_bucket: list[float],
        current_timestamp: int,
        current_peek: int,
        total_seconds_passed: float,
    ) -> TesterReturn:
        """
        We conduct the test here. And make the decision based on
        the test results.

        1. We check if the effect size is above the minimal effect size of interest
        2. We check if the p_value_h0 is below the alpha value (we reject the null hypothesis)
        3. We check if the p_value_h1 is below the alpha value (we reject the alternative
            hypothesis)
        4. If none of the above is true we continue the test.
        """

        alpha = self._select_alpha_gst_obrien_fleming(
            current_peek,
            self._total_peeks,
            self._test_config["significance_level"],
        )
        effect_size_ci_low, effect_size_ci_high = self._statistic_test.effect_size_ci(
            a_bucket, b_bucket, alpha
        )
        p_value_h0 = self._statistic_test.p_value(
            a_bucket,
            b_bucket,
            alternative="greater",  # means that alternative hypothesis is that a is greater than b
        )
        p_value_h1 = self._statistic_test.p_value(
            a_bucket,
            b_bucket,
            alternative="less",
        )

        logger.debug({
            "name": self.name,
            "time": dt.datetime.fromtimestamp(current_timestamp).strftime(
                "%m/%d/%Y, %H:%M:%S"
            ),
            "control_sample_size": len(self._control_group),
            "treatment_sample_size": len(self._treatment_group),
            "direction": self._test_config["direction"],
            "mean_a": np.mean(a_bucket),
            "mean_b": np.mean(b_bucket),
            "effect_size_ci_low": effect_size_ci_low,
            "effect_size_ci_high": effect_size_ci_high,
            "effect_size_threshold": self._test_config[
                "minimal_effect_size_of_interest"
            ],
            "p_value_h0": p_value_h0,
            "p_value_h1": p_value_h1,
            "alpha": alpha,
            "current_peek": current_peek,
            "total_peek": self._total_peeks,
        })

        if self._is_lower_than_minimal_effect_size_of_interest(
            self._test_config["minimal_effect_size_of_interest"],
            effect_size_ci_low,
            effect_size_ci_high,
        ):
            reason = TesterReturnReason.EFFECT_SIZE_UNDER_THRESHOLD
        elif p_value_h0 < alpha:
            reason = TesterReturnReason.WORSE
        elif p_value_h1 < alpha:
            reason = TesterReturnReason.BETTER
        else:
            reason = TesterReturnReason.COULD_NOT_MAKE_DECISION

        if not os.path.exists("results"):
            os.makedirs("results")
            with open(f"results/{self.name}.csv", "w") as f:
                f.write(
                    "total_min_passed,control_sample_size,treatment_sample_size,mean_a,mean_b,effect_size_ci_low,effect_size_ci_high,effect_size_threshold,p_value_h0,p_value_h1,alpha,reason\n"
                )
        # store into csv file into folder results
        with open(f"results/{self.name}.csv", "a") as f:
            f.write(
                f"{np.ceil(total_seconds_passed / 60)},{len(a_bucket)},{len(b_bucket)},{np.mean(a_bucket)},{np.mean(b_bucket)},{effect_size_ci_low},{effect_size_ci_high},{self._test_config['minimal_effect_size_of_interest']},{p_value_h0},{p_value_h1},{alpha},{reason.value}\n"
            )

        if self._is_lower_than_minimal_effect_size_of_interest(
            self._test_config["minimal_effect_size_of_interest"],
            effect_size_ci_low,
            effect_size_ci_high,
        ):
            return TesterReturn(
                name=self.name,
                type=TesterReturnType.TERMINATION,
                reason=TesterReturnReason.EFFECT_SIZE_UNDER_THRESHOLD,
            )

        if p_value_h0 < alpha:
            return TesterReturn(
                name=self.name,
                type=TesterReturnType.TERMINATION,
                reason=TesterReturnReason.WORSE,
            )

        if p_value_h1 < alpha:
            return TesterReturn(
                name=self.name,
                type=TesterReturnType.TERMINATION,
                reason=TesterReturnReason.BETTER,
            )

        return TesterReturn(
            name=self.name,
            type=TesterReturnType.CONTINUE,
            reason=TesterReturnReason.COULD_NOT_MAKE_DECISION,
        )

    def _verify_if_in_valid_version(
        self, metric: VersionEnrichedStandardScalarMetric
    ) -> bool:
        if self._version_under_test == metric.version:
            return True
        else:
            return metric.version in self._control_group_versions

    def _increase_peek(self):
        self._current_peek += 1

    def _is_lower_than_minimal_effect_size_of_interest(
        self,
        minimal_effect_size_of_interest: float,
        effect_size_ci_low: float,
        effect_size_ci_high: float,
    ):
        """
        Looks if the confidence interval does not contain the minimal effect size of interest.
        We are looking at both sides, when we measure a smaller value or when we measure a bigger
        value than before. eg. We set the minimal effect size to 0.5 than we excpect it to be either
        50% bigger or smaller -> which results in following inteval check:
        1 / 1.5 < effect_size_ci_low and 1.5 > effect_size_ci_high.
        """
        if minimal_effect_size_of_interest <= 0:
            return False

        # minimal_effect = minimal_effect_size_of_interest + 1
        # res = (
        #     1 / minimal_effect < effect_size_ci_low
        #     and minimal_effect > effect_size_ci_high
        # )
        # print(
        #     f"{1 / minimal_effect} < {effect_size_ci_low} and {minimal_effect} >"
        #     f" {effect_size_ci_high}: {res}"
        # )
        # return (
        #     1 / minimal_effect < effect_size_ci_low
        #     and minimal_effect > effect_size_ci_high
        # )

        return effect_size_ci_high < minimal_effect_size_of_interest
