from typing import override
from scipy import stats
import statsmodels.api as sm_api
import statsmodels as sm

from canary_tester.types import (
    VersionEnrichedStandardScalarMetric,
)

from canary_tester.tester.frequency_kstest_one_sided import FrequencyKSTestOneSided


class BaseStatisticTest:
    """
    Abstract Base class for all the tests.
    """

    @staticmethod
    def p_value(
        a_bucket: list[VersionEnrichedStandardScalarMetric],
        b_bucket: list[VersionEnrichedStandardScalarMetric],
        alternative: str = "less",
    ) -> float:
        """
        Returns the p-value of the test.
        """
        pass

    @staticmethod
    def effect_size_ci(
        a_bucket: list[VersionEnrichedStandardScalarMetric],
        b_bucket: list[VersionEnrichedStandardScalarMetric],
        alpha: float,
    ):
        """
        This is the effect size, Pearson r .
        """
        pass

    @staticmethod
    def calculate_N(
        minimal_effect_size_of_interest: float,
        alpha: float,
    ) -> int:
        """
        Returns the total number of samples required.
        """
        pass


class ZProportionTest(BaseStatisticTest):

    @staticmethod
    @override
    def p_value(
        a_bucket: list[VersionEnrichedStandardScalarMetric],
        b_bucket: list[VersionEnrichedStandardScalarMetric],
        alternative: str = "less",
    ) -> float:
        """
        Returns the p-value of the Z proportion test.
        """

        total_n = len(a_bucket) + len(b_bucket)

        if alternative == "less":
            _, p = sm_api.stats.proportions_ztest(
                [len(a_bucket), len(b_bucket)],
                [total_n, total_n],  # 0.5 each
                alternative="smaller",
            )
        elif alternative == "greater":
            _, p = sm_api.stats.proportions_ztest(
                [len(a_bucket), len(b_bucket)],
                [total_n, total_n],  # 0.5 each
                alternative="larger",
            )
        else:
            _, p = sm_api.stats.proportions_ztest(
                [len(a_bucket), len(b_bucket)],
                [total_n, total_n],  # 0.5 each
            )

        return p

    @staticmethod
    @override
    def effect_size_ci(
        a_bucket: list[VersionEnrichedStandardScalarMetric],
        b_bucket: list[VersionEnrichedStandardScalarMetric],
        alpha: float,
    ):
        """
        Returns the ci of the statmodel z proportion test.

        """
        total_n = len(a_bucket) + len(b_bucket)

        return sm.stats.proportion.confint_proportions_2indep(
            len(a_bucket),
            total_n,
            len(b_bucket),
            total_n,
            method=None,
            compare="ratio",
            alpha=alpha,
            correction=True,
        )


class TTest(BaseStatisticTest):
    """
    The TTest. It takes the relative difference between the two samples in to account.
    and expect them to be zero.
    """

    @staticmethod
    @override
    def p_value(
        a_bucket: list[float],
        b_bucket: list[float],
        alternative: str = "less",
    ) -> float:

        # We expect that the relative difference is zero between
        # the old version and the new one
        _, p = stats.ttest_ind(a_bucket, b_bucket, alternative=alternative)

        return p

    @staticmethod
    @override
    def effect_size_ci(
        a_bucket: list[float],
        b_bucket: list[float],
        alpha: float,
    ) -> (float, float):

        relative_diff = [a / b for a, b in zip(a_bucket, b_bucket) if a != 0]

        res = stats.ttest_1samp(
            relative_diff, popmean=0
        )  # Popmean is zero because we expect the relative difference to be zero

        ci = res.confidence_interval(1 - alpha)

        return ci.low, ci.high


class KSTest(BaseStatisticTest):
    """
    The KSTest. A more robust test that compares the time difference of the samples.
    """

    @staticmethod
    @override
    def p_value(
        a_bucket: list[float],
        b_bucket: list[float],
        alternative: str = "less",
    ) -> float:

        # This has to be like that because scipy inversed the meaning of the alternative hypothesis
        if alternative == "less":
            _, p = stats.ks_2samp(a_bucket, b_bucket, alternative="less")
        elif alternative == "greater":
            _, p = stats.ks_2samp(a_bucket, b_bucket, alternative="greater")
        else:
            _, p = stats.ks_2samp(a_bucket, b_bucket, alternative="two-sided")

        return p

    @staticmethod
    @override
    def effect_size_ci(
        a_bucket: list[VersionEnrichedStandardScalarMetric],
        b_bucket: list[VersionEnrichedStandardScalarMetric],
        alpha: float,
    ):
        return FrequencyKSTestOneSided.ci(a_bucket, b_bucket, alpha)
