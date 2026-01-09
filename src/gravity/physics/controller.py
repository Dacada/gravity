from dataclasses import dataclass
from typing import Iterator, Optional, Self

import pygame
from typing_extensions import Callable

from gravity.config.schema.simulation import Control as ControlConfig
from gravity.config.schema.simulation import Model as ModelConfig
from gravity.physics._core import MergeInfo, SimulatedEntityHandle
from gravity.physics.core import SimulationCore
from gravity.physics.model import SimulatedEntity
from gravity.types import Color

OnMergeCallback = Callable[
    [SimulatedEntityHandle, SimulatedEntityHandle, SimulatedEntityHandle], None
]


@dataclass
class _EntityDescription:
    handle: SimulatedEntityHandle
    name: Optional[str]
    color: Color


class SimulationEntityDescriptor:
    def __init__(self, default_simulated_entity_color: Color):
        self._default_simulated_entity_color = default_simulated_entity_color
        self._descriptions: dict[SimulatedEntityHandle, _EntityDescription] = {}

    @classmethod
    def from_config(cls, cfg: ModelConfig) -> Self:
        return cls(
            cfg.default_simulated_entity_color,
        )

    def create(
        self,
        handle: SimulatedEntityHandle,
        name: Optional[str] = None,
        color: Optional[Color] = None,
    ) -> None:
        if handle in self._descriptions:
            entity = self._descriptions[handle]
            if name is not None:
                entity.name = name
            if color is not None:
                entity.color = color
            return

        if color is None:
            color = self._default_simulated_entity_color

        self._descriptions[handle] = _EntityDescription(handle, name, color)

    def delete(self, handle: SimulatedEntityHandle) -> None:
        if handle not in self._descriptions:
            return
        del self._descriptions[handle]

    def merge(
        self,
        hdl1: SimulatedEntityHandle,
        hdl2: SimulatedEntityHandle,
        new_hdl: SimulatedEntityHandle,
    ) -> None:
        entity1 = self._get(hdl1)
        entity2 = self._get(hdl2)

        name1 = None
        if entity1 is not None:
            if entity1.name is not None:
                name1 = entity1.name

        name2 = None
        if entity2 is not None:
            if entity2.name is not None:
                name2 = entity2.name

        if name1 is not None and name2 is not None:
            new_name = name1 + " / " + name2
        elif name1 is not None:
            new_name = name1
        elif name2 is not None:
            new_name = name2
        else:
            new_name = None

        if entity1 is not None and entity2 is not None:
            new_color = entity1.color.merge(entity2.color)
        elif entity1 is not None:
            new_color = entity1.color
        elif entity2 is not None:
            new_color = entity2.color
        else:
            new_color = self._default_simulated_entity_color

        self.delete(hdl1)
        self.delete(hdl2)
        self.create(new_hdl, new_name, new_color)

    def _get(self, handle: SimulatedEntityHandle) -> Optional[_EntityDescription]:
        return self._descriptions.get(handle)

    def get_name(self, handle: SimulatedEntityHandle) -> Optional[str]:
        descr = self._get(handle)
        if descr is None:
            return None
        return descr.name

    def set_name(self, handle: SimulatedEntityHandle, name: Optional[str]) -> None:
        descr = self._get(handle)
        if descr is None:
            return
        descr.name = name

    def get_color(self, handle: SimulatedEntityHandle) -> Color:
        descr = self._get(handle)
        if descr is None:
            return self._default_simulated_entity_color
        return descr.color

    def set_color(self, handle: SimulatedEntityHandle, color: Color) -> None:
        descr = self._get(handle)
        if descr is None:
            return
        descr.color = color


@dataclass
class _ListNode:
    handle: SimulatedEntityHandle
    next: Self
    prev: Self


