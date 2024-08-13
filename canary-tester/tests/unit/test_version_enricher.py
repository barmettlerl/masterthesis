from canary_tester.version_enricher import VersionEnricher, VersionEntry
from canary_tester.types import (
    StandardScalarMetric,
)


class TestGetVersionAtTs:
    def test_no_entry_for_host(self):
        version_enricher = VersionEnricher()
        metric = StandardScalarMetric(1, "host1", 0)

        assert version_enricher._get_version_at_ts(metric) == "unknown"

    def test_host_with_only_one_version_present(self):
        version_enricher = VersionEnricher()
        version_enricher._host_to_versions = {
            "host1": [VersionEntry(0, "1.0.0")],
        }
        metric = StandardScalarMetric(1, "host1", 0)

        assert version_enricher._get_version_at_ts(metric) == "1.0.0"

    def test_host_with_changing_version(self):
        version_enricher = VersionEnricher()
        version_enricher._host_to_versions = {
            "host1": [VersionEntry(0, "1.0.0"), VersionEntry(1, "2.0.0")],
        }
        metric = StandardScalarMetric(2, "host1", 0)

        assert version_enricher._get_version_at_ts(metric) == "2.0.0"

    def test_host_with_changing_version_metric_between(self):
        version_enricher = VersionEnricher()
        version_enricher._host_to_versions = {
            "host1": [VersionEntry(0, "1.0.0"), VersionEntry(2, "2.0.0")],
        }
        metric = StandardScalarMetric(1, "host1", 0)

        assert version_enricher._get_version_at_ts(metric) == "1.0.0"


class TestAddVersionToHost:
    def test_first_version_added(self):
        version_enricher = VersionEnricher()
        version_enricher._add_version_to_host("host1", 1, "1.0.0")

        assert version_enricher._host_to_versions == {
            "host1": [VersionEntry(1, "1.0.0")],
        }

    def test_second_version_added(self):
        version_enricher = VersionEnricher()
        version_enricher._host_to_versions = {
            "host1": [VersionEntry(1, "1.0.0")],
        }
        version_enricher._add_version_to_host("host1", 2, "2.0.0")

        assert version_enricher._host_to_versions == {
            "host1": [VersionEntry(1, "1.0.0"), VersionEntry(2, "2.0.0")],
        }

    def test_add_version_that_is_the_same_as_previous_one(self):
        version_enricher = VersionEnricher()
        version_enricher._host_to_versions = {
            "host1": [VersionEntry(1, "1.0.0")],
        }
        version_enricher._add_version_to_host("host1", 2, "1.0.0")

        assert version_enricher._host_to_versions == {
            "host1": [VersionEntry(1, "1.0.0")],
        }

    def test_add_new_version_that_has_been_changed_before_older_one(self):
        version_enricher = VersionEnricher()
        version_enricher._host_to_versions = {
            "host1": [VersionEntry(1, "1.0.0"), VersionEntry(3, "2.0.0")],
        }
        version_enricher._add_version_to_host("host1", 2, "1.1.0")

        assert version_enricher._host_to_versions == {
            "host1": [VersionEntry(1, "1.0.0"), VersionEntry(3, "2.0.0")],
        }


class TestGetHostWithChangedVersionInInterval:
    def test_returns_one_version_change(self):
        version_enricher = VersionEnricher()
        version_enricher._host_to_versions = {
            "host1": [VersionEntry(0, "0.0.0"), VersionEntry(1, "1.0.0")],
        }

        assert version_enricher.get_host_with_changed_version_in_interval(
            "1.0.0", 0, 2
        ) == [("host1", 1)]

    def terst_doesnt_return_when_only_one_entry(self):
        version_enricher = VersionEnricher()
        version_enricher._host_to_versions = {
            "host1": [VersionEntry(1, "1.0.0")],
        }

        assert (
            version_enricher.get_host_with_changed_version_in_interval("1.0.0", 0, 2)
            == []
        )

    def test_doesnt_return_when_version_not_in_time_interval(self):
        version_enricher = VersionEnricher()
        version_enricher._host_to_versions = {
            "host1": [VersionEntry(0, "0.0.0"), VersionEntry(2, "1.0.0")],
        }

        assert (
            version_enricher.get_host_with_changed_version_in_interval("1.0.0", 0, 1)
            == []
        )

    def test_doesnt_return_when_changed_version_is_not_version_under_test(self):
        version_enricher = VersionEnricher()
        version_enricher._host_to_versions = {
            "host1": [VersionEntry(0, "0.0.0"), VersionEntry(1, "1.0.0")],
        }

        assert (
            version_enricher.get_host_with_changed_version_in_interval("0.0.0", 0, 2)
            == []
        )


class TestVerionEntryEqual:
    def test_equal_true(self):
        version_entry1 = VersionEntry(1, "1.0.0")
        version_entry2 = VersionEntry(1, "1.0.0")

        assert version_entry1 == version_entry2

    def test_equal_false(self):
        version_entry1 = VersionEntry(1, "1.0.0")

        assert version_entry1 != 4
