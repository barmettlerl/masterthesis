from typing import List
from canary_tester.config_loader.schema import SingleTestConfigType
from canary_tester.version_enricher import VersionEnricher
from canary_tester.types import GlobalConfig, TestArrivalType
from canary_tester.tester.tester import Tester
from canary_tester.tester.predictable_arrival_tester import PredictableArrivalTester
from canary_tester.tester.unpredictable_arrival_tester import UnpredictableArrivalTester
from canary_tester.tester.statistic_tests import (
    BaseStatisticTest,
    KSTest,
)


class TestBuilder:
    """
    Based on the configuration it builds a single test object
    """

    def _select_arrival_test(type_arrival: str) -> Tester:
        match TestArrivalType.from_str(type_arrival):
            case TestArrivalType.PredictableArrival:
                return PredictableArrivalTester
            case TestArrivalType.UnpredicatableArrival:
                return UnpredictableArrivalTester

    def _select_statistic_test(type_arrival: str):
        match TestArrivalType.from_str(type_arrival):
            case TestArrivalType.PredictableArrival:
                return KSTest
            case TestArrivalType.UnpredicatableArrival:
                return KSTest

    def build(
        version_under_test: str,
        total_peeks: int,
        control_group_versions: List[str],
        enricher: VersionEnricher,
        test_config: SingleTestConfigType,
        global_config: GlobalConfig,
    ):
        tester: Tester = TestBuilder._select_arrival_test(test_config["type_arrival"])
        statistic_test: BaseStatisticTest = TestBuilder._select_statistic_test(
            test_config["type_arrival"]
        )

        return tester(
            version_under_test=version_under_test,
            total_peeks=total_peeks,
            control_group_versions=control_group_versions,
            enricher=enricher,
            test_config=test_config,
            statistic_test=statistic_test,
            global_config=global_config,
        )
