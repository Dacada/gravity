from typing import Annotated, Any, Literal, Optional, Union

from pydantic import RootModel, field_validator
from pydantic.fields import Field
from pydantic.main import BaseModel

from gravity.config.parse import IrrationalFloat
from gravity.types import Color


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


PropertyUnion = Annotated[
    Union[LiteralProperty, GaussProperty, GaussAbsoluteProperty, UniformProperty],
    Field(discriminator="type"),
]


class Property(RootModel[PropertyUnion]):
    @field_validator("root", mode="before")
    @classmethod
    def coerce_float(cls, v: Any) -> Any:
        if isinstance(v, (int, float)):
            return {"type": "literal", "value": float(v)}
        return v


class BoxRegion(BaseModel):
    shape: Literal["box"]
    disorder: float
    width: float
    height: float


Region = Annotated[Union[BoxRegion], Field(discriminator="shape")]


class SimpleEntity(BaseModel):
    type: Literal["simple"]
    mass: Property
    name: Optional[str] = None
    color: Optional[Color] = None


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
    funny: bool = False
    seed: Optional[int]
