import json


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        pass


def mocked_requests_get_empty(*args, **kwargs):
    return MockResponse(
        {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [],
            },
        },
        200,
    )


def mocked_request_better_performing_alert_get(*args, **kwargs):

    with open("tests/mocks/simulate_data/a_better_dist.json") as f:
        response = json.load(f)

    start = kwargs["params"]["start"]
    end = kwargs["params"]["end"]

    metrics = []

    for ts in range(start, end):
        if ts in response["a"]:
            metrics.append({
                "metric": {
                    "alertname": "AlertName",
                    "instance": "Instance",
                    "job": "Job",
                    "host": "host1" if ts % 2 == 0 else "host2",
                },
                "values": [[ts, 1]],
            })
        if ts in response["b"]:
            metrics.append({
                "metric": {
                    "alertname": "AlertName",
                    "instance": "Instance",
                    "job": "Job",
                    "host": "host3" if ts % 2 == 0 else "host4",
                },
                "values": [[ts, 1]],
            })

    return MockResponse(
        {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": metrics,
            },
        },
        200,
    )


def mocked_request_worse_performing_alert_get(*args, **kwargs):

    with open("tests/mocks/simulate_data/a_worse_dist.json") as f:
        response = json.load(f)

    start = kwargs["params"]["start"]
    end = kwargs["params"]["end"]

    metrics = []

    for ts in range(start, end):
        if ts in response["a"]:
            metrics.append({
                "metric": {
                    "alertname": "AlertName",
                    "instance": "Instance",
                    "job": "Job",
                    "host": "host1" if ts % 2 == 0 else "host2",
                },
                "values": [[ts, 1]],
            })
        if ts in response["b"]:
            metrics.append({
                "metric": {
                    "alertname": "AlertName",
                    "instance": "Instance",
                    "job": "Job",
                    "host": "host3" if ts % 2 == 0 else "host4",
                },
                "values": [[ts, 1]],
            })

    return MockResponse(
        {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": metrics,
            },
        },
        200,
    )


def mocked_request_similar_performing_alert_get(*args, **kwargs):

    with open("tests/mocks/simulate_data/a_similar_dist.json") as f:
        response = json.load(f)

    start = kwargs["params"]["start"]
    end = kwargs["params"]["end"]

    metrics = []

    for ts in range(start, end):
        if ts in response["a"]:
            metrics.append({
                "metric": {
                    "alertname": "AlertName" + str(ts),
                    "instance": "Instance",
                    "job": "Job",
                    "host": "host1" if ts % 2 == 0 else "host2",
                },
                "values": [[ts, start]],
            })
        if ts in response["b"]:
            metrics.append({
                "metric": {
                    "alertname": "AlertName" + str(ts),
                    "instance": "Instance",
                    "job": "Job",
                    "host": "host3" if ts % 2 == 0 else "host4",
                },
                "values": [[ts, start]],
            })

    return MockResponse(
        {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": metrics,
            },
        },
        200,
    )
