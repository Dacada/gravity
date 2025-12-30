from dataclasses import dataclass

import pygame


@dataclass
class PointMass:
    pos: pygame.Vector2
    vel: pygame.Vector2
    mass: float

    @property
    def x(self) -> float:
        return self.pos.x

    @x.setter
    def x(self, value: float) -> None:
        self.pos.x = value

    @property
    def y(self) -> float:
        return self.pos.y

    @y.setter
    def y(self, value: float) -> None:
        self.pos.y = value

    @property
    def vx(self) -> float:
        return self.vel.x

    @vx.setter
    def vx(self, value: float) -> None:
        self.vel.x = value

    @property
    def vy(self) -> float:
        return self.vel.y

    @vy.setter
    def vy(self, value: float) -> None:
        self.vel.y = value
