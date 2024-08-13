from typing import TypedDict
from pydantic import BaseModel, Field
from canary_tester.types import ComparisonDirection, TestArrivalType


class SingleTestConfig(BaseModel):
    """A class that represents the configuration of a single FrequencyTTestOneSided test"""

    name: str
    query: str = Field(
        pattern=r"(\w+) \((\w+(?:_\w+)*)\) by\((\w+(?:, \w+)*)\)|(\w+(?:_\w+)*)"
    )
    significance_level: float
    minimal_effect_size_of_interest: float
    type_arrival: TestArrivalType
    direction: ComparisonDirection


SingleTestConfigType = TypedDict(
    "ConfigType",
    {
        "name": str,
        "query": str,
        "significance_level": float,
        "minimal_effect_size_of_interest": float,
        "type_arrival": TestArrivalType,
        "direction": ComparisonDirection,
    },
)


class TestConfigList(BaseModel):
    tests: list[SingleTestConfig]


TestConfigListType = TypedDict(
    "TestConfigListType", {"tests": list[SingleTestConfigType]}
)
