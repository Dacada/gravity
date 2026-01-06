from typing import Iterator, Optional, Self

import pygame

from gravity.config.schema.simulation import Physics as PhysicsConfig
from gravity.physics._core import MergeInfo, NativeSimulationCore, SimulatedEntityHandle


class SimulationCore(NativeSimulationCore):
    @classmethod
    def from_config(cls, cfg: PhysicsConfig) -> Self:
        return cls(
            cfg.gravitational_constant,
            cfg.softening_factor,
            cfg.enable_merging,
            cfg.merge_distance_squared,
        )

    def create(self, pos: pygame.Vector2, vel: pygame.Vector2, mass: float) -> SimulatedEntityHandle:  # type: ignore[override]
        return super().create(pos.x, pos.y, vel.x, vel.y, mass)

    def get(  # type: ignore[override]
        self, handle: SimulatedEntityHandle
    ) -> Optional[tuple[pygame.Vector2, pygame.Vector2, float]]:
        res = super().get(handle)
        if res is None:
            return None

        posx, posy, velx, vely, mass = res
        return (
            pygame.Vector2(posx, posy),
            pygame.Vector2(velx, vely),
            mass,
        )

    def set_position(self, handle: SimulatedEntityHandle, pos: pygame.Vector2) -> None:  # type: ignore[override]
        super().set_position(handle, pos.x, pos.y)

    def set_velocity(self, handle: SimulatedEntityHandle, vel: pygame.Vector2) -> None:  # type: ignore[override]
        super().set_velocity(handle, vel.x, vel.y)

    def entities_in_rect_iter(  # type: ignore[override]
        self, topleft: pygame.Vector2, bottomright: pygame.Vector2
    ) -> Iterator[SimulatedEntityHandle]:
        """
        NOTE: mutating the object during iteration will RESULT IN UNDEFINED BEHAVIOR AT THE C LAYER
        """
        return super().entities_in_rect_iter(
            topleft.x, topleft.y, bottomright.x, bottomright.y
        )

    def center_of_mass(self) -> pygame.Vector2:  # type: ignore[override]
        x, y = super().center_of_mass()
        return pygame.Vector2(x, y)
