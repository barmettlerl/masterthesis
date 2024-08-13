import json
import os
from typing import List, override

from aiohttp import ClientSession
from canary_tester.fetcher.alert_fetcher import AlertFetcher


class MockAlertFetcher(AlertFetcher):

    @override
    def __init__(self, session: ClientSession, query: str):
        super().__init__(session, query)

    @override
    async def _fetch_alerts(self, time_delta) -> List[List[str]]:
        with open(
            os.path.dirname(os.path.abspath(__file__)) + "/simulate_data/alerts.json",
            "r",
        ) as f:
            simulation_data = json.load(f)

        alerts = []

        for el in simulation_data:
            alerts.append(el)

        return alerts
