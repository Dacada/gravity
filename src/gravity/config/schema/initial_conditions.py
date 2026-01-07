from typing import Annotated, Literal, Optional, Union

from pydantic.fields import Field
from pydantic.main import BaseModel


class LiteralProperty(BaseModel):
    type: Literal["literal"]
    value: float


Property = Annotated[Union[LiteralProperty], Field(discriminator="type")]


class SimpleEntity(BaseModel):
    type: Literal["simple"]
    mass: Property


class SystemEntity(BaseModel):
    type: Literal["system"]
    system: "System"


Entity = Annotated[Union[SimpleEntity, SystemEntity], Field(discriminator="type")]


class EntityInstance(BaseModel):
    entity: Entity
    position: tuple[Property, Property]
    velocity: tuple[Property, Property]


class System(BaseModel):
    entities: list[EntityInstance]


class InitialConditions(BaseModel):
    root: SystemEntity
    seed: Optional[int]
