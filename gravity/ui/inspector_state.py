from typing import Optional
from gravity.physics import PointMass

import logging

logger = logging.getLogger(__name__)


class InspectorUIControlState:
    def __init__(
        self, inspector: "InspectorUIState", label: str, attr_name: str
    ) -> None:
        self.label = label
        self._inspector = inspector
        self._attr_name = attr_name

    def get(self) -> float:
        p = self._inspector.get_selected_point()
        if p is None:
            return 0.0
        return getattr(p, self._attr_name, 0.0)

    def set(self, v: float):
        p = self._inspector.get_selected_point()
        if p is None:
            return
        return setattr(p, self._attr_name, v)


class InspectorUIState:
    def __init__(self) -> None:
        self.controls = [
            InspectorUIControlState(self, "X Pos", "x"),
            InspectorUIControlState(self, "Y Pos", "y"),
            InspectorUIControlState(self, "X Vel", "vx"),
            InspectorUIControlState(self, "Y Vel", "vy"),
            InspectorUIControlState(self, "Mass", "mass"),
        ]
        self._selected_point_mass: Optional[PointMass] = None
        self._current_idx = 0
        self._typing = ""

    def reset(self) -> None:
        self._selected_point_mass = None
        self._current_idx = 0
        self._typing = ""

    def get_selected_point(self) -> Optional[PointMass]:
        return self._selected_point_mass

    def set_selected_point(self, point: PointMass) -> None:
        self._selected_point_mass = point

    def unselect_point(self) -> None:
        self._selected_point_mass = None

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

    def try_commit(self) -> None:
        try:
            val = float(self._typing)
        except ValueError:
            logger.info(f"failed to parse '{self._typing}' as float")
            return

        self.controls[self._current_idx].set(val)
        self._typing = ""
