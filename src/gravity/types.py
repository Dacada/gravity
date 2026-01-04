from enum import Enum
from typing import NamedTuple, Self


class Color(NamedTuple):
    r: int
    g: int
    b: int

    def merge(self, other: Self) -> Self:
        return self.__class__(
            (self.r + other.r) // 2,
            (self.g + other.g) // 2,
            (self.b + other.b) // 2,
        )

    @classmethod
    def from_str(cls, text: str) -> Self:
        text = text.strip()

        if len(text) != 6:
            raise ValueError("color spec is not 6 characters")

        return cls(
            int(text[0:2], 16),
            int(text[2:4], 16),
            int(text[4:6], 16),
        )

    def as_str(self) -> str:
        return "".join(format(x, "02x") for x in self)


class AnchorType(str, Enum):
    TOP_LEFT = "TOP_LEFT"
    TOP_RIGHT = "TOP_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
