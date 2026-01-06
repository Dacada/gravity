from pydantic import BaseModel


class PauseIcon(BaseModel):
    color: tuple[int, int, int]
    bar_width: int
    bar_height: int
    gap: int


class TargetIcon(BaseModel):
    color: tuple[int, int, int]
    size: int
    center_radius: int
    corner_length: int
    corner_thickness: int


class ComIcon(BaseModel):
    color: tuple[int, int, int]
    center_radius: int
    center_thickness: int
    dot_radius: int
    dot_distance: int
    dot_count: int


class FreeCamIcon(BaseModel):
    color: tuple[int, int, int]
    tri_size: int
    circle_radius: int
    line_width: int


class Inspector(BaseModel):
    bg_color: tuple[int, int, int]
    border_color: tuple[int, int, int]
    text_color: tuple[int, int, int]
    padding: tuple[int, int]
    control_separation: int


class SimulatedEntity(BaseModel):
    radius: int
    reticle_padding: int
    reticle_width: int
    reticle_color: tuple[int, int, int]


class Name(BaseModel):
    diagonal_length: int
    horizontal_length: int
