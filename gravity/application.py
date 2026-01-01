import logging

import pygame

from gravity.camera import Camera, CameraController
from gravity.config import AppConfig
from gravity.core import EventHandler, GameState
from gravity.layout import Layout
from gravity.physics import PointMassSimulator
from gravity.render import Renderer
from gravity.ui import CursorUIController, InspectorUIState, PauseController


class Application:
    def __init__(
        self,
        layout: Layout,
        game: GameState,
        events: EventHandler,
        renderer: Renderer,
        target_framerate: int,
    ):
        self._target_framerate = target_framerate
        self._layout = layout
        self._game = game
        self._events = events
        self._renderer = renderer

    def _initialize(self) -> None:
        logging.basicConfig(level=logging.INFO)

        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Gravity")
        self._renderer.initialize()

        # temp, for quickly setting up a test state
        import random

        w = 300
        h = 300
        for i in range(50):
            self._game.points.create(
                pygame.Vector2(
                    random.uniform(-w // 2, w // 2),
                    random.uniform(-h // 2, h // 2),
                ),
                abs(random.gauss(mu=0, sigma=1)),
            )

    def _deinitialize(self) -> None:
        pygame.quit()
        logging.shutdown()

    def run(self) -> int:
        self._initialize()

        clock = pygame.time.Clock()
        while self._game.is_running():
            dt = clock.get_time() / 1000.0
            self._events.handle_events()
            self._game.update(dt)
            self._renderer.render(self._game)
            clock.tick(self._target_framerate)

        self._deinitialize()
        return 0


def build_application(config: AppConfig) -> Application:
    target_framerate = config.core.target_framerate
    layout = Layout.from_config(config.layout)
    points = PointMassSimulator.from_config(config.physics_simulation)
    inspector = InspectorUIState.from_config(config.ui_format)
    camera = Camera.from_config(config.camera, layout)
    camera_controller = CameraController()
    pause_controller = PauseController.from_config(config.pause_animation)
    cursor_ui_controller = CursorUIController.from_config(config.cursor_ui, layout)
    game = GameState.from_config(
        config.simulation_control,
        points,
        inspector,
        camera,
        camera_controller,
        pause_controller,
        cursor_ui_controller,
    )
    events = EventHandler(game, layout)
    renderer = Renderer.from_config(config.render, layout)
    return Application(
        layout, game, events, renderer, target_framerate=target_framerate
    )
