from gravity.ui.layout import Layout
from gravity.ui import InspectorUIState, PauseController
from gravity.render.styles import RenderStyle, IconStyle
from gravity.core import GameState
from gravity.camera import Camera, CameraController
from gravity.physics import PointMassSimulator, PointMass

import pygame

from typing import Optional


class Renderer:
    def __init__(self, layout: Layout, style: RenderStyle) -> None:
        self._layout = layout
        self._style = style

        self._screen = self._make_surface()
        self._font = pygame.font.SysFont("notosansmono", 12)

    def render(self, game: GameState) -> None:
        self._maybe_resize(game)
        self._clear()
        self._render(game)
        pygame.display.flip()

    def _maybe_resize(self, game: GameState) -> None:
        new_size = game.query_resize()
        if new_size is not None:
            self._layout.resize(*new_size)
            # actually, under wayland this does weird stuff
            # self._screen = self._make_surface()

    def _make_surface(self) -> pygame.Surface:
        return pygame.display.set_mode(self._layout.rect.size, pygame.RESIZABLE)

    def _clear(self) -> None:
        self._screen.fill((0, 0, 0))

    def _render(self, game: GameState) -> None:
        self._render_viewport(
            game.camera, game.points, game.inspector.get_selected_point()
        )
        self._render_inspector(game.inspector, game.points)
        self._render_overlay(game.pause_controller, game.camera_controller)

    def _render_viewport(
        self,
        camera: Camera,
        points: PointMassSimulator,
        selected_point: Optional[PointMass],
    ) -> None:
        for p in points:
            color = self._style.point_mass.color
            if selected_point is p:
                color = self._style.point_mass.selected_color

            screen_space_pos = camera.world_to_screen(p.pos)

            pygame.draw.circle(
                self._screen,
                color,
                (screen_space_pos.x, screen_space_pos.y),
                self._style.point_mass.radius,
            )

    def _render_inspector(
        self, inspector: InspectorUIState, points: PointMassSimulator
    ):
        panel = self._layout.inspector

        pygame.draw.rect(
            self._screen,
            self._style.inspector.bg_color,
            panel,
        )

        pygame.draw.line(
            self._screen,
            self._style.inspector.border_color,
            panel.topleft,
            panel.bottomleft,
            1,
        )

        offset_y = 0

        selected_point = inspector.get_selected_point()
        if selected_point is None:
            return

        total = points.get_total()
        curr = points.index(selected_point)
        if curr is not None:
            curr += 1

        index_text = f"{curr} / {total}"
        self._render_text(index_text, panel, offset_y)
        offset_y += self._style.inspector.control_separation * 2

        for i, control in enumerate(inspector.controls):
            text = f"{control.label}: {control.get():.3f}"
            if i == inspector.get_current_idx():
                text += " ◀ "
                text += inspector.get_typing_input()

            self._render_text(text, panel, offset_y)
            offset_y += self._style.inspector.control_separation

    def _render_text(self, text: str, panel: pygame.Rect, y_offset: int):
        x = panel.x + self._style.inspector.padding[0]
        y = panel.y + self._style.inspector.padding[1] + y_offset
        text_surface = self._font.render(text, True, self._style.inspector.text_color)
        text_rect = text_surface.get_rect(topleft=(x, y))
        self._screen.blit(text_surface, text_rect)

    def _render_overlay(
        self, pause_controller: PauseController, camera_controller: CameraController
    ) -> None:
        if pause_controller.is_paused():
            self._render_paused_icon(pause_controller.icon_alpha)
        if camera_controller.is_follow_selected_mass_mode():
            self._render_target_icon()
        if camera_controller.is_follow_center_of_mass_mode():
            self._render_com_icon()

    def _render_icon(
        self, layout_rect: pygame.Rect, style: IconStyle, args: tuple[int, ...]
    ) -> None:
        surface = pygame.Surface(layout_rect.size, pygame.SRCALPHA)
        style.render(surface, *args)
        icon_rect = surface.get_rect(center=layout_rect.center)
        self._screen.blit(surface, icon_rect)

    def _render_paused_icon(self, alpha: int) -> None:
        self._render_icon(
            self._layout.pause_icon,
            self._style.pause_icon,
            (alpha,),
        )

    def _render_target_icon(self) -> None:
        self._render_icon(
            self._layout.camera_state_icon,
            self._style.target_icon,
            (),
        )

    def _render_com_icon(self) -> None:
        self._render_icon(
            self._layout.camera_state_icon,
            self._style.com_icon,
            (),
        )
