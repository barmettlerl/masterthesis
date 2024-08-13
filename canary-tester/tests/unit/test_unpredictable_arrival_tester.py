from typing import List
from canary_tester.tester.unpredictable_arrival_tester import UnpredictableArrivalTester
from canary_tester.types import VersionEnrichedStandardScalarMetric


class TestApplyNewDataChunk:
    def test_apply_new_data_chunk_first_entry(self):
        # Arrange
        tester = UnpredictableArrivalTester(
            "1.0.0", 1, [], None, {"name": "test"}, None, None
        )

        new_data_chunk: List[VersionEnrichedStandardScalarMetric] = [
            VersionEnrichedStandardScalarMetric(3, "host1", 1.0, "1.0.0"),
            VersionEnrichedStandardScalarMetric(2, "host1", 1.0, "0.0.0"),
        ]

        # Act
        tester._apply_new_data_chunk(new_data_chunk)

        assert tester._treatment_group == [new_data_chunk[0]]
        assert tester._control_group == [new_data_chunk[1]]

    def test_apply_new_data_chunk_multiple_entries(self):
        tester = UnpredictableArrivalTester(
            "1.0.0", 1, [], None, {"name": "test"}, None, None
        )

        new_data_chunk: List[VersionEnrichedStandardScalarMetric] = [
            VersionEnrichedStandardScalarMetric(3, "host1", 0, "1.0.0"),
            VersionEnrichedStandardScalarMetric(4, "host1", 0, "1.0.0"),
            VersionEnrichedStandardScalarMetric(2, "host1", 0, "0.0.0"),
            VersionEnrichedStandardScalarMetric(4, "host1", 0, "0.0.0"),
        ]

        tester._apply_new_data_chunk(new_data_chunk)

        assert tester._treatment_group[-1].value == 1
        assert tester._control_group[-1].value == 2


class TestCalculateSecondDiff:
    def test_calculate_diff_between_two_microsecond_ts(self):
        # Arrange
        tester = UnpredictableArrivalTester(
            "1.0.0", 1, [], None, {"name": "test"}, None, None
        )

        a = VersionEnrichedStandardScalarMetric(2.123456, "host1", 0, "1.0.0")
        b = VersionEnrichedStandardScalarMetric(1.133456, "host1", 0, "0.0.0")

        # Act
        result = tester._calculate_second_diff(a, b)

        # Assert
        assert result == 0.99
