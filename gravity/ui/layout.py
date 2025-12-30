from enum import Enum
from dataclasses import dataclass
import pygame


class AnchorType(str, Enum):
    TOP_LEFT = "TOP_LEFT"
    TOP_RIGHT = "TOP_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"


@dataclass
class LayoutIcon:
    offset_ratio: tuple[float, float]
    size: tuple[int, int]
    anchor: AnchorType


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

    def resize(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self._width, self._height)

    @property
    def _split_x(self) -> int:
        return int(self._width * (1.0 - self._inspector_ratio))

    @property
    def viewport(self) -> pygame.Rect:
        return pygame.Rect(
            0,
            0,
            self._split_x,
            self._height,
        )

    @property
    def inspector(self) -> pygame.Rect:
        return pygame.Rect(
            self._split_x,
            0,
            self._width - self._split_x,
            self._height,
        )

    def _icon(
        self,
        parent: pygame.Rect,
        icon: LayoutIcon,
    ) -> pygame.Rect:
        x = parent.x + int(parent.w * icon.offset_ratio[0])
        y = parent.y + int(parent.h * icon.offset_ratio[1])

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

    @property
    def pause_icon(self) -> pygame.Rect:
        return self._icon(
            self.rect,
            self._pause_icon,
        )

    @property
    def camera_state_icon(self) -> pygame.Rect:
        return self._icon(
            self.rect,
            self._camera_state_icon,
        )
