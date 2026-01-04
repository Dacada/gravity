import math
from typing import Optional, Self

import pygame

from gravity.camera import Camera
from gravity.config.schema import AppConfigCursorUi
from gravity.layout import Layout
from gravity.physics import SimulatedEntityHandle, SimulationController


class CursorUIController:
    def __init__(
        self,
        layout: Layout,
        viewport_clickable_margin: int,
        selection_distance_squared: float,
    ):
        self._layout = layout
        self._viewport_clickable_margin = viewport_clickable_margin
        self._selection_distance_squared = selection_distance_squared

    @classmethod
    def from_config(cls, cfg: AppConfigCursorUi, layout: Layout) -> Self:
        return cls(
            layout,
            cfg.viewport_clickable_margin,
            cfg.selection_distance_squared,
        )

    def is_viewport_click_allowed(self, pos: pygame.Vector2) -> bool:
        rect = self._layout.viewport
        return (
            rect.collidepoint(pos)
            and pos[0] < rect.right - self._viewport_clickable_margin
        )

    def find_closest_point_screen_space(
        self,
        camera: Camera,
        simulation: SimulationController,
        pos_cursor: pygame.Vector2,
    ) -> Optional[SimulatedEntityHandle]:
        r = math.sqrt(self._selection_distance_squared)
        box = pygame.Rect(
            pos_cursor.x - r,
            pos_cursor.y - r,
            2 * r,
            2 * r,
        )

        topleft = camera.screen_to_world(pygame.Vector2(box.topleft))
        bottomright = camera.screen_to_world(pygame.Vector2(box.bottomright))
        point_iterator = simulation.entities_in_rect_iter(topleft, bottomright)

        best = None
        best_dist = self._selection_distance_squared

        for handle in point_iterator:
            entity = simulation.get(handle)
            if entity is None:
                continue
            pos = camera.world_to_screen(entity.pos)
            d = pos_cursor.distance_squared_to(pos)
            if d < best_dist:
                best = handle
                best_dist = d

        return best
