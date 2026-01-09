from pydantic import BaseModel


class Format(BaseModel):
    position_format: str
    velocity_format: str
    mass_format: str


class Cursor(BaseModel):
    viewport_clickable_margin: int
    selection_distance_squared: int


class AnimationInfo(BaseModel):
    speed: float


class Animation(BaseModel):
    pause: AnimationInfo
    chrono_trigger: AnimationInfo


class Ui(BaseModel):
    animation: Animation
    cursor: Cursor
    format: Format
