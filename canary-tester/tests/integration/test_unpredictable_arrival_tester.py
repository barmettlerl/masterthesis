from unittest import mock

from tests.mocks.mock_unpredictable_arrival_requests import (
    mocked_request_better_performing_alert_get,
    mocked_request_similar_performing_alert_get,
    mocked_request_worse_performing_alert_get,
    mocked_requests_get_empty,
)
from canary_tester.tester.unpredictable_arrival_tester import UnpredictableArrivalTester
from canary_tester.types import (
    TesterReturn,
    TesterReturnType,
    TesterReturnReason,
    GlobalConfig,
)
from canary_tester.version_enricher import VersionEnricher
from canary_tester.tester.statistic_tests import ZProportionTest
from canary_tester.version_enricher import VersionEntry


class TestRun:
    @mock.patch("requests.get", side_effect=mocked_requests_get_empty)
    def test_return_not_enough_data(self, mock_get):
        enricher: VersionEnricher = _init_enricher()
        test = UnpredictableArrivalTester(
            "1.0.0",
            2,
            [],
            enricher,
            {"name": "test", "query": ""},
            None,
            GlobalConfig(),
        )
        res = test.run(0, 1)

        assert res == TesterReturn(
            "test",
            TesterReturnType.CONTINUE,
            TesterReturnReason.NOT_ENOUGH_DATA,
        )


class TestZProportionTestRun:
    @mock.patch("requests.get", side_effect=mocked_request_better_performing_alert_get)
    def test_zproportion_should_perform_better_than_previous_version(self, mock_get):
        enricher: VersionEnricher = _init_enricher()

        test = UnpredictableArrivalTester(
            "1.0.0",
            101,
            ["0.0.0"],
            enricher,
            {
                "name": "test",
                "query": "",
                "direction": "Smaller",
                "significance_level": 0.05,
                "minimal_effect_size_of_interest": 0.1,
            },
            ZProportionTest,
            GlobalConfig(),
        )

        res = None

        for i in range(0, 10000, 100):
            res = test.run(i, i + 100)

        assert res == TesterReturn(
            "test",
            TesterReturnType.TERMINATION,
            TesterReturnReason.BETTER,
        )

    @mock.patch("requests.get", side_effect=mocked_request_worse_performing_alert_get)
    def test_zproportion_should_not_perform_better_than_previous_version(
        self, mock_get
    ):
        enricher: VersionEnricher = _init_enricher()

        test = UnpredictableArrivalTester(
            "1.0.0",
            101,
            ["0.0.0"],
            enricher,
            {
                "name": "test",
                "query": "",
                "direction": "Smaller",
                "significance_level": 0.01,
                "minimal_effect_size_of_interest": 0.1,
            },
            ZProportionTest,
            GlobalConfig(),
        )

        res = None

        for i in range(0, 10000, 100):
            res = test.run(i, i + 100)

        assert res == TesterReturn(
            "test",
            TesterReturnType.TERMINATION,
            TesterReturnReason.WORSE,
        )

    @mock.patch("requests.get", side_effect=mocked_request_similar_performing_alert_get)
    def test_zproportion_should_stop_because_of_insignificant_difference(
        self, mock_get
    ):
        enricher: VersionEnricher = _init_enricher()

        test = UnpredictableArrivalTester(
            "1.0.0",
            101,
            ["0.0.0"],
            enricher,
            {
                "name": "test",
                "query": "",
                "direction": "Smaller",
                "significance_level": 0.05,
                "minimal_effect_size_of_interest": 0.5,
            },
            ZProportionTest,
            GlobalConfig(),
        )

        res = None

        for i in range(0, 10000, 100):
            res = test.run(i, i + 100)

        assert res == TesterReturn(
            "test",
            TesterReturnType.TERMINATION,
            TesterReturnReason.EFFECT_SIZE_UNDER_THRESHOLD,
        )


def _init_enricher():
    enricher: VersionEnricher = VersionEnricher()
    enricher._host_to_versions = {
        "host1": [VersionEntry(0, "0.0.0")],
        "host2": [VersionEntry(0, "0.0.0")],
        "host3": [VersionEntry(1, "1.0.0")],
        "host4": [VersionEntry(1, "1.0.0")],
    }

    enricher._set_frequencies()

    return enricher
