from pydantic import BaseModel


class Format(BaseModel):
    position_format: str
    velocity_format: str
    mass_format: str


class Cursor(BaseModel):
    viewport_clickable_margin: int
    selection_distance_squared: int


class PauseAnimation(BaseModel):
    speed: float


class Ui(BaseModel):
    pause_animation: PauseAnimation
    cursor: Cursor
    format: Format
