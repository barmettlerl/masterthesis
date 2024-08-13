import json
import os
from typing import Dict, override

from aiohttp import ClientSession

from canary_tester.enricher.version_enricher import VersionEnricher


class MockVersionEnricher(VersionEnricher):

    def __init__(self, session: ClientSession):
        super().__init__(session)
        self._host_to_version: Dict[str, int] = {}

    @override
    async def _fetch_host_version(self) -> Dict[str, str]:

        with open(
            os.path.dirname(os.path.abspath(__file__))
            + "/simulate_data/osix_version.json",
            "r",
        ) as f:
            simulation_data = json.load(f)

        for el in simulation_data["data"]["result"]:
            self._host_to_version[el["metric"]["host"]] = el["metric"]["version"]
