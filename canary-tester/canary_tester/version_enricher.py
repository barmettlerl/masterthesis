from typing import Dict, List
from dotenv import load_dotenv
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


from canary_tester.types import (
    GlobalConfig,
    StandardScalarMetric,
    VersionEnrichedStandardScalarMetric,
)

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

load_dotenv()

logger = logging.getLogger("root")


class VersionEntry:
    ts: float
    version: str

    def __init__(self, ts: float, version: str):
        self.ts = ts
        self.version = version

    def __eq__(self, other: object) -> bool:
        if isinstance(other, VersionEntry):
            return self.ts == other.ts and self.version == other.version
        return False


class VersionEnricher:
    """A class that enriches metrics or logs with the version of the host."""

    _host_to_versions: Dict[str, list[VersionEntry]]
    _frequencies: Dict[str, int]
    _global_config: GlobalConfig

    def __init__(self, global_config: GlobalConfig = GlobalConfig()):
        self._host_to_versions: Dict[str, list[VersionEntry]] = {}
        self._frequencies = {}
        self._global_config = global_config

    @property
    def frequencies(self) -> Dict[str, int]:
        """Returns the frequencies of the versions of the hosts."""
        return self._frequencies

    def update(self, timestamp) -> None:
        """Updates the enricher with the new host to version mapping."""

        self._fetch_host_version(timestamp)

        self._set_frequencies()

        logger.debug(self._frequencies)

    def enrich(
        self, metrics: List[StandardScalarMetric]
    ) -> List[VersionEnrichedStandardScalarMetric]:
        """Enriches the metrics with the version of the host."""

        enriched_metrics = []

        for metric in metrics:
            enriched_metrics.append(
                VersionEnrichedStandardScalarMetric(
                    ts=metric.ts,
                    host_name=metric.host_name,
                    value=metric.value,
                    version=self._get_version_at_ts(metric),
                )
            )

        return enriched_metrics

    def get_host_with_changed_version_in_interval(
        self, version_under_test: str, start: float, end: float
    ):
        host_with_changed_version: list[tuple[str, float]] = []

        for host, versions in self._host_to_versions.items():
            if (
                len(versions) > 1
                and versions[-1].ts >= start
                and versions[-1].ts <= end
                and versions[-1].version == version_under_test
            ):
                host_with_changed_version.append((host, versions[-1].ts))

        return host_with_changed_version

    def verify_version(self, version: str) -> bool:
        """Verifies if the version is in the mapping."""

        return version in self._frequencies.keys()

    def _get_version_at_ts(self, metric: StandardScalarMetric) -> str:
        """Returns the version of the host at the timestamp of the metric."""
        if metric.host_name not in self._host_to_versions.keys():
            return "unknown"

        version_entries = self._host_to_versions[metric.host_name]

        if len(version_entries) == 1:
            return version_entries[0].version

        for i in range(1, len(version_entries)):
            if version_entries[i].ts > metric.ts:
                return version_entries[i - 1].version

        return version_entries[-1].version

    def _set_frequencies(self):

        self._frequencies = {}
        for entries in self._host_to_versions.values():
            self._frequencies[entries[-1].version] = (
                self._frequencies.get(entries[-1].version, 0) + 1
            )

    def _fetch_host_version(self, timestamp: float):

        params = {
            "query": "max(osix_build_info) by (host, version)",
            "dedup": "true",
            "partial_response": "false",
            "time": timestamp,
            "engine": "thanos",
            "analyze": "false",
        }
        session = self._create_sesion_with_retries()

        res = session.get(
            self._global_config.THANOS_QUERIER_ENDPOINT + "/api/v1/query",
            params=params,
            cookies={"_oauth2_proxy_osdp_open_ch": self._global_config.AUTH_COOKIE},
            verify=self._global_config.VERIFY_SSL,
        )

        try:
            res.raise_for_status()
            json_extract = res.json()

        except requests.exceptions.HTTPError as e:
            raise Exception(
                f"Error while fetching host version: {e} {res.text} {res.url}: THIS"
                " MIGHT BE A PROBLEM WITH AUTHENTICATION OR THE QUERY"
                " ITSELF."
            )

        for el in json_extract["data"]["result"]:
            if "version" in el["metric"]:

                self._add_version_to_host(
                    el["metric"]["host"],  # host
                    el["value"][0],  # ts
                    el["metric"]["version"],  # version
                )
            else:
                self._add_version_to_host(
                    el["metric"]["host"], el["value"][0], "unknown"
                )

    def _add_version_to_host(self, host: str, ts: int, version: str) -> None:
        """Adds a version to a host in the mapping."""
        entries = self._host_to_versions.setdefault(host, [])
        if not entries or (entries[-1].version != version and entries[-1].ts < ts):
            entries.append(VersionEntry(ts, version))

    def _create_sesion_with_retries(self):
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504, 422],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
