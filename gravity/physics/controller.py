from typing import Iterator, Optional, Self

import pygame

from gravity.config.schema import AppConfigSimulation
from gravity.physics.core import SimulatedEntityHandle
from gravity.physics.model import SimulatedEntity


class SimulationController:
    @classmethod
    def from_config(cls, cfg: AppConfigSimulation) -> Self:
        pass

    def create(
        self, pos: Optional[pygame.Vector2] = None, mass: Optional[float] = None
    ) -> SimulatedEntityHandle:
        pass

    def delete(self, handle: SimulatedEntityHandle) -> None:
        pass

    def get(self, handle: SimulatedEntityHandle) -> Optional[SimulatedEntity]:
        pass

    def update(self) -> None:
        pass

    def center_of_mass(self) -> pygame.Vector2:
        pass

    def entities_in_rect_iter(
        self, topleft: pygame.Vector2, bottomright: pygame.Vector2
    ) -> Iterator[SimulatedEntityHandle]:
        pass

    def is_handle_valid(self, handle: SimulatedEntityHandle) -> bool:
        pass

    def get_first_point(self) -> Optional[SimulatedEntityHandle]:
        pass

    def get_last_point(self) -> Optional[SimulatedEntityHandle]:
        pass

    def get_next_point(self, handle: SimulatedEntityHandle) -> SimulatedEntityHandle:
        pass

    def get_prev_point(self, handle: SimulatedEntityHandle) -> SimulatedEntityHandle:
        pass
