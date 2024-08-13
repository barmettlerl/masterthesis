Canary tester
-
Rapid regression detection for canary rollout code for the masterthesis of lars barmettler



### Start Test
* **POST /start**: This endpoint initiates the experiment, which includes all the tests defined in the `values.yaml` file.

The body of the test request can look like this:
```json
{
    "version_under_test": "23.351.0",
    "control_group_versions": ["23.342.0", "23.331.0"],
    "max_time_s": 72000,
    "fetch_interval_s": 60,
    "start_time": 1716553605,
    "simulation_speedup_factor": 10
}
```

* `version_under_test`: The version you wan't to test
* (Optional) `control_group_versions`: A list of versions that forms the control group. If not defined all other versions are considered for control group.
* `max_time_s`: The max time in seconds the test should run
* `fetch_interval_s`: In which interval we want to run the test
* (Optional) `start_time`: This is just for debugging. Usefull if we want to rerun experiment in the past
* (Optional) `simulation_speedup_factor`: If we execute a test in the past with `start_time`, we don't like to wait as if it'd a live test. Thus the speedup

To run it with curl: 
```bash
 curl --location 'https://localhost:5000/start' \
-H 'Content-Type: application/json' \
--data '{
    "version_under_test": "23.384.0",
    "max_time_s": 72000,
    "fetch_interval_s": 60,
    "start_time": 1719560400,
    "simulation_speedup_factor": 10
}' -X POST
```

### Stop Test
* **POST /stop**:  Stops the experiment at next fetch execution (You need to wait for fetch_interval_s).
```bash
 curl --location 'https://localhost:5000/stop' \
-H 'Content-Type: application/json' \
-X POST
```


##  How to define a new test
The test are defined in the `values.yaml` file under the `test` section in the corresponding deployment (dev, test, prod). A typical test looks like this: 
```yaml
      - name: "TotalAlerts"
        query: 'ALERTS_FOR_STATE{host!=""}'
        significance_level: 0.01
        minimal_effect_size_of_interest: 2
        type_arrival: UnpredictableArrival
        direction: Bigger
```
or like 
```yaml
      - name: "TotalAlerts"
        query: 'ALERTS_FOR_STATE{host!=""}'
        significance_level: 0.01
        minimal_effect_size_of_interest: 2
        type_arrival: UnpredictableArrival
        direction: Bigger
```

### name: 
This is the name of your test, should be unique. It will be an filter criteria if you building grafana dashboards for your test. 

### query: 
This is the query that will be used on the thanos endpoint. Depending of we have a PredictableArrival-Test or an Unpredictable, the query result should be defined as follows:

#### Result from PredictableArrival-Test Query: 
`avg(cpu_usage_guest) by (host)`

```json
{
    "status": "success",
    "data": {
        "resultType": "matrix",
        "result": [
            {
                "metric": {
                    "host": "examplehost"
                },
                "values": [
                    [
                        1720691168,
                        "1.1426442277818265"
                    ], 
                    ...
                ]
            }
        ]
    }
}
```

> Make Sure that the you have in the `metric` section the host name and that in the values you have a list of  `timestamp` and the value you want to do the test upon.

#### Result from UnpredictableArrival-Test Query: 
`query: 'ALERTS_FOR_STATE{host!=""}'`

```json
[
  {
    "schema": {
     ...,
      "fields": [
        ...,
        {
          ...,
          "labels": {
            "__name__": "ALERTS_FOR_STATE",
            "host": "examplehost",
            "host_id": "21252",
            ...
          },
        }
      ]
    },
    "data": {
      "values": [
        [
          1720692000000,
          1720692060000,
          1720692120000,
          1720692180000,
          1720692240000,
          ...
        ],
        ...
      ]
    }
  }
]

```

> The same unpredicted event can come in multiple request, don't bother about it. We will verify the uniqueness of the event to prevent dublicates.

### significance_level
In a statistical test, we can never assert that something has a 100% probability of occurring. Instead, we use a significance level, such as 0.05, 0.01, or 0.001, to express our confidence levels of 95%, 99%, or 99.9% respectively. A lower significance level indicates higher confidence that a detected effect is real, but it also requires more data to reach a conclusion. Therefore, selecting a significance level is a trade-off between confidence and data requirements. We recommend starting with a significance level of 0.05 and reducing it only if you have sufficient data to allow the test to converge more quickly than existing tests.


### minimal_effect_size_of_interest
Not every change in behavior is significant for the test. For instance, consider a CPU usage that averages 30%. If, after a software update, the usage increases to 32%, should we really consider this a problem? A minimal effect size of interest is necessary to prevent the system from flagging such small differences as alerts. This threshold defines the point at which a change in behavior becomes relevant.

For example, if you set the minimal effect size of interest at 0.5, only changes greater than 50% are deemed significant. In the case of a 30% CPU usage, we would only consider it a problem if the usage increases above 45% or decreases below 15% after the update. This threshold ensures that we only react to changes that are truly impactful, avoiding unnecessary alerts for minor variations.

### type_arrival
For performance and logical reasons, we have separated the tests into two types: `PredictableArrival` and `UnpredictableArrival`. `UnpredictableArrival` tests are designed for information that arrives unpredictably, such as alerts. In contrast, `PredictableArrival` tests are intended for metrics with a regular heartbeat, like CPU usage or DiskSizeUsage.

However, `PredictableArrival` tests are conducted only when we detect a version change to the version under test. Therefore, `PredictableArrival` tests are only useful if there are devices that undergo version changes.

### direction
To define which direction is considered as worse, we have to define either `Bigger` or `Smaller`. For example in the case of `DiskFreeSizeLeft`, we consider it harmful if the size left is significant smaller than before, in this case we set `direction: Smaller`. In the case of `Alerts` we consider it harmful if we have more alerts thus `direction: Bigger`. 

## Environment variables

| Name                    | Default Value                                                    | Description                                            |
|-------------------------|------------------------------------------------------------------|--------------------------------------------------------|
| `AUTH_COOKIE`           | ""                                                               | Authentication cookie used for securing access.        |
| `THANOS_QUERIER_ENDPOINT` | `http://localhost:9090`                                        | Endpoint for Thanos querier.                           |
| `VERIFY_SSL`            | `True`                                                           | Can set to `False` to bypass problems during development                           |
| `FETCH_INTERVAL_IN_SEC` | `60`                                                             | Interval in seconds for fetching data.                 |
| `CONFIG_FILE_PATH`      | `config.yaml`                                                    | Path to the configuration file.                        |
| `PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME`      | `30`                                | Time to wait after and before version changed on device |
| `PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME`      | `300`                                | Time region to analyze before and after version change to detect differences |
| `LOG_LEVEL`             | `20`                                | Log level we want to display |
| `MINIMAL_SAMPLE_SIZE`      | `8`                                | Minimal number of sample for each treatment and control group we need to start analysis |

