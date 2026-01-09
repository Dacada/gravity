import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from random import Random
from typing import Iterable, Optional, Self, assert_never

import pygame

from gravity.config.schema import initial_conditions as config


@dataclass
class InitialConditionsEntity:
    pos: pygame.Vector2
    vel: pygame.Vector2
    mass: float
    name: Optional[str]


class ResolvableValue(ABC):
    def __init__(self) -> None:
        self._resolved: Optional[float] = None

    @abstractmethod
    def _resolve(self, rand: Random) -> float:
        pass

    def resolve(self, rand: Random) -> float:
        if self._resolved is None:
            self._resolved = self._resolve(rand)
        return self._resolved


class ResolvableLiteral(ResolvableValue):
    def __init__(self, value: float) -> None:
        super().__init__()
        self._value = value

    def _resolve(self, rand: Random) -> float:
        return self._value


class ResolvableGaussian(ResolvableValue):
    def __init__(self, mean: float, sigma: float, absolute: bool) -> None:
        super().__init__()
        self._mean = mean
        self._sigma = sigma
        self._absolute = absolute

    def _resolve(self, rand: Random) -> float:
        res = rand.gauss(self._mean, self._sigma)
        if self._absolute:
            return abs(res)
        return res


class ResolvableUniform(ResolvableValue):
    def __init__(self, start: float, end: float) -> None:
        super().__init__()
        self._start = start
        self._end = end

    def _resolve(self, rand: Random) -> float:
        return rand.uniform(self._start, self._end)


def resolvable_from_config(cfg: config.Property) -> ResolvableValue:
    if isinstance(cfg, config.LiteralProperty):
        return ResolvableLiteral(cfg.value)
    elif isinstance(cfg, config.GaussProperty):
        return ResolvableGaussian(cfg.mean, cfg.sigma, False)
    elif isinstance(cfg, config.GaussAbsoluteProperty):
        return ResolvableGaussian(cfg.mean, cfg.sigma, True)
    elif isinstance(cfg, config.UniformProperty):
        return ResolvableUniform(cfg.start, cfg.end)


class Entity(ABC):
    @abstractmethod
    def total_mass(self, rand: Random) -> float:
        pass

    @abstractmethod
    def absolute_entities(
        self,
        G: float,
        pos_offset: pygame.Vector2,
        vel_offset: pygame.Vector2,
        rand: Random,
    ) -> Iterable[InitialConditionsEntity]:
        pass


class SimpleEntity(Entity):
    def __init__(self, mass: ResolvableValue, name: Optional[str]) -> None:
        self._mass = mass
        self._name = name

    @classmethod
    def from_config(cls, cfg: config.SimpleEntity) -> Self:
        return cls(resolvable_from_config(cfg.mass), cfg.name)

    def total_mass(self, rand: Random) -> float:
        return self._mass.resolve(rand)

    def absolute_entities(
        self,
        G: float,
        pos_offset: pygame.Vector2,
        vel_offset: pygame.Vector2,
        rand: Random,
    ) -> Iterable[InitialConditionsEntity]:
        yield InitialConditionsEntity(
            pos_offset,  # simple entity is always at its own barycenter
            vel_offset,
            self.total_mass(rand),
            self._name,
        )


class SystemEntity(Entity):
    def __init__(self) -> None:
        self._entities: list[
            tuple[
                Entity,
                tuple[ResolvableValue, ResolvableValue],
                tuple[ResolvableValue, ResolvableValue],
            ]
        ] = []
        self._total_mass: Optional[float] = None

    def add_entity(
        self,
        entity: Entity,
        pos: tuple[ResolvableValue, ResolvableValue],
        vel: tuple[ResolvableValue, ResolvableValue],
    ) -> None:
        self._entities.append((entity, pos, vel))
        self._total_mass = None

    @classmethod
    def from_config(cls, cfg: config.System, rand: Random) -> Self:
        system = cls()
        for entity_instance in cfg.entities:
            entity = entity_from_config(entity_instance.entity, rand)
            pos = (
                resolvable_from_config(entity_instance.position[0]),
                resolvable_from_config(entity_instance.position[1]),
            )
            vel = (
                resolvable_from_config(entity_instance.velocity[0]),
                resolvable_from_config(entity_instance.velocity[1]),
            )
            system.add_entity(entity, pos, vel)
        return system

    def _compute_total_mass(self, rand: Random) -> float:
        total = 0.0
        for entity, _, _ in self._entities:
            total += entity.total_mass(rand)
        return total

    def total_mass(self, rand: Random) -> float:
        if self._total_mass is None:
            self._total_mass = self._compute_total_mass(rand)
        return self._total_mass

    def _barycenter(self, rand: Random) -> pygame.Vector2:
        total_mass = self.total_mass(rand)
        center = pygame.Vector2(0, 0)

        for entity, pos, _ in self._entities:
            mass = entity.total_mass(rand)
            pos_vec = pygame.Vector2(pos[0].resolve(rand), pos[1].resolve(rand))
            center += pos_vec * mass

        if total_mass <= 0:
            raise ValueError("invalid system with nonpositive mass")

        center /= total_mass
        return center

    def absolute_entities(
        self,
        G: float,
        pos_offset: pygame.Vector2,
        vel_offset: pygame.Vector2,
        rand: Random,
    ) -> Iterable[InitialConditionsEntity]:
        if not self._entities:
            return

        barycenter = self._barycenter(rand)

        for entity, pos, vel in self._entities:
            pos_vec = pygame.Vector2(pos[0].resolve(rand), pos[1].resolve(rand))
            vel_vec = pygame.Vector2(vel[0].resolve(rand), vel[1].resolve(rand))
            total_pos = pos_offset + (pos_vec - barycenter)
            total_vel = vel_offset + vel_vec
            yield from entity.absolute_entities(G, total_pos, total_vel, rand)


