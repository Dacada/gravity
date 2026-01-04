from typing import Any, Optional, Self, cast, overload

import pygame

from gravity.types import Color


class _TrackedField[T]:
    def __init__(self, gating_attr_name: str) -> None:
        self.gating_attr_name = gating_attr_name

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.flag_name = f"_{name}_modified"

    @overload
    def __get__(self, instance: None, owner: type) -> Self: ...

    @overload
    def __get__(self, instance: Any, owner: type) -> T: ...

    def __get__(self, instance: Any, owner: type) -> T | Self:
        if instance is None:
            return self

        try:
            return cast(T, instance.__dict__[self.name])
        except KeyError:
            raise AttributeError(f"{owner.__name__}.{self.name} has not been set")

    def __set__(self, instance: Any, value: T) -> None:
        tracking = getattr(instance, self.gating_attr_name, False)
        if tracking:
            instance.__dict__[self.flag_name] = True
        instance.__dict__[self.name] = value

    def was_modified(self, instance: Any) -> bool:
        return cast(bool, instance.__dict__.get(self.flag_name, False))

    def clear_modified(self, instance: Any) -> None:
        instance.__dict__[self.flag_name] = False


class SimulatedEntity:
    x: _TrackedField[float] = _TrackedField("_tracking_enabled")
    y: _TrackedField[float] = _TrackedField("_tracking_enabled")
    vx: _TrackedField[float] = _TrackedField("_tracking_enabled")
    vy: _TrackedField[float] = _TrackedField("_tracking_enabled")
    mass: _TrackedField[float] = _TrackedField("_tracking_enabled")

    color: _TrackedField[Color] = _TrackedField("_tracking_enabled")
    name: _TrackedField[Optional[str]] = _TrackedField("_tracking_enabled")

    def __init__(
        self,
        pos: pygame.Vector2,
        vel: pygame.Vector2,
        mass: float,
        color: Color,
        name: Optional[str],
        index: int,
    ) -> None:
        self.pos = pos
        self.vel = vel
        self.mass = mass
        self.color = color
        self.name = name
        self._index = index
        self._tracking_enabled = True

    @property
    def pos(self) -> pygame.Vector2:
        return pygame.Vector2(self.x, self.y)

    @pos.setter
    def pos(self, val: pygame.Vector2) -> None:
        self.x = val.x
        self.y = val.y

    @property
    def vel(self) -> pygame.Vector2:
        return pygame.Vector2(self.vx, self.vy)

    @vel.setter
    def vel(self, val: pygame.Vector2) -> None:
        self.vx = val.x
        self.vy = val.y

    @property
    def index(self) -> int:
        return self._index
