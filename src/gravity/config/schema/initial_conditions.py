from typing import Annotated, Literal, Optional, Union

from pydantic.fields import Field
from pydantic.main import BaseModel
from gravity.config.parse import IrrationalFloat


class LiteralProperty(BaseModel):
    type: Literal["literal"]
    value: IrrationalFloat


class GaussProperty(BaseModel):
    type: Literal["gaussian"]
    mean: IrrationalFloat
    sigma: IrrationalFloat


class GaussAbsoluteProperty(BaseModel):
    type: Literal["gaussian-absolute"]
    mean: IrrationalFloat
    sigma: IrrationalFloat


class UniformProperty(BaseModel):
    type: Literal["uniform"]
    start: IrrationalFloat
    end: IrrationalFloat


Property = Annotated[
    Union[LiteralProperty, GaussProperty, GaussAbsoluteProperty, UniformProperty],
    Field(discriminator="type"),
]


class BoxRegion(BaseModel):
    shape: Literal["box"]
    disorder: float
    width: float
    height: float


Region = Annotated[Union[BoxRegion], Field(discriminator="shape")]


class SimpleEntity(BaseModel):
    type: Literal["simple"]
    mass: Property


class SystemEntity(BaseModel):
    type: Literal["system"]
    system: "System"


class CloudEntity(BaseModel):
    type: Literal["cloud"]
    count: int
    region: Region
    mass: Property
    velocity: tuple[Property, Property]


class BinarySystemEntity(BaseModel):
    type: Literal["binary"]

    primary: "Entity"
    secondary: "Entity"

    # a>0
    semi_major_axis: Property
    # 0<=e<1 (e>=1 -> flyby)
    eccentricity: Property
    # angle in radians, 0<=f<2pi
    phase: Property
    # andle in radians, 0<=theta<2pi
    orientation: Property


Entity = Annotated[
    Union[SimpleEntity, SystemEntity, CloudEntity, BinarySystemEntity],
    Field(discriminator="type"),
]


class EntityInstance(BaseModel):
    entity: Entity
    position: tuple[Property, Property]
    velocity: tuple[Property, Property]


class System(BaseModel):
    entities: list[EntityInstance]


class InitialConditions(BaseModel):
    root: System
    seed: Optional[int]
