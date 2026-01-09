import colorsys
import logging
import math
import random
import sys
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional

import pygame

from gravity.camera import Camera, CameraController
from gravity.config import AppConfig
from gravity.core import EventHandler, GameState
from gravity.initial_conditions import InitialConditions
from gravity.layout import Layout
from gravity.physics import (
    SimulatedEntity,
    SimulatedEntityHandle,
    SimulationController,
    SimulationCore,
    SimulationEntityDescriptor,
)
from gravity.render import Renderer
from gravity.trail import TrailController
from gravity.types import Color
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


def apply_initial_conditions(
    simulation: SimulationController,
    trail_controller: Optional[TrailController],
    initial_conditions: InitialConditions,
) -> None:
    def random_color() -> Color:
        h = random.random()
        s = random.uniform(0.6, 1.0)
        v = random.uniform(0.7, 1.0)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return Color(int(r * 255), int(g * 255), int(v * 255))

    for entity in initial_conditions.compute_all_entities():
        handle = simulation.create(
            pos=entity.pos,
            vel=entity.vel,
            mass=entity.mass,
            name=entity.name,
        )
        if initial_conditions.funny:
            if trail_controller is not None:
                trail_controller.toggle_track(handle)
            entity_sim = simulation.get(handle)
            if entity_sim is None:
                continue
            entity_sim.color = random_color()
            simulation.apply(entity_sim)


