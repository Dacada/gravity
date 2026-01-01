import math
from typing import Iterable, Iterator, Optional, Self

import pygame

from gravity.config.schema import AppConfigPhysicsSimulation
from gravity.physics.point_mass import PointMass


class PointMassSimulator(Iterable[PointMass]):
    def __init__(
        self,
        gravitational_constant: float,
        softening_factor: float,
        merge_distance_squared: float,
    ) -> None:
        self._gravitational_constant = gravitational_constant
        self._softening_factor = softening_factor
        self._merge_distance_squared = merge_distance_squared

        self._masses: list[PointMass] = []

    @classmethod
    def from_config(cls, cfg: AppConfigPhysicsSimulation) -> Self:
        return cls(
            cfg.gravitational_constant,
            cfg.softening_factor,
            cfg.merge_distance_squared,
        )

    def create(self, pos: pygame.Vector2, mass: float = 1.0) -> PointMass:
        p = PointMass(
            name="",
            color=None,
            pos=pos,
            vel=pygame.Vector2(0.0, 0.0),
            mass=mass,
        )
        self._masses.append(p)
        return p

    def delete(self, p: PointMass) -> None:
        for i, pp in enumerate(self._masses):
            if pp is p:
                del self._masses[i]
                return

    def index(self, p: PointMass) -> Optional[int]:
        for i, q in enumerate(self._masses):
            if q is p:
                return i
        return None

    def by_index(self, idx: int) -> Optional[PointMass]:
        try:
            return self._masses[idx % self.get_total()]
        except IndexError:
            return None

    def get_total(self) -> int:
        return len(self._masses)

    def center_of_mass(self) -> pygame.Vector2:
        total_mass = 0.0
        com = pygame.Vector2(0.0, 0.0)

        for p in self._masses:
            com += p.pos * p.mass
            total_mass += p.mass

        if total_mass > 0:
            com /= total_mass

        return com

    def update(self, dt: float) -> None:
        self._merge_all_masses()

        acc_old = self._compute_accelerations()

        for i, p in enumerate(self._masses):
            p.pos += p.vel * dt + 0.5 * acc_old[i] * dt * dt

        acc_new = self._compute_accelerations()

        for i, p in enumerate(self._masses):
            p.vel += 0.5 * (acc_old[i] + acc_new[i]) * dt

    def _compute_accelerations(self) -> list[pygame.Vector2]:
        n = len(self._masses)
        acc = [pygame.Vector2(0.0, 0.0) for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                r = self._masses[j].pos - self._masses[i].pos
                dist_sq = r.length_squared() + self._softening_factor
                inv_dist = 1.0 / math.sqrt(dist_sq)

                factor = self._gravitational_constant * inv_dist / dist_sq

                a_i = r * (factor * self._masses[j].mass)
                a_j = r * (-factor * self._masses[i].mass)

                acc[i] += a_i
                acc[j] += a_j

        return acc

    def _merge_all_masses(self) -> None:
        while self._merge_masses():
            pass

    def _merge_masses(self) -> bool:
        n = len(self._masses)

        for i in range(n):
            for j in range(i + 1, n):
                r = self._masses[j].pos - self._masses[i].pos
                if r.length_squared() <= self._merge_distance_squared:
                    self._do_merge_masses(i, j)
                    return True
        return False

    def _do_merge_masses(self, i: int, j: int) -> None:
        pi = self._masses[i]
        pj = self._masses[j]

        if pi.name and pj.name:
            name = pi.name + " / " + pj.name
        elif pi.name:
            name = pi.name
        elif pj.name:
            name = pj.name
        else:
            name = ""

        if pi.color is not None and pj.color is not None:
            color = (
                (pi.color[0] + pj.color[0]) // 2,
                (pi.color[1] + pj.color[1]) // 2,
                (pi.color[2] + pj.color[2]) // 2,
            )
        elif pi.color is not None:
            color = pi.color
        elif pj.color is not None:
            color = pj.color
        else:
            color = None

        p_new = PointMass(
            name=name,
            color=color,
            pos=(pi.mass * pi.pos + pj.mass * pj.pos) / (pi.mass + pj.mass),
            vel=(pi.mass * pi.vel + pj.mass * pj.vel) / (pi.mass + pj.mass),
            mass=pi.mass + pj.mass,
        )

        self._masses[i] = p_new
        del self._masses[j]

    def __iter__(self) -> Iterator[PointMass]:
        return iter(self._masses)
