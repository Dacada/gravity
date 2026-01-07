from typing import Annotated, Literal, Optional, Union

from pydantic.fields import Field
from pydantic.main import BaseModel


class LiteralProperty(BaseModel):
    type: Literal["literal"]
    value: float


class GaussProperty(BaseModel):
    type: Literal["gaussian"]
    mean: float
    sigma: float


class GaussAbsoluteProperty(BaseModel):
    type: Literal["gaussian-absolute"]
    mean: float
    sigma: float


Property = Annotated[Union[LiteralProperty, GaussProperty, GaussAbsoluteProperty], Field(discriminator="type")]


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


Entity = Annotated[
    Union[SimpleEntity, SystemEntity, CloudEntity], Field(discriminator="type")
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
