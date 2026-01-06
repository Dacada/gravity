from typing import Optional, Self

import pygame

from gravity.camera import Camera, CameraController
from gravity.config.schema.render import Render as RenderConfig
from gravity.core import GameState
from gravity.layout import Layout
from gravity.physics import SimulatedEntity, SimulatedEntityHandle, SimulationController
from gravity.render.styles import IconStyle, IconStyleRenderArgs, RenderStyle
from gravity.types import Color
from gravity.ui import InspectorUIState, PauseController


class Renderer:
    def __init__(
        self, layout: Layout, style: RenderStyle, font_name: str, font_size: int
    ) -> None:
        self._layout = layout
        self._style = style
        self._font_name = font_name
        self._font_size = font_size

        self._screen = self._make_surface()
        self._font_optional: Optional[pygame.font.Font] = None

    @property
    def _font(self) -> pygame.font.Font:
        if self._font_optional is None:
            raise RuntimeError("must call initialize() first")
        return self._font_optional

    @classmethod
    def from_config(cls, cfg: RenderConfig, layout: Layout) -> Self:
        return cls(
            layout, RenderStyle.from_config(cfg.styles), cfg.font_name, cfg.font_size
        )

    def initialize(self) -> None:
        self._font_optional = pygame.font.SysFont(self._font_name, self._font_size)

    def render(self, game: GameState) -> None:
        self._maybe_resize(game)
        self._clear()
        self._render(game)
        pygame.display.flip()

    def _maybe_resize(self, game: GameState) -> None:
        new_size = game.query_resize()
        if new_size is not None:
            self._layout.resize(new_size)
            # actually, under wayland this does weird stuff
            # self._screen = self._make_surface()

    def _make_surface(self) -> pygame.Surface:
        return pygame.display.set_mode(self._layout.rect.size, pygame.RESIZABLE)

    def _clear(self) -> None:
        self._screen.fill((0, 0, 0))

    def _render(self, game: GameState) -> None:
        self._render_viewport(
            game.camera,
            game.simulation,
            game.inspector.get_selected_entity_handle(),
        )
        self._render_inspector(game.inspector, game.simulation)
        self._render_overlay(game.pause_controller, game.camera_controller)

    def _render_viewport(
        self,
        camera: Camera,
        simulation: SimulationController,
        selected_handle: Optional[SimulatedEntityHandle],
    ) -> None:
        viewport = self._layout.viewport
        topleft = camera.screen_to_world(pygame.Vector2(viewport.topleft))
        bottomright = camera.screen_to_world(pygame.Vector2(viewport.bottomright))
        entities_iter = simulation.entities_in_rect_iter(topleft, bottomright)
        for handle in entities_iter:
            entity = simulation.get(handle)
            if entity is not None:
                self._render_simulated_entity(camera, entity, handle == selected_handle)

    def _render_simulated_entity(
        self, camera: Camera, entity: SimulatedEntity, is_selected: bool
    ) -> None:

        screen_pos = camera.world_to_screen(entity.pos)

        # Draw point
        pygame.draw.circle(
            self._screen,
            entity.color,
            screen_pos,
            self._style.simulated_entity.radius,
        )

        # Draw selection reticle
        if is_selected:
            self._draw_simulated_entity_reticle(screen_pos)

        # Draw label
        if entity.name is not None:
            self._draw_simulated_entity_label(entity.name, entity.color, screen_pos)

    def _draw_simulated_entity_reticle(self, screen_pos: pygame.Vector2) -> None:
        radius = self._style.simulated_entity.radius
        padding = self._style.simulated_entity.reticle_padding
        line_width = self._style.simulated_entity.reticle_width
        color = self._style.simulated_entity.reticle_color

        size = (radius + padding) * 2

        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(screen_pos.x), int(screen_pos.y))

        pygame.draw.rect(
            self._screen,
            color,
            rect,
            width=line_width,
        )

    def _draw_simulated_entity_label(
        self, name: str, color: Color, start: pygame.Vector2
    ) -> None:
        diag_len = self._style.name.diagonal_length
        horiz_len = self._style.name.horizontal_length

        diag_end = start + pygame.Vector2(diag_len, -diag_len)
        horiz_end = diag_end + pygame.Vector2(-horiz_len, 0)

        pygame.draw.line(self._screen, color, start, diag_end, 1)
        pygame.draw.line(self._screen, color, diag_end, horiz_end, 1)

        text_surface = self._font.render(name, True, color)
        text_rect = text_surface.get_rect()

        # Right-justify text at the end of the horizontal line
        text_rect.midright = int(horiz_end.x), int(horiz_end.y)
        self._screen.blit(text_surface, text_rect)

    def _render_inspector(
        self, inspector: InspectorUIState, simulator: SimulationController
    ) -> None:
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

        selected_handle = inspector.get_selected_entity_handle()
        if selected_handle is None:
            return
        selected_entity = simulator.get(selected_handle)
        if selected_entity is None:
            return

        index_text = f"# {selected_entity.index}"
        self._render_text(index_text, panel, offset_y)
        offset_y += self._style.inspector.control_separation * 2

        for i, control in enumerate(inspector.controls):
            value = control.get_and_format(selected_entity)
            if value is None:
                value = control.get_empty_value_formatted()

            text = f"{control.label}: {value}"
            if i == inspector.get_current_idx():
                text += " ◀ "
                text += inspector.get_typing_input()

            self._render_text(text, panel, offset_y)
            offset_y += self._style.inspector.control_separation

    def _render_text(self, text: str, panel: pygame.Rect, y_offset: int) -> None:
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
        elif camera_controller.is_follow_center_of_mass_mode():
            self._render_com_icon()
        else:
            self._render_freecamera_icon(camera_controller.get_movement_directions())

    def _render_icon(
        self, layout_rect: pygame.Rect, style: IconStyle, kwargs: IconStyleRenderArgs
    ) -> None:
        surface = pygame.Surface(layout_rect.size, pygame.SRCALPHA)
        style.render(surface, **kwargs)
        icon_rect = surface.get_rect(center=layout_rect.center)
        self._screen.blit(surface, icon_rect)

    def _render_paused_icon(self, alpha: int) -> None:
        self._render_icon(
            self._layout.pause_icon,
            self._style.pause_icon,
            {"alpha": alpha},
        )

    def _render_target_icon(self) -> None:
        self._render_icon(
            self._layout.camera_state_icon,
            self._style.target_icon,
            {},
        )

    def _render_com_icon(self) -> None:
        self._render_icon(
            self._layout.camera_state_icon,
            self._style.com_icon,
            {},
        )

    def _render_freecamera_icon(self, dirs: tuple[int, int, int]) -> None:
        self._render_icon(
            self._layout.camera_state_icon,
            self._style.freecam_icon,
            {"dirs": dirs},
        )