class SimulationEntityOrderController:
    def __init__(self) -> None:
        self._first: Optional[_ListNode] = None
        self._last: Optional[_ListNode] = None
        self._nodes: dict[SimulatedEntityHandle, _ListNode] = {}

    def append(self, handle: SimulatedEntityHandle) -> None:
        if handle in self._nodes:
            return

        node = _ListNode(handle, None, None)  # type: ignore
        node.next = node
        node.prev = node
        self._nodes[handle] = node

        if self._last is None or self._first is None:
            self._last = self._first = node
            return

        self._last.next = node
        node.prev = self._last
        node.next = self._first
        self._first.prev = node
        self._last = node

    def remove(self, handle: SimulatedEntityHandle) -> None:
        if handle not in self._nodes:
            return

        node = self._nodes[handle]
        del self._nodes[handle]

        if node is self._last and node is self._first:
            self._last = self._first = None
            return

        if node is self._first:
            self._first = node.next

        if node is self._last:
            self._last = node.prev

        node.prev.next = node.next
        node.next.prev = node.prev

    def last(self) -> Optional[SimulatedEntityHandle]:
        if self._last is None:
            return None
        return self._last.handle

    def first(self) -> Optional[SimulatedEntityHandle]:
        if self._first is None:
            return None
        return self._first.handle

    def next(self, handle: SimulatedEntityHandle) -> Optional[SimulatedEntityHandle]:
        if handle not in self._nodes:
            return None
        return self._nodes[handle].next.handle

    def prev(self, handle: SimulatedEntityHandle) -> Optional[SimulatedEntityHandle]:
        if handle not in self._nodes:
            return None
        return self._nodes[handle].prev.handle

    def merge(
        self,
        old1: SimulatedEntityHandle,
        old2: SimulatedEntityHandle,
        new: SimulatedEntityHandle,
    ) -> None:
        self.remove(old1)
        self.remove(old2)
        self.append(new)


class SimulationEntityCounter:
    def __init__(self) -> None:
        self._monotonic_counter = 0
        self._entities: dict[SimulatedEntityHandle, int] = {}
        self._indices: dict[int, SimulatedEntityHandle] = {}

    def add(self, handle: SimulatedEntityHandle) -> None:
        if handle in self._entities:
            return

        self._entities[handle] = self._monotonic_counter
        self._indices[self._monotonic_counter] = handle
        self._monotonic_counter += 1

    def remove(self, handle: SimulatedEntityHandle) -> None:
        if handle not in self._entities:
            return

        del self._indices[self._entities[handle]]
        del self._entities[handle]

    def get_index(self, handle: SimulatedEntityHandle) -> int:
        if handle not in self._entities:
            self.add(handle)

        return self._entities[handle]

    def get_handle(self, idx: int) -> Optional[SimulatedEntityHandle]:
        if idx not in self._indices:
            return None

        return self._indices[idx]

    def merge(
        self,
        old1: SimulatedEntityHandle,
        old2: SimulatedEntityHandle,
        new: SimulatedEntityHandle,
    ) -> None:
        self.remove(old1)
        self.remove(old2)
        self.add(new)


