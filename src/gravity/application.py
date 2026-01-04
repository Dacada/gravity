import logging
import random
import sys
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Iterator, Optional

import pygame

from gravity.camera import Camera, CameraController
from gravity.config import AppConfig
from gravity.core import EventHandler, GameState
from gravity.layout import Layout
from gravity.physics import (
    SimulationController,
    SimulationCore,
    SimulationEntityDescriptor,
)
from gravity.render import Renderer
from gravity.ui import CursorUIController, InspectorUIState, PauseController

logger = logging.getLogger(__name__)


class _Timer:
    def __init__(self, count: int) -> None:
        self._target_count = count
        self._current_count = 0
        self._samples: dict[str, deque[float]] = {}

    def count(self) -> None:
        self._current_count += 1

    @contextmanager
    def time(self, name: str) -> Iterator[None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            t1 = time.perf_counter()
            self.sample(name, t1 - t0)

    def sample(self, name: str, sample: float) -> None:
        samples = self._samples.setdefault(name, deque())
        samples.append(sample)

        if len(samples) > self._target_count:
            samples.popleft()

    def average(self, name: str) -> float:
        samples = self._samples.get(name)
        if samples is None:
            return 0.0
        res = sum(samples) / len(samples)
        return res

    def reset(self) -> None:
        self._current_count = 0
        for samples in self._samples.values():
            samples.clear()

    def done(self) -> bool:
        return self._current_count >= self._target_count


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

        self._timer = _Timer(100)

    def _initialize(self) -> None:
        logging.basicConfig(level=logging.DEBUG)

        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Gravity")
        self._renderer.initialize()

        # temp, for quickly setting up a test state
        w = 300
        h = 300
        for i in range(75):
            self._game.simulation.create(
                pos=pygame.Vector2(
                    random.uniform(-w // 2, w // 2),
                    random.uniform(-h // 2, h // 2),
                ),
                mass=abs(random.gauss(mu=0, sigma=1)),
            )

    def _deinitialize(self) -> None:
        pygame.quit()
        logging.shutdown()

    def run(self) -> int:
        self._initialize()

        clock = pygame.time.Clock()
        while self._game.is_running():
            dt = clock.tick(self._target_framerate) / 1000.0
            self._timer.sample("dt", dt)

            with self._timer.time("events"):
                self._events.handle_events()
            with self._timer.time("update"):
                self._game.update(dt)
            with self._timer.time("render"):
                self._renderer.render(self._game)

            self._timer.count()
            self._show_frame_stats()

        self._deinitialize()
        return 0

    def _show_frame_stats(self) -> None:
        if not self._timer.done():
            return

        dt = self._timer.average("dt")
        fps = 1 / dt
        logger.debug(f"fps: {fps:.3}")

        for name in ("events", "update", "render"):
            value = self._timer.average(name)
            percent = value / dt * 100
            logger.debug(f"{name}: {percent:.3}%")

        self._timer.reset()


def build_application(config: AppConfig) -> Application:
    layout = Layout.from_config(config.layout)

    simulation_core = SimulationCore.from_config(config.simulation.physics)
    simulation_entity_descriptor = SimulationEntityDescriptor.from_config(
        config.simulation.model
    )
    simulation = SimulationController.from_config(
        config.simulation.control,
        simulation_core,
        simulation_entity_descriptor,
    )

    inspector = InspectorUIState.from_config(config.ui_format)
    camera = Camera.from_config(config.camera, layout)

    camera_controller = CameraController()
    pause_controller = PauseController.from_config(config.pause_animation)
    cursor_ui_controller = CursorUIController.from_config(config.cursor_ui, layout)

    renderer = Renderer.from_config(config.render, layout)

    game = GameState(
        simulation,
        inspector,
        camera,
        camera_controller,
        pause_controller,
        cursor_ui_controller,
    )
    events = EventHandler(game, layout)

    return Application(
        layout, game, events, renderer, target_framerate=config.core.target_framerate
    )


def run_benchmark(config: AppConfig) -> int:
    warmup_samples = 5
    steps_per_trial = 100
    trials = 5
    seed_base = 12345
    entity_counts = range(1, 101, 1)

    width = 500
    height = 500
    mu = 0.0
    sigma = 1.0

    dt = config.simulation.control.physics_timedelta

    results = defaultdict(list)

    total_runs = len(entity_counts) * trials
    completed = 0

    for n_entities in entity_counts:
        for trial in range(trials):
            completed += 1
            sys.stderr.write(f"\rBenchmark progress: {completed}/{total_runs}")

            random.seed(seed_base + trial)

            # initialize simulation
            simulation_core = SimulationCore.from_config(config.simulation.physics)

            for _ in range(n_entities):
                pos = pygame.Vector2(
                    random.uniform(-width / 2, width / 2),
                    random.uniform(-height / 2, height / 2),
                )
                vel = pygame.Vector2(0, 0)
                mass = random.gauss(mu, sigma)
                simulation_core.create(pos, vel, mass)

            # warm-up
            for _ in range(warmup_samples):
                simulation_core.update(dt)

            # timed section
            t0 = time.perf_counter()
            for _ in range(steps_per_trial):
                simulation_core.update(dt)
            t1 = time.perf_counter()

            step_time = (t1 - t0) / steps_per_trial
            results[n_entities].append(step_time)
    sys.stderr.write("\n")

    print("entities,min,max,avg")
    for n, times in results.items():
        print(f"{n},{min(times)},{max(times)},{sum(times)/len(times)}")

    return 0
