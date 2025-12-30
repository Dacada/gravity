from gravity.ui.layout import Layout
from typing import Iterable, Optional
from gravity.physics import PointMass
from gravity.camera import Camera
import pygame


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

    def is_viewport_click_allowed(self, pos: tuple[int, int]):
        rect = self._layout.viewport
        return (
            rect.collidepoint(pos)
            and pos[0] < rect.right - self._viewport_clickable_margin
        )

    def find_closest_point_screen_space(
        self, points: Iterable[PointMass], camera: Camera, pos_cursor: tuple[int, int]
    ) -> Optional[PointMass]:
        pos = pygame.Vector2(*pos_cursor)
        best = None
        best_dist = self._selection_distance_squared

        for p in points:
            point = camera.world_to_screen(p.pos)
            d = pos.distance_squared_to(point)
            if d < best_dist:
                best = p
                best_dist = d

        return best
