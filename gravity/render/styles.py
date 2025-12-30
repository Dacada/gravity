from abc import ABC, abstractmethod
from dataclasses import dataclass

import math
import pygame


class IconStyle(ABC):
    @abstractmethod
    def render(self, surface: pygame.Surface, *args):
        pass


@dataclass
class PauseIconStyle(IconStyle):
    color: tuple[int, int, int]
    bar_width: int
    bar_height: int
    gap: int

    def render(self, surface: pygame.Surface, *args):
        alpha = args[0]
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

    def render(self, surface: pygame.Surface, *args):
        s = self.size
        l = self.corner_length
        t = self.corner_thickness
        c = self.color

        cx = cy = s // 2

        pygame.draw.circle(surface, c, (cx, cy), self.center_radius)

        def h_bar(x, y):
            pygame.draw.rect(
                surface,
                c,
                (x, y, l, t),
            )

        def v_bar(x, y):
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

    def render(self, surface: pygame.Surface, *args):
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


@dataclass
class PointMassStyle:
    color: tuple[int, int, int]
    selected_color: tuple[int, int, int]
    radius: int


@dataclass
class RenderStyle:
    pause_icon: IconStyle
    target_icon: IconStyle
    com_icon: IconStyle
    inspector: InspectorStyle
    point_mass: PointMassStyle
