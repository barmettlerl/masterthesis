from typing import List
from canary_tester.types import VersionEnrichedStandardScalarMetric

import random
import logging

logger = logging.getLogger("root")


class AlertGroupBalancer:
    """
    To balance the alert metrics evently between test and control groups, we have to ensure that the
    number of hosts with the version under test is equal to the number of hosts with an other
    version. Furthermore we make sure that following things hold:

    - The hosts are selected randomly.
    - The hosts that have asigned a version not equal to the version under test should be
      distributed accordingly to the frequencies of the versions in the control group.
    - Changing assignments between hosts and versions should be taken into account.
    """

    def balance(
        frequencies: dict[str, int],
        version_under_test: str,
        control_group_versions: List[str],
        enriched_data: List[VersionEnrichedStandardScalarMetric],
    ) -> List[VersionEnrichedStandardScalarMetric]:
        """
        Balances the metrics evently between test and control groups. We can do that because
        we assume that each metric is independently and identically distributed.

        Args:
            frequencies: The frequencies of the versions of the hosts.
            version_under_test: The version under test.
            enriched_data: The enriched data.

        Returns:
            The balanced enriched data.
        """

        version_under_test_count = frequencies[version_under_test]

        if control_group_versions == []:
            other_versions = list(
                filter(lambda x: x != version_under_test, frequencies.keys())
            )
        else:
            other_versions = list(
                filter(lambda x: x in control_group_versions, frequencies.keys())
            )

        other_versions_count = sum([frequencies[el] for el in other_versions])

        filtred_data_version_under_test = []
        filtered_data_other_versions = []

        for metric in enriched_data:
            if (
                metric.version == version_under_test
                and random.randint(1, version_under_test_count) <= other_versions_count
            ):
                filtred_data_version_under_test.append(metric)
            elif (
                metric.version != version_under_test
                and random.randint(1, other_versions_count) <= version_under_test_count
            ):
                filtered_data_other_versions.append(metric)

        return filtred_data_version_under_test + filtered_data_other_versions
