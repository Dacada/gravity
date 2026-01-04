import math
from typing import Self

from gravity.config.schema import AppConfigPauseAnimation


class PauseController:
    def __init__(self, animation_speed: float):
        self._animation_speed = animation_speed

        self._paused = True
        self._paused_timer = 0.0
        self.icon_alpha = 255

    @classmethod
    def from_config(cls, cfg: AppConfigPauseAnimation) -> Self:
        return cls(cfg.speed)

    def toggle_paused(self) -> None:
        self._paused = not self._paused

    def is_paused(self) -> bool:
        return self._paused

    def update(self, dt: float) -> None:
        if self.is_paused():
            self._paused_timer += dt
            alpha = 0.5 * (1 + math.cos(self._animation_speed * self._paused_timer))
            self.icon_alpha = round(255 * alpha)
        else:
            self._paused_timer = 0
