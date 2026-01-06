from dataclasses import dataclass
from typing import Self

import pygame

from gravity.config.schema.layout import Icon as LayoutIconConfig
from gravity.config.schema.layout import Layout as LayoutConfig
from gravity.types import AnchorType


@dataclass
class LayoutIcon:
    offset_ratio: pygame.Vector2
    size: pygame.Vector2
    anchor: AnchorType

    @classmethod
    def from_config(cls, cfg: LayoutIconConfig) -> Self:
        return cls(
            pygame.Vector2(cfg.offset_ratio), pygame.Vector2(cfg.size), cfg.anchor
        )


class Layout:
    def __init__(
        self,
        width: int,
        height: int,
        inspector_ratio: float,
        pause_icon: LayoutIcon,
        camera_state_icon: LayoutIcon,
    ):
        self._width = width
        self._height = height

        self._inspector_ratio = inspector_ratio
        self._pause_icon = pause_icon
        self._camera_state_icon = camera_state_icon

        self.rect: pygame.Rect
        self.viewport: pygame.Rect
        self.inspector: pygame.Rect
        self.pause_icon: pygame.Rect
        self.camera_state_icon: pygame.Rect

        self._recalculate()

    @classmethod
    def from_config(cls, cfg: LayoutConfig) -> Self:
        return cls(
            cfg.width,
            cfg.height,
            cfg.inspector_ratio,
            LayoutIcon.from_config(cfg.pause_icon),
            LayoutIcon.from_config(cfg.camera_state_icon),
        )

    def resize(self, size: pygame.Vector2) -> None:
        self._width = int(size.x)
        self._height = int(size.y)
        self._recalculate()

    @property
    def _split_x(self) -> int:
        return int(self._width * (1.0 - self._inspector_ratio))

    def _icon(
        self,
        parent: pygame.Rect,
        icon: LayoutIcon,
    ) -> pygame.Rect:
        x = parent.x + parent.w * icon.offset_ratio[0]
        y = parent.y + parent.h * icon.offset_ratio[1]

        w, h = icon.size

        if icon.anchor == AnchorType.TOP_LEFT:
            pass
        elif icon.anchor == AnchorType.TOP_RIGHT:
            x -= w
        elif icon.anchor == AnchorType.BOTTOM_LEFT:
            y -= h
        elif icon.anchor == AnchorType.BOTTOM_RIGHT:
            x -= w
            y -= h

        return pygame.Rect(x, y, w, h)

    def _recalculate(self) -> None:
        self.rect = pygame.Rect(0, 0, self._width, self._height)
        self.viewport = pygame.Rect(
            0,
            0,
            self._split_x,
            self._height,
        )
        self.inspector = pygame.Rect(
            self._split_x,
            0,
            self._width - self._split_x,
            self._height,
        )
        self.pause_icon = self._icon(
            self.rect,
            self._pause_icon,
        )
        self.camera_state_icon = self._icon(
            self.rect,
            self._camera_state_icon,
        )
