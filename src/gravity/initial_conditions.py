from abc import ABC, abstractmethod
from dataclasses import dataclass
from random import Random
from typing import Iterable, Optional, Self

import pygame

from gravity.config.schema import initial_conditions as config


@dataclass
class InitialConditionsEntity:
    pos: pygame.Vector2
    vel: pygame.Vector2
    mass: float


def cfg_resolve(cfg: config.Property, rand: Random) -> float:
    if isinstance(cfg, config.LiteralProperty):
        return cfg.value
    raise ValueError("invalid type for config literal")


class Entity(ABC):
    @abstractmethod
    def total_mass(self) -> float:
        pass

    @abstractmethod
    def absolute_entities(
        self, pos_offset: pygame.Vector2, vel_offset: pygame.Vector2
    ) -> Iterable[InitialConditionsEntity]:
        pass


class SimpleEntity(Entity):
    def __init__(self, mass: float) -> None:
        self._mass = mass

    @classmethod
    def from_config(cls, cfg: config.SimpleEntity, rand: Random) -> Self:
        return cls(cfg_resolve(cfg.mass, rand))

    def total_mass(self) -> float:
        return self._mass

    def absolute_entities(
        self, pos_offset: pygame.Vector2, vel_offset: pygame.Vector2
    ) -> Iterable[InitialConditionsEntity]:
        yield InitialConditionsEntity(
            pos_offset,  # simple entity is always at its own barycenter
            vel_offset,
            self.total_mass(),
        )


class SystemEntity(Entity):
    def __init__(self) -> None:
        self._entities: list[tuple[Entity, pygame.Vector2, pygame.Vector2]] = []
        self._total_mass: Optional[float] = None

    def add_entity(
        self, entity: Entity, pos: pygame.Vector2, vel: pygame.Vector2
    ) -> None:
        self._entities.append((entity, pos, vel))
        self._total_mass = None

    @classmethod
    def from_config(cls, cfg: config.SystemEntity, rand: Random) -> Self:
        system = cls()
        for entity_instance in cfg.system.entities:
            entity = entity_from_config(entity_instance, rand)
            pos = pygame.Vector2(
                *(cfg_resolve(p, rand) for p in entity_instance.position)
            )
            vel = pygame.Vector2(
                *(cfg_resolve(v, rand) for v in entity_instance.velocity)
            )
            system.add_entity(entity, pos, vel)
        return system

    def _compute_total_mass(self) -> float:
        total = 0.0
        for entity, _, _ in self._entities:
            total += entity.total_mass()
        return total

    def total_mass(self) -> float:
        if self._total_mass is None:
            self._total_mass = self._compute_total_mass()
        return self._total_mass

    def _barycenter(self) -> pygame.Vector2:
        total_mass = self.total_mass()
        center = pygame.Vector2(0, 0)

        for entity, pos, _ in self._entities:
            mass = entity.total_mass()
            center += pos * mass

        if total_mass <= 0:
            raise ValueError("invalid system with nonpositive mass")

        center /= total_mass
        return center

    def absolute_entities(
        self, pos_offset: pygame.Vector2, vel_offset: pygame.Vector2
    ) -> Iterable[InitialConditionsEntity]:
        if not self._entities:
            return

        barycenter = self._barycenter()

        for entity, pos, vel in self._entities:
            total_pos = pos_offset + (pos - barycenter)
            total_vel = vel_offset + vel
            yield from entity.absolute_entities(total_pos, total_vel)


def entity_from_config(cfg: config.EntityInstance, rand: Random) -> Entity:
    if isinstance(cfg.entity, config.SimpleEntity):
        return SimpleEntity.from_config(cfg.entity, rand)
    elif isinstance(cfg.entity, config.SystemEntity):
        return SystemEntity.from_config(cfg.entity, rand)
    raise ValueError("invalid type for config entity")


class InitialConditions:
    def __init__(self, root: SystemEntity):
        self._root = root

    @classmethod
    def from_config(cls, cfg: Optional[config.InitialConditions]) -> Self:
        if cfg is None:
            return cls(SystemEntity())
        rand = Random(cfg.seed)
        return cls(SystemEntity.from_config(cfg.root, rand))

    def compute_all_entities(self) -> Iterable[InitialConditionsEntity]:
        return self._root.absolute_entities(pygame.Vector2(0, 0), pygame.Vector2(0, 0))
