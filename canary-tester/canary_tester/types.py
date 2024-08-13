from enum import Enum
import logging
import threading


class TestArrivalType(Enum):
    """
    An enumeration class that represents the types of tests that can be run
    - UnpredictableArrival are tests that run on data that can arrive arbitrarily
    like alerts or errors, etc.
    - PredictableArrival are tests that run on data that arrives in a predictable
      interval like heartbeats, CPU usage, etc.
    """

    UnpredicatableArrival = "UnpredictableArrival"
    PredictableArrival = "PredictableArrival"

    __test__ = False

    @staticmethod
    def from_str(value: str) -> "TestArrivalType":
        if value in ("UnpredictableArrival", "unpredictable_arrival"):
            return TestArrivalType.UnpredicatableArrival
        elif value in ("PredictableArrival", "predictable_arrival"):
            return TestArrivalType.PredictableArrival
        else:
            raise ValueError(f"Unknown value: {value}")


class ComparisonDirection(Enum):
    """
    When we compare the distribution we want to check whenever our new version performs
    better than the old one. But better depens on the metric we are comparing. So if we
    compare free_disk size then we want to have as much as possible thus we are interested
    that B < A. But if we compare the CPU usage then we want to have as less as possible
    thus we are interested that A < B.

    - Bigger: B < A (e.g. free_disk size)
    - Smaller: A < B (e.g. CPU usage)
    """

    Bigger = "Bigger"
    Smaller = "Smaller"

    @staticmethod
    def from_str(value: str) -> "ComparisonDirection":
        if value in ("BIGGER", "Bigger", "bigger"):
            return ComparisonDirection.Bigger
        elif value in ("SMALLER", "Smaller", "smaller"):
            return ComparisonDirection.Smaller
        else:
            raise ValueError(f"Unknown value: {value}")


class TestStatistictType(Enum):
    """
    The type of the test statistic that we want to run.
    """

    ZProportionTest = "ZProportionTest"
    TTest = "TTest"

    __test__ = False

    @staticmethod
    def from_str(value: str) -> "TestStatistictType":
        if value in ("ZProportionTest", "z_proportion_test"):
            return TestStatistictType.ZProportionTest
        elif value in ("TTest", "t_test"):
            return TestStatistictType.TTest
        else:
            raise ValueError(f"Unknown value: {value}")


class BaseMetric:
    """
    The base metric class.
    """

    ts: int
    host_name: str

    def __init__(self, ts: int, host_name: str):
        self.ts = ts
        self.host_name = host_name

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, BaseMetric)
            and self.ts == value.ts
            and self.host_name == value.host_name
        )

    def __str__(self):
        return f"host: {self.host_name}, ts: {self.ts}"


class StandardScalarMetric(BaseMetric):
    """
    The metric is for all values that contain as a value a scalar type
    """

    value: float

    def __init__(self, ts: int, host_name: str, value: float):
        super().__init__(ts, host_name)
        self.value = value

    def __eq__(self, value: object) -> bool:
        return super().__eq__(value) and self.value == value.value

    def __str__(self):
        return f"{super().__str__()}, value: {self.value}"


class VersionEnrichedStandardScalarMetric(StandardScalarMetric):
    """
    The standard metric with the version of the host.
    """

    version: str

    def __init__(
        self,
        ts: int,
        host_name: str,
        value: float,
        version: str,
    ):
        super().__init__(ts, host_name, value)
        self.version = version

    def __eq__(self, value: object) -> bool:
        return super().__eq__(value) and self.version == value.version

    def __str__(self):
        return f"{super().__str__()}, version: {self.version}"


class RunningThread:
    lock: threading.Lock = None

    def __init__(self):
        self.lock = threading.Lock()
        self.started = False
        self.finished = False
        self.should_stop = False
        self.thread: threading.Thread = None


class TesterReturnType(Enum):

    __test__ = False
    TERMINATION = "TERMINATION"
    CONTINUE = "CONTINUE"


class TesterReturnReason(Enum):
    __test__ = False
    MAX_TIME_REACHED = "MAX_TIME_REACHED"
    BETTER = "BETTER"  # A performs better than B
    WORSE = "WORSE"  # A performs worse than B
    NOT_ENOUGH_DATA = (  # we don't started the test yet because we don't have enough data
        "NOT_ENOUGH_DATA"
    )
    EFFECT_SIZE_UNDER_THRESHOLD = (  # the effect size is smaller than the minimal effectsize of interest
        "EFFECT_SIZE_UNDER_THRESHOLD"
    )
    COULD_NOT_MAKE_DECISION = (  # we could not make a decision yet
        "COULD_NOT_MAKE_DECISION"
    )
    HTTP_ERROR = "HTTP_ERROR"  # we got an http error

    UNKNOWN_ERROR = "UNKNOWN_ERROR"  # we got an unknown error


class TesterReturn:
    __test__ = False
    type: TesterReturnType
    name: str
    reason: TesterReturnReason

    def __init__(
        self,
        name: str,
        type: TesterReturnType,
        reason: TesterReturnReason,
    ):
        self.name = name
        self.type = type
        self.reason = reason

    def log(self, logger):
        logger.info({
            "name": self.name,
            "type": f"{self.type.value}",
            "reason": f"{self.reason.value}",
        })

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, TesterReturn)
            and self.type == value.type
            and self.name == value.name
            and self.reason == value.reason
        )

    def __str__(self):
        return f"name: {self.name}, type: {self.type}, reason: {self.reason}"


class GlobalConfig:
    THANOS_QUERIER_ENDPOINT: str
    AUTH_COOKIE: str
    PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME: int
    PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME: int
    CONFIG_FILE_PATH: str
    LOG_LEVEL: int
    VERIFY_SSL: bool
    MINIMAL_SAMPLE_SIZE: int

    def __init__(self, **kwargs):
        self.THANOS_QUERIER_ENDPOINT = kwargs.get(
            "THANOS_QUERIER_ENDPOINT", "http://localhost:9090"
        )
        self.AUTH_COOKIE = kwargs.get("AUTH_COOKIE", "")
        self.PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME = int(
            kwargs.get("PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME", 30)
        )
        self.PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME = int(
            kwargs.get("PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME", 300)
        )
        self.CONFIG_FILE_PATH = kwargs.get("CONFIG_FILE_PATH", "config.yaml")
        self.LOG_LEVEL = int(kwargs.get("LOG_LEVEL", logging.INFO))
        self.VERIFY_SSL = kwargs.get("VERIFY_SSL", "True") == "True"
        self.MINIMAL_SAMPLE_SIZE = int(kwargs.get("MINIMAL_SAMPLE_SIZE", 10))
