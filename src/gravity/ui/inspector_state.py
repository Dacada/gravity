import logging
from typing import Any, Callable, Optional, Protocol, Self

from gravity.config.schema.ui import Format as FormatConfig
from gravity.physics import SimulatedEntity, SimulatedEntityHandle, SimulationController
from gravity.types import Color

logger = logging.getLogger(__name__)


class UIControl(Protocol):
    label: str

    def get_and_format(self, p: Optional[SimulatedEntity]) -> Optional[str]: ...
    def get_empty_value_formatted(self) -> str: ...
    def parse_and_set(self, v: str, p: SimulatedEntity) -> bool: ...


class InspectorUIControlState[T]:
    def __init__(
        self,
        label: str,
        attr_name: str,
        parser: Callable[[str], T],
        formatter: Callable[[T], str],
    ) -> None:
        self.label = label
        self._attr_name = attr_name
        self._parser = parser
        self._formatter = formatter

    def get_and_format(self, p: Optional[SimulatedEntity]) -> Optional[str]:
        if p is None:
            return None
        val = getattr(p, self._attr_name, None)
        if val is None:
            return None
        return self._formatter(val)

    def get_empty_value_formatted(self) -> str:
        return "<empty>"

    def parse_and_set(self, v: str, p: SimulatedEntity) -> bool:
        val = self._parse(v)
        if val is None:
            return False
        setattr(p, self._attr_name, val)
        return True

    def _parse(self, v: str) -> Optional[T]:
        try:
            val = self._parser(v)
        except ValueError as e:
            logger.info(f"failed to parse '{v}' as {self._parser.__name__}: {e}")
            return None
        else:
            return val


def _make_formatter(format_spec: str) -> Callable[[Any], str]:
    def formatter(value: Any) -> str:
        return format(value, format_spec)

    return formatter


def _mass_parser(mass: str) -> float:
    m = float(mass)
    if m <= 0:
        raise ValueError("invalid nonpositive mass")
    return m


class InspectorUIState:
    def __init__(
        self,
        position_value_formatter: Callable[[float], str],
        velocity_value_formatter: Callable[[float], str],
        mass_value_formatter: Callable[[float], str],
    ) -> None:
        self.controls: list[UIControl] = [
            InspectorUIControlState("Name", "name", str, lambda s: s),
            InspectorUIControlState("Color", "color", Color.from_str, Color.as_str),
            InspectorUIControlState("X Pos", "x", float, position_value_formatter),
            InspectorUIControlState("Y Pos", "y", float, position_value_formatter),
            InspectorUIControlState("X Vel", "vx", float, velocity_value_formatter),
            InspectorUIControlState("Y Vel", "vy", float, velocity_value_formatter),
            InspectorUIControlState("Mass", "mass", _mass_parser, mass_value_formatter),
        ]
        self._selected_entity: Optional[SimulatedEntityHandle] = None
        self._current_idx = 0
        self._typing = ""

    @classmethod
    def from_config(cls, cfg: FormatConfig) -> Self:
        return cls(
            _make_formatter(cfg.position_format),
            _make_formatter(cfg.velocity_format),
            _make_formatter(cfg.mass_format),
        )

    def reset(self) -> None:
        self._selected_entity = None
        self._current_idx = 0
        self._typing = ""

    def get_selected_entity_handle(self) -> Optional[SimulatedEntityHandle]:
        return self._selected_entity

    def set_selected_entity_handle(self, entity: SimulatedEntityHandle) -> None:
        self._selected_entity = entity

    def unselect_entity_handle(self) -> None:
        self._selected_entity = None

    def get_current_idx(self) -> int:
        return self._current_idx

    def cycle_forward(self) -> None:
        self._current_idx += 1
        self._current_idx %= len(self.controls)

    def cycle_backward(self) -> None:
        self._current_idx -= 1
        self._current_idx %= len(self.controls)

    def type_input(self, char: str) -> None:
        self._typing += char

    def type_backspace(self) -> None:
        if self._typing:
            self._typing = self._typing[:-1]

    def get_typing_input(self) -> str:
        return self._typing

    def try_commit(self, simulation: SimulationController) -> None:
        control = self.controls[self._current_idx]
        handler = self.get_selected_entity_handle()
        if handler is not None:
            entity = simulation.get(handler)
            if entity is None:
                return
            success = control.parse_and_set(self._typing, entity)
            if success:
                simulation.apply(entity)
                self._typing = ""
