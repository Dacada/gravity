import math
from enum import Enum, auto
from typing import Self

from gravity.config.schema.ui import Animation


class AnimationName(Enum):
    PAUSE = auto()
    CHRONO_TRIGGER = auto()


class FadeController:
    def __init__(self) -> None:
        self._animation_speeds: dict[AnimationName, float] = {}
        self._animation_states: dict[AnimationName, bool] = {}
        self._animation_timers: dict[AnimationName, float] = {}
        self._animation_alphas: dict[AnimationName, int] = {}

    @classmethod
    def from_config(cls, cfg: Animation) -> Self:
        self = cls()
        pause = cfg.pause
        chrono_trigger = cfg.chrono_trigger
        self.add_animation(AnimationName.PAUSE, pause.speed)
        self.add_animation(AnimationName.CHRONO_TRIGGER, chrono_trigger.speed)
        return self

    def add_animation(self, name: AnimationName, speed: float) -> None:
        self._animation_speeds[name] = speed
        self._animation_states[name] = False
        self._animation_timers[name] = 0.0
        self._animation_alphas[name] = 255

    def toggle_animation(self, name: AnimationName) -> None:
        self._animation_states[name] = not self._animation_states[name]

    def is_animation_running(self, name: AnimationName) -> bool:
        return self._animation_states[name]

    def current_alpha(self, name: AnimationName) -> int:
        return self._animation_alphas[name]

    def update(self, dt: float) -> None:
        for name, state in self._animation_states.items():
            if not state:
                self._animation_timers[name] = 0.0
                continue

            self._animation_timers[name] += dt
            alpha = 0.5 * (
                1
                + math.cos(self._animation_speeds[name] * self._animation_timers[name])
            )
            self._animation_alphas[name] = round(255 * alpha)
