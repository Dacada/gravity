from dataclasses import dataclass
from typing import Optional

import pygame

from gravity.types import Color


@dataclass
class SimulatedEntity:
    pos: pygame.Vector2
    vel: pygame.Vector2
    mass: float

    color: Color
    name: Optional[str]

    index: int

    @property
    def x(self) -> float:
        return self.pos.x

    @property
    def y(self) -> float:
        return self.pos.y

    @property
    def vx(self) -> float:
        return self.vel.x

    @property
    def vy(self) -> float:
        return self.vel.y
