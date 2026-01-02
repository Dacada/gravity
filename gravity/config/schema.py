from typing import Any, Self, Type

from pydantic import BaseModel
from pydantic.annotated_handlers import GetCoreSchemaHandler
from pydantic_core import core_schema

from gravity.types import AnchorType, Color


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


class AppConfigCore(BaseModel):
    target_framerate: int


class AppConfigLayoutIcon(BaseModel):
    offset_ratio: tuple[RationalFloat, RationalFloat]
    size: tuple[int, int]
    anchor: AnchorType


class AppConfigLayout(BaseModel):
    width: int
    height: int
    inspector_ratio: RationalFloat
    pause_icon: AppConfigLayoutIcon
    camera_state_icon: AppConfigLayoutIcon


class AppConfigSimulationControl(BaseModel):
    physics_timedelta: RationalFloat
    physics_step_alloted_time_clamp: RationalFloat


class AppConfigSimulationModel(BaseModel):
    default_simulated_entity_color: Color


class AppConfigSimulationPhysics(BaseModel):
    gravitational_constant: float
    softening_factor: float
    merge_distance_squared: float


class AppConfigSimulation(BaseModel):
    control: AppConfigSimulationControl
    model: AppConfigSimulationModel
    physics: AppConfigSimulationPhysics


class AppConfigUiFormat(BaseModel):
    position_format: str
    velocity_format: str
    mass_format: str


class AppConfigCamera(BaseModel):
    pan_speed: float
    zoom_factor: float


class AppConfigPauseAnimation(BaseModel):
    speed: float


class AppConfigCursorUi(BaseModel):
    viewport_clickable_margin: int
    selection_distance_squared: int


class AppConfigRenderStylePauseIcon(BaseModel):
    color: tuple[int, int, int]
    bar_width: int
    bar_height: int
    gap: int


class AppConfigRenderStyleTargetIcon(BaseModel):
    color: tuple[int, int, int]
    size: int
    center_radius: int
    corner_length: int
    corner_thickness: int


class AppConfigRenderStyleComIcon(BaseModel):
    color: tuple[int, int, int]
    center_radius: int
    center_thickness: int
    dot_radius: int
    dot_distance: int
    dot_count: int


class AppConfigRenderStyleFreeCamIcon(BaseModel):
    color: tuple[int, int, int]
    tri_size: int
    circle_radius: int
    line_width: int


class AppConfigRenderStyleInspector(BaseModel):
    bg_color: tuple[int, int, int]
    border_color: tuple[int, int, int]
    text_color: tuple[int, int, int]
    padding: tuple[int, int]
    control_separation: int


class AppConfigRenderStyleSimulatedEntity(BaseModel):
    radius: int
    reticle_padding: int
    reticle_width: int
    reticle_color: tuple[int, int, int]


class AppConfigRenderStyleName(BaseModel):
    diagonal_length: int
    horizontal_length: int


class AppConfigRenderStyles(BaseModel):
    pause_icon: AppConfigRenderStylePauseIcon
    target_icon: AppConfigRenderStyleTargetIcon
    com_icon: AppConfigRenderStyleComIcon
    freecam_icon: AppConfigRenderStyleFreeCamIcon
    inspector: AppConfigRenderStyleInspector
    simulated_entity: AppConfigRenderStyleSimulatedEntity
    name: AppConfigRenderStyleName


class AppConfigRender(BaseModel):
    styles: AppConfigRenderStyles
    font_name: str
    font_size: int


class AppConfig(BaseModel):
    core: AppConfigCore
    layout: AppConfigLayout
    simulation: AppConfigSimulation
    ui_format: AppConfigUiFormat
    camera: AppConfigCamera
    pause_animation: AppConfigPauseAnimation
    cursor_ui: AppConfigCursorUi
    render: AppConfigRender
