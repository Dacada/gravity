from typing import Optional, Self

import pygame

from gravity.camera import Camera, CameraController
from gravity.config.schema import AppConfigSimulationControl
from gravity.physics import SimulationController
from gravity.physics.controller import SimulationController
from gravity.ui import CursorUIController, InspectorUIState, PauseController


class GameState:
    def __init__(
        self,
        simulation: SimulationController,
        inspector: InspectorUIState,
        camera: Camera,
        camera_controller: CameraController,
        pause_controller: PauseController,
        cursor_ui_controller: CursorUIController,
    ):
        self.simulation = simulation
        self.inspector = inspector
        self.camera = camera
        self.camera_controller = camera_controller
        self.pause_controller = pause_controller
        self.cursor_ui_controller = cursor_ui_controller

        self._running = True
        self._physics_loop_accumulator = 0.0
        self._resize: Optional[pygame.Vector2] = None

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def resize(self, width: int, height: int) -> None:
        self._resize = pygame.Vector2(width, height)

    def query_resize(self) -> Optional[pygame.Vector2]:
        ret = self._resize
        self._resize = None
        return ret

    def update(self, dt: float) -> None:
        self.pause_controller.update(dt)

        if not self.pause_controller.is_paused():
            self.simulation.update()

        handle = self.inspector.get_selected_entity_handle()
        if handle is not None:
            if not self.simulation.is_handle_valid(handle):
                self.inspector.unselect_entity_handle()

        self.camera_controller.update(dt, self.camera, self.simulation, handle)
