from typing import Iterable, Optional, Self

import pygame

from gravity.camera import Camera
from gravity.config.schema import AppConfigCursorUi
from gravity.layout import Layout
from gravity.physics import PointMass


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
        self, points: Iterable[PointMass], camera: Camera, pos_cursor: pygame.Vector2
    ) -> Optional[PointMass]:
        best = None
        best_dist = self._selection_distance_squared

        for p in points:
            point = camera.world_to_screen(p.pos)
            d = pos_cursor.distance_squared_to(point)
            if d < best_dist:
                best = p
                best_dist = d

        return best
