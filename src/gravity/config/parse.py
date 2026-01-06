from typing import Any, Self, Type

from pydantic.annotated_handlers import GetCoreSchemaHandler
from pydantic_core import core_schema


class RationalFloat(float):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_before_validator_function(
            cls._validate,
            core_schema.float_schema(),
        )

    @classmethod
    def _validate(cls, value: Any) -> Self:
        if isinstance(value, (int, float)):
            return cls(value)

        if isinstance(value, dict):
            if set(value.keys()) != {"ratio"}:
                raise ValueError("Invalid rational object")
            return cls._parse_ratio(value["ratio"])

        raise ValueError("Invalid rational value")

    @classmethod
    def _parse_ratio(cls, value: Any) -> Self:
        if isinstance(value, (int, float)):
            return cls(value)

        if not isinstance(value, str):
            raise ValueError("Invalid ratio literal")

        text = value.strip()

        # Percentage
        if text.endswith("%"):
            return cls(float(text[:-1]) / 100.0)

        # Fraction
        if "/" in text:
            num, den = text.split("/", 1)
            return cls(float(num) / float(den))

        raise ValueError(f"Invalid ratio format: {value!r}")
