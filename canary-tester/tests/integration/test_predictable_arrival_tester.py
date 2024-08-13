from unittest import mock

from canary_tester.config_loader.schema import SingleTestConfigType
from canary_tester.tester.predictable_arrival_tester import PredictableArrivalTester
from canary_tester.tester.statistic_tests import TTest
from canary_tester.types import (
    GlobalConfig,
    StandardScalarMetric,
    TesterReturn,
    TesterReturnReason,
    TesterReturnType,
)
from canary_tester.version_enricher import VersionEnricher, VersionEntry
from tests.mocks.mock_thanos_predictable_arrival import (
    mocked_request_get_full,
    mocked_requests_get_simple,
)


class TestAvgMetricAggregation:
    @mock.patch("requests.get", side_effect=mocked_requests_get_simple)
    def test_succesfully_returns_avg(self, mock_get):
        test = PredictableArrivalTester(
            "1.0.0", 1, [], None, {"name": "test", "query": ""}, None, GlobalConfig()
        )
        res = test._avg_metric_aggregation("host1", 0, 1)
        assert res == StandardScalarMetric(1, "host1", 3.0)


class TestFetch:
    @mock.patch("requests.get", side_effect=mocked_requests_get_simple)
    def test_succesfully_returns_avg_before_and_after(self, mock_get):
        test = PredictableArrivalTester(
            "1.0.0",
            1,
            [],
            None,
            {"name": "test", "query": ""},
            None,
            GlobalConfig(
                PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME=1,
                PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME=1,
            ),
        )
        old_version_metrics, new_version_metrics = test._fetch([("host1", 2)])

        assert old_version_metrics[0] == StandardScalarMetric(1, "host1", 3.0)
        assert new_version_metrics[0] == StandardScalarMetric(3, "host1", 5.0)


class TestRun:
    @mock.patch("requests.get", side_effect=mocked_requests_get_simple)
    def test_that_has_not_enough_data(sekf, mock_get):
        enricher: VersionEnricher = mock.MagicMock(return_value=[])
        test = PredictableArrivalTester(
            "1.0.0",
            2,
            [],
            enricher,
            {"name": "test"},
            None,
            GlobalConfig(),
        )
        res = test.run(0, 1)

        assert res == TesterReturn(
            "test", TesterReturnType.CONTINUE, TesterReturnReason.NOT_ENOUGH_DATA
        )

    @mock.patch("requests.get", side_effect=mocked_request_get_full)
    def test_terminates_test_because_of_worse_performance(sekf, mock_get):

        enricher = VersionEnricher()
        enricher._host_to_versions = {
            "host1": [VersionEntry(0, "0.0.0"), VersionEntry(2, "1.0.0")],
            "host2": [VersionEntry(0, "0.0.0"), VersionEntry(2, "1.0.0")],
            "host3": [VersionEntry(0, "0.0.0"), VersionEntry(2, "1.0.0")],
            "host4": [VersionEntry(0, "0.0.0"), VersionEntry(2, "1.0.0")],
            "host5": [VersionEntry(0, "0.0.0"), VersionEntry(4, "1.0.0")],
        }

        test_config: SingleTestConfigType = {
            "name": "test",
            "query": "avg (disk_free) by(host)",
            "significance_level": 0.05,
            "minimal_effect_size_of_interest": 0.1,
            "type_arrival": "PredictableArrival",
            "test_statistic_type": "MannWhitneyUTest",
            "direction": "Smaller",
        }

        test = PredictableArrivalTester(
            "1.0.0",
            3,
            [],
            enricher,
            test_config,
            TTest,
            GlobalConfig(
                PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME=1,
                PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME=1,
                MINIMAL_SAMPLE_SIZE=5,
            ),
        )

        res = test.run(4, 5)

        assert res == TesterReturn(
            "test",
            TesterReturnType.CONTINUE,
            TesterReturnReason.NOT_ENOUGH_DATA,
        )

        res = test.run(5, 6)

        assert res == TesterReturn(
            "test",
            TesterReturnType.TERMINATION,
            TesterReturnReason.WORSE,
        )