class BinarySystemEntity(Entity):
    def __init__(
        self,
        primary: Entity,
        secondary: Entity,
        semi_major_axis: ResolvableValue,
        eccentricity: ResolvableValue,
        phase: ResolvableValue,
        orientation: ResolvableValue,
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        self._semi_major_axis = semi_major_axis
        self._eccentricity = eccentricity
        self._phase = phase
        self._orientation = orientation

    @classmethod
    def from_config(cls, cfg: config.BinarySystemEntity, rand: Random) -> Self:
        return cls(
            entity_from_config(cfg.primary, rand),
            entity_from_config(cfg.secondary, rand),
            resolvable_from_config(cfg.semi_major_axis),
            resolvable_from_config(cfg.eccentricity),
            resolvable_from_config(cfg.phase),
            resolvable_from_config(cfg.orientation),
        )

    def total_mass(self, rand: Random) -> float:
        return self._primary.total_mass(rand) + self._secondary.total_mass(rand)

    def absolute_entities(
        self,
        G: float,
        pos_offset: pygame.Vector2,
        vel_offset: pygame.Vector2,
        rand: Random,
    ) -> Iterable[InitialConditionsEntity]:
        m1 = self._primary.total_mass(rand)
        m2 = self._secondary.total_mass(rand)
        M = self.total_mass(rand)
        mu = G * M
        a = self._semi_major_axis.resolve(rand)
        e = self._eccentricity.resolve(rand)
        f = self._phase.resolve(rand)
        theta_deg = math.degrees(self._orientation.resolve(rand))
        r = a * (1 - e * e) / (1 + e * math.cos(f))
        r_pf = pygame.Vector2(r * math.cos(f), r * math.sin(f))
        h = math.sqrt(mu * a * (1 - e * e))
        v_pf = (mu / h) * pygame.Vector2(-math.sin(f), e + math.cos(f))
        r_rel = r_pf.rotate(theta_deg)
        v_rel = v_pf.rotate(theta_deg)
        r1 = -(m2 / M) * r_rel
        r2 = +(m1 / M) * r_rel
        v1 = -(m2 / M) * v_rel
        v2 = +(m1 / M) * v_rel

        total_pos_1 = pos_offset + r1
        total_pos_2 = pos_offset + r2
        total_vel_1 = vel_offset + v1
        total_vel_2 = vel_offset + v2
        yield from self._primary.absolute_entities(G, total_pos_1, total_vel_1, rand)
        yield from self._secondary.absolute_entities(G, total_pos_2, total_vel_2, rand)


def create_box_lattice(
    region: config.BoxRegion, count: int, rand: Random
) -> Iterable[pygame.Vector2]:
    nx = math.ceil(math.sqrt(count * region.width / region.height))
    ny = math.ceil(count / nx)

    hx = region.width / nx
    hy = region.height / ny

    curr = 0
    for j in range(int(ny)):
        for i in range(int(nx)):
            if curr == count:
                return

            x = (i + 0.5) * hx
            y = (j + 0.5) * hy

            dx = region.disorder * (rand.random() - 0.5) * hx
            dy = region.disorder * (rand.random() - 0.5) * hy

            yield pygame.Vector2(x + dx, y + dy)
            curr += 1


def create_lattice(
    region: config.Region, count: int, rand: Random
) -> Iterable[pygame.Vector2]:
    if isinstance(region, config.BoxRegion):
        return create_box_lattice(region, count, rand)


def create_cloud_system(cfg: config.CloudEntity, rand: Random) -> SystemEntity:
    positions = create_lattice(cfg.region, cfg.count, rand)
    system = SystemEntity()
    for position in positions:
        entity = SimpleEntity(resolvable_from_config(cfg.mass), None)
        velocity = (
            resolvable_from_config(cfg.velocity[0]),
            resolvable_from_config(cfg.velocity[1]),
        )
        position_resolvanle = (
            ResolvableLiteral(position[0]),
            ResolvableLiteral(position[1]),
        )
        system.add_entity(entity, position_resolvanle, velocity)
    return system


def entity_from_config(cfg: config.Entity, rand: Random) -> Entity:
    if isinstance(cfg, config.SimpleEntity):
        return SimpleEntity.from_config(cfg)
    elif isinstance(cfg, config.SystemEntity):
        return SystemEntity.from_config(cfg.system, rand)
    elif isinstance(cfg, config.CloudEntity):
        return create_cloud_system(cfg, rand)
    elif isinstance(cfg, config.BinarySystemEntity):
        return BinarySystemEntity.from_config(cfg, rand)


class InitialConditions:
    def __init__(self, root: SystemEntity, funny: bool, G: float, rand: Random):
        self._root = root
        self._rand = rand
        self._G = G

        self.funny = funny

    @classmethod
    def from_config(cls, cfg: Optional[config.InitialConditions], G: float) -> Self:
        if cfg is None:
            return cls(SystemEntity(), False, G, Random())
        rand = Random(cfg.seed)
        return cls(SystemEntity.from_config(cfg.root, rand), cfg.funny, G, rand)

    def compute_all_entities(self) -> Iterable[InitialConditionsEntity]:
        return self._root.absolute_entities(
            self._G, pygame.Vector2(0, 0), pygame.Vector2(0, 0), self._rand
        )

    def system_mass(self) -> float:
        return self._root.total_mass(self._rand)