class SimulationController:
    def __init__(
        self,
        simulation_core: SimulationCore,
        simulation_entity_descriptor: SimulationEntityDescriptor,
        physics_timedelta: float,
        time_scale: float,
        physics_step_alloted_time_clamp: float,
        allow_before_the_beginning_of_time: float,
    ):
        self._simulation_core = simulation_core
        self._simulation_entity_descriptor = simulation_entity_descriptor
        self._physics_step_alloted_time_clamp = physics_step_alloted_time_clamp
        self._time_scale = time_scale
        self._allow_before_the_beginning_of_time = allow_before_the_beginning_of_time
        self._simulation_entity_order_controller = SimulationEntityOrderController()
        self._simulation_entity_counter = SimulationEntityCounter()

        self._physics_loop_accumulator = 0.0
        self._physics_total_time = 0.0
        self._entity_cache: dict[SimulatedEntityHandle, SimulatedEntity] = {}
        self._on_merge_callbacks: list[OnMergeCallback] = []

        self._physics_timedelta = physics_timedelta

        self._chrono_trigger = False

        self.on_merge(self._simulation_entity_descriptor.merge)
        self.on_merge(self._simulation_entity_counter.merge)
        self.on_merge(self._simulation_entity_order_controller.merge)

    @classmethod
    def from_config(
        cls,
        cfg: ControlConfig,
        simulation_core: SimulationCore,
        simulation_entity_descriptor: SimulationEntityDescriptor,
    ) -> Self:
        return cls(
            simulation_core,
            simulation_entity_descriptor,
            cfg.physics_timedelta,
            cfg.time_scale,
            cfg.physics_step_alloted_time_clamp,
            cfg.allow_before_the_beginning_of_time,
        )

    def create(
        self,
        pos: Optional[pygame.Vector2] = None,
        vel: Optional[pygame.Vector2] = None,
        mass: Optional[float] = None,
        name: Optional[str] = None,
        color: Optional[Color] = None,
    ) -> SimulatedEntityHandle:
        if pos is None:
            pos = pygame.Vector2(0.0, 0.0)
        if vel is None:
            vel = pygame.Vector2(0.0, 0.0)
        if mass is None:
            mass = 1.0

        handle = self._simulation_core.create(pos, vel, mass)
        self._simulation_entity_descriptor.create(handle, name, color)
        self._simulation_entity_order_controller.append(handle)
        self._simulation_entity_counter.add(handle)
        return handle

    def delete(self, handle: SimulatedEntityHandle) -> None:
        self._simulation_entity_counter.remove(handle)
        self._simulation_entity_order_controller.remove(handle)
        self._simulation_entity_descriptor.delete(handle)
        self._simulation_core.delete(handle)
        self._entity_cache.pop(handle)

    def get(self, handle: SimulatedEntityHandle) -> Optional[SimulatedEntity]:
        res = self._entity_cache.get(handle)
        if res is not None:
            return res

        entity = self._simulation_core.get(handle)
        if entity is None:
            return None

        pos, vel, mass = entity
        color = self._simulation_entity_descriptor.get_color(handle)
        name = self._simulation_entity_descriptor.get_name(handle)
        index = self._simulation_entity_counter.get_index(handle)

        res = SimulatedEntity(pos, vel, mass, color, name, index)
        self._entity_cache[handle] = res
        return res

    def apply(self, entity: SimulatedEntity) -> None:
        handle = self._simulation_entity_counter.get_handle(entity.index)
        if handle is None:
            return

        if SimulatedEntity.x.was_modified(entity) or SimulatedEntity.y.was_modified(
            entity
        ):
            self._simulation_core.set_position(handle, entity.pos)
            SimulatedEntity.x.clear_modified(entity)
            SimulatedEntity.y.clear_modified(entity)
        if SimulatedEntity.vx.was_modified(entity) or SimulatedEntity.vy.was_modified(
            entity
        ):
            self._simulation_core.set_velocity(handle, entity.vel)
            SimulatedEntity.vx.clear_modified(entity)
            SimulatedEntity.vy.clear_modified(entity)
        if SimulatedEntity.mass.was_modified(entity):
            self._simulation_core.set_mass(handle, entity.mass)
            SimulatedEntity.mass.clear_modified(entity)
        if SimulatedEntity.color.was_modified(entity):
            self._simulation_entity_descriptor.set_color(handle, entity.color)
            SimulatedEntity.color.clear_modified(entity)
        if SimulatedEntity.name.was_modified(entity):
            self._simulation_entity_descriptor.set_name(handle, entity.name)
            SimulatedEntity.name.clear_modified(entity)

    def update(self, dt: float) -> None:
        if not self._allow_before_the_beginning_of_time and self._chrono_trigger:
            if self._physics_total_time < 0.0:
                return

        if dt > self._physics_step_alloted_time_clamp:
            dt = self._physics_step_alloted_time_clamp

        self._physics_loop_accumulator += dt * self._time_scale
        while self._physics_loop_accumulator >= self._physics_timedelta:
            if self._chrono_trigger:
                timestep = -self._physics_timedelta
            else:
                timestep = self._physics_timedelta
            self._simulation_core.update(timestep)
            self._physics_loop_accumulator -= self._physics_timedelta
            self._physics_total_time += timestep

        merges = self._simulation_core.merge_entities()
        self._process_merges(merges)
        self._entity_cache.clear()

    def _process_merges(self, merges: list[MergeInfo]) -> None:
        for merge in merges:
            hdl1, hdl2 = merge.merged
            hdl_new = merge.into
            for callback in self._on_merge_callbacks:
                callback(hdl1, hdl2, hdl_new)

    def center_of_mass(self) -> pygame.Vector2:
        return self._simulation_core.center_of_mass()

    def entities_in_rect_iter(
        self, topleft: pygame.Vector2, bottomright: pygame.Vector2
    ) -> Iterator[SimulatedEntityHandle]:
        return self._simulation_core.entities_in_rect_iter(topleft, bottomright)

    def is_handle_valid(self, handle: SimulatedEntityHandle) -> bool:
        return self._simulation_core.is_handle_valid(handle)

    def get_last_point(self) -> Optional[SimulatedEntityHandle]:
        return self._simulation_entity_order_controller.last()

    def get_first_point(self) -> Optional[SimulatedEntityHandle]:
        return self._simulation_entity_order_controller.first()

    def get_next_point(
        self, handle: SimulatedEntityHandle
    ) -> Optional[SimulatedEntityHandle]:
        return self._simulation_entity_order_controller.next(handle)

    def get_prev_point(
        self, handle: SimulatedEntityHandle
    ) -> Optional[SimulatedEntityHandle]:
        return self._simulation_entity_order_controller.prev(handle)

    def on_merge(self, callback: OnMergeCallback) -> None:
        self._on_merge_callbacks.append(callback)

    def toggle_chrono_trigger(self) -> None:
        self._chrono_trigger = not self._chrono_trigger

    def is_chrono_trigger(self) -> bool:
        return self._chrono_trigger
