class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        pass


def mocked_requests_get_simple(*args, **kwargs):

    if kwargs["params"]["end"] == 1:
        return MockResponse(
            {
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {
                            "metric": {"host": "host1"},
                            "values": [[1, "2"], [1, "4"]],
                        },
                    ],
                },
            },
            200,
        )
    else:
        return MockResponse(
            {
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {
                            "metric": {"host": "host1"},
                            "values": [[3, "4"], [3, "6"]],
                        },
                    ],
                },
            },
            200,
        )


def mocked_request_get_full(*args, **kwargs):
    match kwargs["params"]["end"]:
        case 0:
            return MockResponse(
                {
                    "status": "success",
                    "data": {
                        "resultType": "matrix",
                        "result": [
                            {
                                "metric": {"host": "host1"},
                                "values": [],
                            },
                        ],
                    },
                },
                200,
            )
        case 1:
            return MockResponse(
                {
                    "status": "success",
                    "data": {
                        "resultType": "matrix",
                        "result": [
                            {
                                "metric": {"host": "host1"},
                                "values": [[1, "1"]],
                            },
                            {
                                "metric": {"host": "host2"},
                                "values": [[1, "1"]],
                            },
                            {
                                "metric": {"host": "host3"},
                                "values": [[1, "1"]],
                            },
                            {
                                "metric": {"host": "host4"},
                                "values": [[1, "1"]],
                            },
                        ],
                    },
                },
                200,
            )
        case 2:
            return MockResponse(
                {
                    "status": "success",
                    "data": {
                        "resultType": "matrix",
                        "result": [
                            {
                                "metric": {"host": "host1"},
                                "values": [[2, "2"], [2, "2"]],
                            },
                            {
                                "metric": {"host": "host2"},
                                "values": [[2, "2"], [2, "2"]],
                            },
                            {
                                "metric": {"host": "host3"},
                                "values": [[2, "2"], [2, "2"]],
                            },
                            {
                                "metric": {"host": "host4"},
                                "values": [[2, "2"], [2, "2"]],
                            },
                        ],
                    },
                },
                200,
            )
        case 3:
            return MockResponse(
                {
                    "status": "success",
                    "data": {
                        "resultType": "matrix",
                        "result": [
                            {
                                "metric": {"host": "host1"},
                                "values": [[3, "3"], [3, "3"], [3, "3"]],
                            },
                            {
                                "metric": {"host": "host2"},
                                "values": [[3, "3"], [3, "3"], [3, "3"]],
                            },
                            {
                                "metric": {"host": "host3"},
                                "values": [[3, "3"], [3, "3"], [3, "3"]],
                            },
                            {
                                "metric": {"host": "host4"},
                                "values": [[3, "3"], [3, "3"], [3, "3"]],
                            },
                        ],
                    },
                },
                200,
            )
        case 4:
            return MockResponse(
                {
                    "status": "success",
                    "data": {
                        "resultType": "matrix",
                        "result": [
                            {
                                "metric": {"host": "host1"},
                                "values": [
                                    [4, "4"],
                                    [4, "4"],
                                ],
                            },
                            {
                                "metric": {"host": "host2"},
                                "values": [[4, "4"], [4, "4"]],
                            },
                            {
                                "metric": {"host": "host3"},
                                "values": [[4, "4"], [4, "4"]],
                            },
                            {
                                "metric": {"host": "host4"},
                                "values": [[4, "4"], [4, "4"]],
                            },
                        ],
                    },
                },
                200,
            )
        case 5:
            return MockResponse(
                {
                    "status": "success",
                    "data": {
                        "resultType": "matrix",
                        "result": [
                            {
                                "metric": {"host": "host2"},
                                "values": [
                                    [5, "5"],
                                    [5, "5"],
                                ],
                            },
                        ],
                    },
                },
                200,
            )

        case 6:
            return MockResponse(
                {
                    "status": "success",
                    "data": {
                        "resultType": "matrix",
                        "result": [
                            {
                                "metric": {"host": "host2"},
                                "values": [
                                    [6, "6"],
                                    [6, "6"],
                                ],
                            },
                        ],
                    },
                },
                200,
            )
