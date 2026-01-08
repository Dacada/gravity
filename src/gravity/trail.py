import collections
from typing import Iterable, Optional, Self, Sequence

import pygame

from gravity.config.schema.render import Trail
from gravity.physics import SimulatedEntityHandle, SimulationController


class TrailController:
    def __init__(
        self,
        simulation_controller: SimulationController,
        sampling_period: float,
        sample_buffer_size: int,
    ) -> None:
        self._simulation = simulation_controller
        self._sampling_period = sampling_period
        self._sample_buffer_size = sample_buffer_size

        self._samples: dict[
            SimulatedEntityHandle, collections.deque[pygame.Vector2]
        ] = {}
        self._accumulator = 0.0

    @classmethod
    def from_config(
        cls, trail: Trail, simulation_controller: SimulationController
    ) -> Self:
        return cls(
            simulation_controller,
            trail.sampling_period,
            trail.sample_buffer_size,
        )

    def toggle_track(self, handle: Optional[SimulatedEntityHandle]) -> None:
        if handle is None:
            return

        if handle in self._samples:
            self._samples.pop(handle, None)
        else:
            self._samples[handle] = collections.deque(maxlen=self._sample_buffer_size)

    def update(self, dt: float) -> None:
        self._accumulator += dt
        should_sample = False
        while self._accumulator >= self._sampling_period:
            self._accumulator -= self._sampling_period
            should_sample = True
        if should_sample:
            self._collect_samples()

    def entities(self) -> Iterable[SimulatedEntityHandle]:
        return self._samples.keys()

    def samples(self, handle: SimulatedEntityHandle) -> Sequence[pygame.Vector2]:
        return self._samples[handle]

    def _collect_samples(self) -> None:
        invalid: list[SimulatedEntityHandle] = []

        for handle, samples in self._samples.items():
            entity = self._simulation.get(handle)
            if entity is None:
                invalid.append(handle)
                continue
            samples.append(entity.pos)

        for handle in invalid:
            self._samples.pop(handle)
