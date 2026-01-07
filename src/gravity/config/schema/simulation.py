from typing import Optional

from pydantic import BaseModel

from gravity.config.parse import RationalFloat
from gravity.config.schema.initial_conditions import InitialConditions
from gravity.types import Color


class Control(BaseModel):
    physics_timedelta: RationalFloat
    physics_step_alloted_time_clamp: RationalFloat


class Model(BaseModel):
    default_simulated_entity_color: Color


class Physics(BaseModel):
    gravitational_constant: float
    softening_factor: float
    enable_merging: bool
    merge_distance_squared: float


class Simulation(BaseModel):
    control: Control
    model: Model
    physics: Physics
    initial_conditions: Optional[InitialConditions]
