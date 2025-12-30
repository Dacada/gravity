from enum import Enum, auto
from typing import Optional

import pygame

from gravity.physics import PointMass, PointMassSimulator
from gravity.camera import Camera


class CameraFollowMode(Enum):
    NONE = auto()
    SELECTED_POINT_MASS = auto()
    CENTER_OF_MASS = auto()


class CameraController:
    def __init__(self):
        self._pan_direction_x = 0
        self._pan_direction_y = 0
        self._zoom_direction = 0
        self._follow_mode = CameraFollowMode.NONE

    def set_pan_direction_left(self):
        self._pan_direction_x -= 1

    def reset_pan_direction_left(self):
        if self._pan_direction_x < 0:
            self._pan_direction_x = 0

    def set_pan_direction_right(self):
        self._pan_direction_x += 1

    def reset_pan_direction_right(self):
        if self._pan_direction_x > 0:
            self._pan_direction_x = 0

    def set_pan_direction_up(self):
        self._pan_direction_y -= 1

    def reset_pan_direction_up(self):
        if self._pan_direction_y < 0:
            self._pan_direction_y = 0

    def set_pan_direction_down(self):
        self._pan_direction_y += 1

    def reset_pan_direction_down(self):
        if self._pan_direction_y > 0:
            self._pan_direction_y = 0

    def set_zoom_direction_in(self):
        self._zoom_direction = 1

    def set_zoom_direction_out(self):
        self._zoom_direction = -1

    def reset_zoom_direction(self):
        self._zoom_direction = 0

    def set_follow_mode_selected_mass(self):
        self._follow_mode = CameraFollowMode.SELECTED_POINT_MASS

    def set_follow_mode_center_of_mass(self):
        self._follow_mode = CameraFollowMode.CENTER_OF_MASS

    def unset_follow_mode(self):
        self._follow_mode = CameraFollowMode.NONE

    def is_follow_mode_set(self):
        return self._follow_mode != CameraFollowMode.NONE

    def is_follow_selected_mass_mode(self) -> bool:
        return self._follow_mode == CameraFollowMode.SELECTED_POINT_MASS

    def is_follow_center_of_mass_mode(self) -> bool:
        return self._follow_mode == CameraFollowMode.CENTER_OF_MASS

    def update(
        self,
        selected: Optional[PointMass],
        camera: Camera,
        points: PointMassSimulator,
        dt: float,
    ) -> None:
        if not self.is_follow_mode_set():
            if self._pan_direction_x or self._pan_direction_y:
                camera_dir = pygame.Vector2(
                    self._pan_direction_x, self._pan_direction_y
                )
                camera_dir = camera_dir.normalize()
                camera.pan(camera_dir, dt)

        if self._zoom_direction:
            camera.zoom(self._zoom_direction, dt)

        if self.is_follow_selected_mass_mode():
            if selected is None:
                self._follow_mode = CameraFollowMode.NONE
            else:
                camera.set_world_center(selected.pos.copy())

        if self.is_follow_center_of_mass_mode():
            camera.set_world_center(points.center_of_mass())
