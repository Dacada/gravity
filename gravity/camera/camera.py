import pygame

from gravity.ui.layout import Layout


class Camera:
    def __init__(self, layout: Layout, pan_speed: float, zoom_factor: float) -> None:
        self._layout = layout
        self._pan_speed = pan_speed
        self._zoom_factor = zoom_factor

        self._world_center = pygame.Vector2(0, 0)
        self._zoom = 1.0

    def world_to_screen(self, world_pos: pygame.Vector2) -> pygame.Vector2:
        return (
            world_pos - self._world_center
        ) * self._zoom + self._layout.viewport.center

    def screen_to_world(self, screen_pos: pygame.Vector2) -> pygame.Vector2:
        return (
            screen_pos - self._layout.viewport.center
        ) / self._zoom + self._world_center

    def pan(self, direction: pygame.Vector2, dt: float) -> None:
        self._world_center += direction * dt * self._pan_speed

    def set_world_center(self, world_center: pygame.Vector2):
        self._world_center = world_center

    def zoom(self, direction: int, dt: float) -> None:
        self._zoom *= self._zoom_factor ** (float(direction) * dt)
