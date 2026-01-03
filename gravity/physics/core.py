import math
from dataclasses import dataclass
from typing import Iterator, Optional, Self

import pygame

from gravity.config.schema import AppConfigSimulationPhysics


@dataclass(frozen=True)
class SimulatedEntityHandle:
    slot_idx: int
    generation: int


@dataclass
class MergeInfo:
    merged: tuple[SimulatedEntityHandle, SimulatedEntityHandle]
    into: SimulatedEntityHandle


@dataclass
class _Slot:
    array_idx: int
    generation: int


class SimulationCore:
    def __init__(
        self,
        gravitational_constant: float,
        softening_factor: float,
        enable_merging: bool,
        merge_distance_squared: float,
    ) -> None:
        self._gravitational_constant = gravitational_constant
        self._softening_factor = softening_factor
        self._enable_merging = enable_merging
        self._merge_distance_squared = merge_distance_squared

        self._positions: list[pygame.Vector2] = []
        self._velocities: list[pygame.Vector2] = []
        self._masses: list[float] = []
        self._array_to_slot: list[int] = []

        self._slots: list[_Slot] = []
        self._free_slots: list[int] = []

    @classmethod
    def from_config(cls, cfg: AppConfigSimulationPhysics) -> Self:
        return cls(
            cfg.gravitational_constant,
            cfg.softening_factor,
            cfg.enable_merging,
            cfg.merge_distance_squared,
        )

    def create(
        self, pos: pygame.Vector2, vel: pygame.Vector2, mass: float
    ) -> SimulatedEntityHandle:
        if len(self._free_slots) == 0:
            slot_idx = len(self._slots)
            self._slots.append(_Slot(0, 0))
        else:
            slot_idx = self._free_slots.pop()

        array_idx = len(self._positions)

        self._positions.append(pos)
        self._velocities.append(vel)
        self._masses.append(mass)
        self._array_to_slot.append(slot_idx)

        self._slots[slot_idx].array_idx = array_idx
        return SimulatedEntityHandle(slot_idx, self._slots[slot_idx].generation)

    def is_handle_valid(self, handle: SimulatedEntityHandle) -> bool:
        return (
            handle.slot_idx < len(self._slots)
            and self._slots[handle.slot_idx].generation == handle.generation
        )

    def get(
        self, handle: SimulatedEntityHandle
    ) -> Optional[tuple[pygame.Vector2, pygame.Vector2, float]]:
        if not self.is_handle_valid(handle):
            return None

        array_idx = self._slots[handle.slot_idx].array_idx
        return (
            self._positions[array_idx].copy(),
            self._velocities[array_idx].copy(),
            self._masses[array_idx],
        )

    def set_position(self, handle: SimulatedEntityHandle, pos: pygame.Vector2) -> None:
        if not self.is_handle_valid(handle):
            return

        array_idx = self._slots[handle.slot_idx].array_idx
        self._positions[array_idx] = pos.copy()

    def set_velocity(self, handle: SimulatedEntityHandle, vel: pygame.Vector2) -> None:
        if not self.is_handle_valid(handle):
            return

        array_idx = self._slots[handle.slot_idx].array_idx
        self._velocities[array_idx] = vel.copy()

    def set_mass(self, handle: SimulatedEntityHandle, mass: float) -> None:
        if not self.is_handle_valid(handle):
            return

        array_idx = self._slots[handle.slot_idx].array_idx
        self._masses[array_idx] = mass

    def delete(self, handle: SimulatedEntityHandle) -> None:
        if not self.is_handle_valid(handle):
            return

        array_idx = self._slots[handle.slot_idx].array_idx
        self._delete_idx(array_idx)

    def _delete_idx(self, array_idx: int) -> None:
        slot_idx = self._array_to_slot[array_idx]
        last = len(self._positions) - 1

        if array_idx != last:
            self._positions[array_idx] = self._positions[last]
            self._velocities[array_idx] = self._velocities[last]
            self._masses[array_idx] = self._masses[last]

            moved_slot = self._array_to_slot[last]
            self._array_to_slot[array_idx] = moved_slot
            self._slots[moved_slot].array_idx = array_idx

        self._positions.pop()
        self._velocities.pop()
        self._masses.pop()
        self._array_to_slot.pop()

        self._slots[slot_idx].generation += 1
        self._free_slots.append(slot_idx)

    def _get_handle(self, array_idx: int) -> SimulatedEntityHandle:
        slot_idx = self._array_to_slot[array_idx]
        return SimulatedEntityHandle(slot_idx, self._slots[slot_idx].generation)

    def entities_in_rect_iter(
        self, topleft: pygame.Vector2, bottomright: pygame.Vector2
    ) -> Iterator[SimulatedEntityHandle]:
        for i, p in enumerate(self._positions):
            if topleft.x <= p.x <= bottomright.x and topleft.y <= p.y <= bottomright.y:
                yield self._get_handle(i)

    def center_of_mass(self) -> pygame.Vector2:
        total_mass = 0.0
        com = pygame.Vector2(0.0, 0.0)

        for i in range(len(self._positions)):
            pos = self._positions[i]
            mass = self._masses[i]
            com += pos * mass
            total_mass += mass

        if total_mass > 0:
            com /= total_mass

        return com

    def update(self, dt: float) -> list[MergeInfo]:
        merge_result = self._merge_all_masses()

        acc_old = self._compute_accelerations()

        for i in range(len(self._positions)):
            self._positions[i] += self._velocities[i] * dt + 0.5 * acc_old[i] * dt * dt

        acc_new = self._compute_accelerations()

        for i in range(len(self._positions)):
            self._velocities[i] += 0.5 * (acc_old[i] + acc_new[i]) * dt

        return merge_result

    def _compute_accelerations(self) -> list[pygame.Vector2]:
        n = len(self._masses)
        acc = [pygame.Vector2(0.0, 0.0) for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                r = self._positions[j] - self._positions[i]
                dist_sq = r.length_squared() + self._softening_factor
                inv_dist = 1.0 / math.sqrt(dist_sq)

                factor = self._gravitational_constant * inv_dist / dist_sq

                a_i = r * (factor * self._masses[j])
                a_j = r * (-factor * self._masses[i])

                acc[i] += a_i
                acc[j] += a_j

        return acc

    def _merge_all_masses(self) -> list[MergeInfo]:
        merges: list[MergeInfo] = []
        if not self._enable_merging:
            return merges

        while True:
            merge = self._merge_masses()
            if merge is None:
                break
            merges.append(merge)
        return merges

    def _merge_masses(self) -> Optional[MergeInfo]:
        n = len(self._positions)

        for i in range(n):
            for j in range(i + 1, n):
                r = self._positions[j] - self._positions[i]
                if r.length_squared() <= self._merge_distance_squared:
                    return self._do_merge_masses(i, j)
        return None

    def _do_merge_masses(self, i: int, j: int) -> MergeInfo:
        pi = self._positions[i]
        pj = self._positions[j]
        vi = self._velocities[i]
        vj = self._velocities[j]
        mi = self._masses[i]
        mj = self._masses[j]

        p = (mi * pi + mj * pj) / (mi + mj)
        v = (mi * vi + mj * vj) / (mi + mj)
        m = mi + mj

        old_handle_1 = self._get_handle(i)
        old_handle_2 = self._get_handle(j)

        if i < j:
            i, j = j, i
        self._delete_idx(i)
        self._delete_idx(j)

        new_handle = self.create(p, v, m)

        return MergeInfo(
            (old_handle_1, old_handle_2),
            new_handle,
        )
