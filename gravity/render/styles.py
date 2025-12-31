import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self, TypedDict, Unpack

import pygame

from gravity.config.schema import (
    AppConfigRenderStyleComIcon,
    AppConfigRenderStyleInspector,
    AppConfigRenderStylePauseIcon,
    AppConfigRenderStylePointMass,
    AppConfigRenderStyles,
    AppConfigRenderStyleTargetIcon,
)


class IconStyleRenderArgs(TypedDict, total=False):
    alpha: int


class IconStyle(ABC):
    @abstractmethod
    def render(
        self, surface: pygame.Surface, **kwargs: Unpack[IconStyleRenderArgs]
    ) -> None:
        pass


@dataclass
class PauseIconStyle(IconStyle):
    color: tuple[int, int, int]
    bar_width: int
    bar_height: int
    gap: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStylePauseIcon) -> Self:
        return cls(
            cfg.color,
            cfg.bar_width,
            cfg.bar_height,
            cfg.gap,
        )

    def render(
        self, surface: pygame.Surface, **kwargs: Unpack[IconStyleRenderArgs]
    ) -> None:
        alpha = kwargs.get("alpha")
        if alpha is None:
            raise RuntimeError("missing alpha value for pause icon render")

        color = (*self.color, alpha)
        pygame.draw.rect(surface, color, (0, 0, self.bar_width, self.bar_height))
        pygame.draw.rect(
            surface,
            color,
            (self.bar_width + self.gap, 0, self.bar_width, self.bar_height),
        )


@dataclass
class TargetIconStyle(IconStyle):
    color: tuple[int, int, int]
    size: int
    center_radius: int
    corner_length: int
    corner_thickness: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStyleTargetIcon) -> Self:
        return cls(
            cfg.color,
            cfg.size,
            cfg.center_radius,
            cfg.corner_length,
            cfg.corner_thickness,
        )

    def render(
        self, surface: pygame.Surface, **kwargs: Unpack[IconStyleRenderArgs]
    ) -> None:
        s = self.size
        l = self.corner_length
        t = self.corner_thickness
        c = self.color

        cx = cy = s // 2

        pygame.draw.circle(surface, c, (cx, cy), self.center_radius)

        def h_bar(x: int, y: int) -> None:
            pygame.draw.rect(
                surface,
                c,
                (x, y, l, t),
            )

        def v_bar(x: int, y: int) -> None:
            pygame.draw.rect(
                surface,
                c,
                (x, y, t, l),
            )

        h_bar(0, 0)
        v_bar(0, 0)

        h_bar(s - l, 0)
        v_bar(s - t, 0)

        h_bar(0, s - t)
        v_bar(0, s - l)

        h_bar(s - l, s - t)
        v_bar(s - t, s - l)


@dataclass
class CenterOfMassRingIconStyle(IconStyle):
    color: tuple[int, int, int]
    center_radius: int
    center_thickness: int
    dot_radius: int
    dot_distance: int
    dot_count: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStyleComIcon) -> Self:
        return cls(
            cfg.color,
            cfg.center_radius,
            cfg.center_thickness,
            cfg.dot_radius,
            cfg.dot_distance,
            cfg.dot_count,
        )

    def render(
        self, surface: pygame.Surface, **kwargs: Unpack[IconStyleRenderArgs]
    ) -> None:
        cx = surface.get_width() // 2
        cy = surface.get_height() // 2

        # Draw central ring
        pygame.draw.circle(
            surface, self.color, (cx, cy), self.center_radius, self.center_thickness
        )

        # Draw surrounding masses
        for i in range(self.dot_count):
            angle = i * (2 * math.pi / self.dot_count)

            x = cx + int(math.cos(angle) * self.dot_distance)
            y = cy + int(math.sin(angle) * self.dot_distance)

            pygame.draw.circle(surface, self.color, (x, y), self.dot_radius)


@dataclass
class InspectorStyle:
    bg_color: tuple[int, int, int]
    border_color: tuple[int, int, int]
    text_color: tuple[int, int, int]
    padding: tuple[int, int]
    control_separation: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStyleInspector) -> Self:
        return cls(
            cfg.bg_color,
            cfg.border_color,
            cfg.text_color,
            cfg.padding,
            cfg.control_separation,
        )


@dataclass
class PointMassStyle:
    color: tuple[int, int, int]
    selected_color: tuple[int, int, int]
    radius: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStylePointMass) -> Self:
        return cls(
            cfg.color,
            cfg.selected_color,
            cfg.radius,
        )


@dataclass
class RenderStyle:
    pause_icon: IconStyle
    target_icon: IconStyle
    com_icon: IconStyle
    inspector: InspectorStyle
    point_mass: PointMassStyle

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStyles) -> Self:
        return cls(
            PauseIconStyle.from_config(cfg.pause_icon),
            TargetIconStyle.from_config(cfg.target_icon),
            CenterOfMassRingIconStyle.from_config(cfg.com_icon),
            InspectorStyle.from_config(cfg.inspector),
            PointMassStyle.from_config(cfg.point_mass),
        )
