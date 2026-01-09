from pydantic import BaseModel

from gravity.config.parse import RationalFloat
from gravity.types import AnchorType


class Icon(BaseModel):
    offset_ratio: tuple[RationalFloat, RationalFloat]
    size: tuple[int, int]
    anchor: AnchorType


class Layout(BaseModel):
    width: int
    height: int
    inspector_ratio: RationalFloat
    pause_icon: Icon
    camera_state_icon: Icon
    chrono_trigger_icon: Icon
