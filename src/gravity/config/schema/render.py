from pydantic import BaseModel

from gravity.config.parse import RationalFloat
from gravity.config.schema.render_styles import (
    ChronoTriggerIcon,
    ComIcon,
    FreeCamIcon,
    Inspector,
    Name,
    PauseIcon,
    SimulatedEntity,
    TargetIcon,
)
from gravity.config.schema.render_styles import Trail as TrailStyle


class Trail(BaseModel):
    sampling_period: RationalFloat
    sample_buffer_size: int


class Effects(BaseModel):
    trail: Trail


class Styles(BaseModel):
    pause_icon: PauseIcon
    target_icon: TargetIcon
    com_icon: ComIcon
    freecam_icon: FreeCamIcon
    chrono_trigger_icon: ChronoTriggerIcon
    inspector: Inspector
    simulated_entity: SimulatedEntity
    name: Name
    trail: TrailStyle


class Render(BaseModel):
    styles: Styles
    font_name: str
    font_size: int
    effects: Effects