class Application:
    def __init__(
        self,
        layout: Layout,
        game: GameState,
        events: EventHandler,
        renderer: Renderer,
        initial_conditions: InitialConditions,
        target_framerate: int,
    ):
        self._target_framerate = target_framerate
        self._layout = layout
        self._game = game
        self._events = events
        self._renderer = renderer
        self._initial_conditions = initial_conditions

        self._timer = _Timer(100)

    def _initialize(self) -> None:
        logging.basicConfig(level=logging.DEBUG)

        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Gravity")
        self._renderer.initialize()

        apply_initial_conditions(
            self._game.simulation, self._game.trail_controller, self._initial_conditions
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

    inspector = InspectorUIState.from_config(config.ui.format)
    camera = Camera.from_config(config.camera, layout)

    camera_controller = CameraController()
    pause_controller = PauseController.from_config(config.ui.pause_animation)
    cursor_ui_controller = CursorUIController.from_config(config.ui.cursor, layout)
    trail_controller = TrailController.from_config(
        config.render.effects.trail, simulation
    )

    renderer = Renderer.from_config(config.render, layout)

    initial_conditions = InitialConditions.from_config(
        config.simulation.initial_conditions,
        config.simulation.physics.gravitational_constant,
    )

    simulation.on_merge(inspector.on_merge)
    simulation.on_merge(trail_controller.on_merge)

    game = GameState(
        simulation,
        inspector,
        camera,
        camera_controller,
        pause_controller,
        cursor_ui_controller,
        trail_controller,
    )
    events = EventHandler(game, layout)

    return Application(
        layout,
        game,
        events,
        renderer,
        initial_conditions,
        target_framerate=config.core.target_framerate,
    )


def run_benchmark(config: AppConfig) -> int:
    warmup_samples = 5
    steps_per_trial = 100
    trials = 5
    seed_base = 12345
    entity_counts = range(1, 3251, 1)

    width = 500
    height = 500
    mu = 0.0
    sigma = 1.0

    dt = 1 / 500

    results = defaultdict(list)

    total_runs = len(entity_counts) * trials
    completed = 0

    config.simulation.physics.enable_merging = False

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
                mass = abs(random.gauss(mu, sigma))
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


def _gather_bodies(
    first: SimulatedEntityHandle, controller: SimulationController, core: SimulationCore
) -> dict[int, SimulatedEntity]:
    bodies = []
    handle: SimulatedEntityHandle = first
    while True:
        body_tuple = core.get(handle)
        if body_tuple is None:
            raise RuntimeError(f"{handle=} is invalid!!")
        pos, vel, mass = body_tuple
        body = controller.get(handle)
        if body is None:
            raise RuntimeError(f"{handle=} is invalid!!")
        body.pos = pos
        body.vel = vel
        body.mass = mass
        bodies.append(body)
        next_handle = controller.get_next_point(handle)
        if next_handle is None:
            raise RuntimeError(f"next of {handle=} is none!!")
        handle = next_handle
        if handle == first:
            break
    for body in bodies:
        if body.name is None:
            raise ValueError("body does not have a name")
    return {int(b.name, 16): b for b in bodies if b.name is not None}


@dataclass
class SimulationSelftestParameters:
    total_linear_momentum: pygame.Vector2
    center_of_mass: pygame.Vector2
    total_angular_momentum: float
    system_energy: float


def _compute_invariants(
    G: float, bodies: dict[int, SimulatedEntity]
) -> SimulationSelftestParameters:
    system_mass = 0.0
    total_linear_momentum = pygame.Vector2(0, 0)
    center_of_mass = pygame.Vector2(0, 0)
    total_angular_momentum = 0.0
    kinetic_energy = 0.0

    for body in bodies.values():
        system_mass += body.mass
        total_linear_momentum += body.mass * body.vel
        center_of_mass += body.mass * body.pos
        total_angular_momentum += body.mass * (body.pos.cross(body.vel))
        kinetic_energy += 0.5 * body.mass * body.vel.length_squared()

    if system_mass <= 0:
        raise ValueError("invalid nonpositive system mass")

    center_of_mass /= system_mass

    bodies_list = list(bodies.values())
    bodies_count = len(bodies_list)
    potential_energy = 0.0
    for i in range(bodies_count):
        bi = bodies_list[i]
        for j in range(i + 1, bodies_count):
            bj = bodies_list[j]
            r = (bi.pos - bj.pos).length()
            if r == 0:
                raise ValueError("zero separation of a pair of bodies")
            potential_energy -= G * bi.mass * bj.mass / r

    system_energy = kinetic_energy + potential_energy

    return SimulationSelftestParameters(
        total_linear_momentum=total_linear_momentum,
        center_of_mass=center_of_mass,
        total_angular_momentum=total_angular_momentum,
        system_energy=system_energy,
    )


def _evaluate_drift(
    initial: SimulationSelftestParameters,
    final: SimulationSelftestParameters,
) -> bool:
    EPS = 1e-12

    def scalar_relative_drift(a: float, b: float) -> float:
        if abs(a) < EPS:
            return abs(b)
        return abs(b - a) / abs(a)

    angmom_drift = scalar_relative_drift(
        initial.total_angular_momentum,
        final.total_angular_momentum,
    )
    energy_drift = scalar_relative_drift(
        initial.system_energy,
        final.system_energy,
    )

    P = final.total_linear_momentum.length()
    CM = final.center_of_mass.length()

    print("Physics invariant drift:")
    print(f"|P| = {P:.3e}")
    print(f"|CM| = {CM:.3e}")
    print(f"ΔL/L = {angmom_drift:.3e}")
    print(f"ΔE/E = {energy_drift:.3e}")

    if P >= 1e-6:
        print("P >= 1e-6")
        return False

    if CM >= 1e-4:
        print("CM >= 1e-4")
        return False

    if angmom_drift >= 1e-6:
        print("ΔL/L >= 1e-6")
        return False

    if energy_drift >= 1e-3:
        print("ΔE/E >= 1e-3")
        return False

    return True


def run_selftest(config: AppConfig) -> int:
    simulation_core = SimulationCore.from_config(config.simulation.physics)
    simulation_entity_descriptor = SimulationEntityDescriptor.from_config(
        config.simulation.model
    )
    simulation_controller = SimulationController.from_config(
        config.simulation.control,
        simulation_core,
        simulation_entity_descriptor,
    )
    initial_conditions = InitialConditions.from_config(
        config.simulation.initial_conditions,
        config.simulation.physics.gravitational_constant,
    )
    apply_initial_conditions(simulation_controller, None, initial_conditions)

    if config.simulation.physics.enable_merging:
        raise ValueError("cannot selftest if merging")
    initial_conditions_config = config.simulation.initial_conditions
    if initial_conditions_config is None:
        raise ValueError("no initial conditions set")
    entities = initial_conditions_config.root.entities
    if len(entities) != 1:
        raise ValueError("more than one root entity in the system")
    entity = entities[0].entity
    a_prop = getattr(entity, "semi_major_axis", None)
    if a_prop is None:
        raise ValueError("initial condition is not a binary system")
    try:
        a = a_prop.value
    except AttributeError:
        raise ValueError("semi major axis is not a constant")

    G = config.simulation.physics.gravitational_constant
    M = initial_conditions.system_mass()

    orbital_period = 2 * math.pi * math.sqrt(a * a * a / G / M)
    timestep = config.simulation.control.physics_timedelta
    physics_steps = int(math.ceil(orbital_period / timestep))

    first = simulation_controller.get_first_point()
    if first is None:
        raise RuntimeError("no handles")

    initial_bodies = _gather_bodies(first, simulation_controller, simulation_core)
    initial_invariants = _compute_invariants(G, initial_bodies)

    for i in range(physics_steps):
        if i % 100000 == 0:
            print(f"Completed: {(i+1)/physics_steps * 100:.2f}%")
            current_bodies = _gather_bodies(
                first, simulation_controller, simulation_core
            )
            current_invariants = _compute_invariants(G, current_bodies)
            if not _evaluate_drift(initial_invariants, current_invariants):
                break
            print()

        simulation_core.update(timestep)

    print()
    print("Finished.")
    final_bodies = _gather_bodies(first, simulation_controller, simulation_core)
    final_invariants = _compute_invariants(G, final_bodies)
    if not _evaluate_drift(initial_invariants, final_invariants):
        print("SELF TEST DID NOT PASS")
        return 1

    return 0
