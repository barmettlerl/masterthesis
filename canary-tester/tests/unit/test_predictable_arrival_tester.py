from canary_tester.tester.predictable_arrival_tester import PredictableArrivalTester


class TestProcessQuery:

    def test_working_process_query_with_aggregation(self):
        tester = PredictableArrivalTester(
            "1.0.0", 1, [], None, {"name": "test"}, None, None
        )

        assert (
            tester._process_query("avg (disk_free) by(host)", "test123")
            == "avg (disk_free{host='test123'}) by (host)"
        )

    def test_working_process_query_without_aggregation(self):
        tester = PredictableArrivalTester(
            "1.0.0", 1, [], None, {"name": "test"}, None, None
        )

        assert (
            tester._process_query("disk_free", "test123") == "disk_free{host='test123'}"
        )

    def test_not_working_process_query(self):
        tester = PredictableArrivalTester(
            "1.0.0", 1, [], None, {"name": "test"}, None, None
        )

        assert (
            tester._process_query("disk_free{host='test133'}", "test123")
            == "disk_free{host='test123'}"
        )

    def test_working_with_already_a_filter(self):
        tester = PredictableArrivalTester(
            "1.0.0", 1, [], None, {"name": "test"}, None, None
        )

        assert (
            tester._process_query(
                "avg(disk_used_percent{path='/'}) by (host)", "test123"
            )
            == "avg (disk_used_percent{path='/', host='test123'}) by (host)"
        )
