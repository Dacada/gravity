from gravity.physics import PointMassSimulator
from gravity.ui import InspectorUIState, PauseController, CursorUIController
from gravity.camera import Camera, CameraController

from typing import Optional


class GameState:
    def __init__(
        self,
        points: PointMassSimulator,
        inspector: InspectorUIState,
        camera: Camera,
        camera_controller: CameraController,
        pause_controller: PauseController,
        cursor_ui_controller: CursorUIController,
        physics_timedelta: float,
        physics_step_alloted_time_clamp: float,
    ):
        self._physics_timedelta = physics_timedelta
        self._physics_step_alloted_time_clamp = physics_step_alloted_time_clamp

        self.points = points
        self.inspector = inspector
        self.camera = camera
        self.camera_controller = camera_controller
        self.pause_controller = pause_controller
        self.cursor_ui_controller = cursor_ui_controller

        self._running = True
        self._physics_loop_accumulator = 0.0
        self._resize: Optional[tuple[int, int]] = None

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def resize(self, width: int, height: int) -> None:
        self._resize = (width, height)

    def query_resize(self) -> Optional[tuple[int, int]]:
        ret = self._resize
        self._resize = None
        return ret

    def update(self, dt: float) -> None:
        self.pause_controller.update(dt)

        if not self.pause_controller.is_paused():
            self._update_physics_loop(dt)

        p = self.inspector.get_selected_point()
        if p is not None:
            idx = self.points.index(p)
            if idx is None:
                self.inspector.unselect_point()

        self.camera_controller.update(p, self.camera, self.points, dt)

    def _update_physics_loop(self, dt: float) -> None:
        if dt > self._physics_step_alloted_time_clamp:
            dt = self._physics_step_alloted_time_clamp

        self._physics_loop_accumulator += dt
        while self._physics_loop_accumulator >= self._physics_timedelta:
            self.points.update(self._physics_timedelta)
            self._physics_loop_accumulator -= self._physics_timedelta
