import os
from canary_tester.types import GlobalConfig


def to_int(value, default: int = 0):
    try:
        return int(value)
    except ValueError:
        return default


def is_int_castable(x):
    try:
        int(x)  # Attempt to cast x to int
        return True
    except ValueError:
        return False


def is_float_castable(x):
    try:
        float(x)  # Attempt to cast x to float
        return True
    except ValueError:
        return False


def load_environment_variable() -> GlobalConfig:
    return GlobalConfig(
        THANOS_QUERIER_ENDPOINT=os.getenv(
            "THANOS_QUERIER_ENDPOINT", "http://localhost:9090"
        ),
        AUTH_COOKIE=os.getenv("AUTH_COOKIE", ""),
        PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME=os.getenv(
            "PREDICTABLE_ARRIVAL_TESTER_STABILIZATION_TIME", "30"
        ),
        PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME=os.getenv(
            "PREDICTABLE_ARRIVAL_TESTER_MONITORING_TIME", "300"
        ),
        CONFIG_FILE_PATH=os.getenv("CONFIG_FILE_PATH", "config.yaml"),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "20"),
        VERIFY_SSL=os.getenv("VERIFY_SSL", "True"),
        # 8 has been proven an reasonable number. It is a tradeoff
        # between early stopping and rubustness
        MINIMAL_SAMPLE_SIZE=os.getenv("MINIMAL_SAMPLE_SIZE", "8"),
    )


def convert_timestamp_into_seconds(timestamp: int) -> int:
    if timestamp > 1_000_000_000_000:
        return timestamp // 1_000_000_000
    if timestamp > 1_000_000_000:
        return timestamp // 1_000_000
    if timestamp > 1_000_000:
        return timestamp // 1_000
    return timestamp
