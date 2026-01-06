from pydantic import BaseModel

from gravity.config.schema.render_styles import (
    ComIcon,
    FreeCamIcon,
    Inspector,
    Name,
    PauseIcon,
    SimulatedEntity,
    TargetIcon,
)


class Styles(BaseModel):
    pause_icon: PauseIcon
    target_icon: TargetIcon
    com_icon: ComIcon
    freecam_icon: FreeCamIcon
    inspector: Inspector
    simulated_entity: SimulatedEntity
    name: Name


class Render(BaseModel):
    styles: Styles
    font_name: str
    font_size: int
