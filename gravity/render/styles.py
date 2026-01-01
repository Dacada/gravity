import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self, TypedDict, Unpack

import pygame

from gravity.config.schema import (
    AppConfigRenderStyleComIcon,
    AppConfigRenderStyleFreeCamIcon,
    AppConfigRenderStyleInspector,
    AppConfigRenderStyleName,
    AppConfigRenderStylePauseIcon,
    AppConfigRenderStylePointMass,
    AppConfigRenderStyles,
    AppConfigRenderStyleTargetIcon,
)
from gravity.types import Color


class IconStyleRenderArgs(TypedDict, total=False):
    alpha: int
    dirs: tuple[int, int, int]


class IconStyle(ABC):
    @abstractmethod
    def render(
        self, surface: pygame.Surface, **kwargs: Unpack[IconStyleRenderArgs]
    ) -> None:
        pass


@dataclass
class PauseIconStyle(IconStyle):
    color: Color
    bar_width: int
    bar_height: int
    gap: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStylePauseIcon) -> Self:
        return cls(
            Color(*cfg.color),
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
    color: Color
    size: int
    center_radius: int
    corner_length: int
    corner_thickness: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStyleTargetIcon) -> Self:
        return cls(
            Color(*cfg.color),
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
    color: Color
    center_radius: int
    center_thickness: int
    dot_radius: int
    dot_distance: int
    dot_count: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStyleComIcon) -> Self:
        return cls(
            Color(*cfg.color),
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
class FreeCamIconStyle(IconStyle):
    color: Color
    tri_size: int
    circle_radius: int
    line_width: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStyleFreeCamIcon) -> Self:
        return cls(
            Color(*cfg.color),
            cfg.tri_size,
            cfg.circle_radius,
            cfg.line_width,
        )

    def render(
        self, surface: pygame.Surface, **kwargs: Unpack[IconStyleRenderArgs]
    ) -> None:
        dirs = kwargs.get("dirs")
        if dirs is None:
            raise RuntimeError("missing dirs value for free camera icon render")

        dx, dy, dz = dirs
        w, h = surface.get_size()
        cx, cy = w // 2, h // 2
        c = self.color

        # X direction (left / right)
        if dx != 0:
            if dx > 0:  # right
                points = [
                    (w, cy),
                    (w - self.tri_size, cy - self.tri_size),
                    (w - self.tri_size, cy + self.tri_size),
                ]
            else:  # left
                points = [
                    (0, cy),
                    (self.tri_size, cy - self.tri_size),
                    (self.tri_size, cy + self.tri_size),
                ]
            pygame.draw.polygon(surface, c, points)

        # Y direction (up / down)
        if dy != 0:
            if dy > 0:  # down
                points = [
                    (cx, h),
                    (cx - self.tri_size, h - self.tri_size),
                    (cx + self.tri_size, h - self.tri_size),
                ]
            else:  # up
                points = [
                    (cx, 0),
                    (cx - self.tri_size, self.tri_size),
                    (cx + self.tri_size, self.tri_size),
                ]
            pygame.draw.polygon(surface, c, points)

        # Z direction (zoom)
        if dz != 0:
            pygame.draw.circle(
                surface, c, (cx, cy), self.circle_radius, self.line_width
            )
            if dz > 0:
                # inwards: empty
                pass
            else:
                # outwards: dot
                pygame.draw.circle(surface, c, (cx, cy), self.line_width * 2)


@dataclass
class InspectorStyle:
    bg_color: Color
    border_color: Color
    text_color: Color
    padding: pygame.Vector2
    control_separation: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStyleInspector) -> Self:
        return cls(
            Color(*cfg.bg_color),
            Color(*cfg.border_color),
            Color(*cfg.text_color),
            pygame.Vector2(cfg.padding),
            cfg.control_separation,
        )


@dataclass
class PointMassStyle:
    radius: int
    reticle_padding: int
    reticle_width: int
    reticle_color: Color

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStylePointMass) -> Self:
        return cls(
            cfg.radius,
            cfg.reticle_padding,
            cfg.reticle_width,
            Color(*cfg.reticle_color),
        )


@dataclass
class NameStyle:
    diagonal_length: int
    horizontal_length: int

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStyleName) -> Self:
        return cls(
            cfg.diagonal_length,
            cfg.horizontal_length,
        )


@dataclass
class RenderStyle:
    pause_icon: IconStyle
    target_icon: IconStyle
    com_icon: IconStyle
    freecam_icon: IconStyle
    inspector: InspectorStyle
    point_mass: PointMassStyle
    name: NameStyle

    @classmethod
    def from_config(cls, cfg: AppConfigRenderStyles) -> Self:
        return cls(
            PauseIconStyle.from_config(cfg.pause_icon),
            TargetIconStyle.from_config(cfg.target_icon),
            CenterOfMassRingIconStyle.from_config(cfg.com_icon),
            FreeCamIconStyle.from_config(cfg.freecam_icon),
            InspectorStyle.from_config(cfg.inspector),
            PointMassStyle.from_config(cfg.point_mass),
            NameStyle.from_config(cfg.name),
        )
