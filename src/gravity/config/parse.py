import math
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


class IrrationalFloat(float):
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

        if isinstance(value, str):
            return cls._parse_expr(value)

        raise ValueError("Invalid rational value")

    @classmethod
    def _parse_expr(cls, value: Any) -> Self:
        if isinstance(value, (int, float)):
            return cls(value)

        if not isinstance(value, str):
            raise ValueError("Invalid expr literal")

        text = value.strip()

        try:
            # ehrm, askshually

            # [c for c in pi.__class__.__bases__[0].__subclasses__() if c.__name__ == "BuiltinImporter"][0].load_module("builtins").print("hello")

            # yeah i don't care, this application does not need to be secure, it's a physics toy that runs on your own
            # machine, i'm only setting globals to math's dict for pure convinience not for security
            return cls(eval(text, globals=math.__dict__))
        except Exception as e:
            raise ValueError("failed to evaluate expr literal") from e
