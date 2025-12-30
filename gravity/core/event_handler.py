from gravity.core import GameState
from gravity.ui.layout import Layout
from gravity.physics import PointMass

import pygame
import logging

logger = logging.getLogger(__name__)

LEFT_MOUSE_BUTTON = 1
RIGHT_MOUSE_BUTTON = 3


class EventHandler:
    def __init__(self, game: GameState, layout: Layout) -> None:
        self._game = game
        self._layout = layout

    def on_Quit(self, event: pygame.event.Event) -> None:
        logger.info("received quit event")
        self._game.stop()

    def on_MouseButtonDown(self, event: pygame.event.Event) -> None:
        if event.button == LEFT_MOUSE_BUTTON:
            if self._game.cursor_ui_controller.is_viewport_click_allowed(event.pos):
                pos = pygame.Vector2(*event.pos)
                pos_world = self._game.camera.screen_to_world(pos)
                self._game.points.create(pos_world)
        elif event.button == RIGHT_MOUSE_BUTTON:
            p = self._game.cursor_ui_controller.find_closest_point_screen_space(
                self._game.points, self._game.camera, event.pos
            )
            if p is None:
                self._game.inspector.unselect_point()
            else:
                self._game.inspector.set_selected_point(p)

    def on_KeyDown(self, event: pygame.event.Event) -> None:
        if self._handle_global(event):
            return

        if self._handle_camera(event):
            return

        p = self._game.inspector.get_selected_point()
        if p is not None:
            if self._handle_inspector(event, p):
                return
            if self._handle_text_input(event):
                return

    def on_KeyUp(self, event: pygame.event.Event) -> None:
        self._handle_camera_keyup(event)

    def on_VideoResize(self, event: pygame.event.Event) -> None:
        self._game.resize(event.w, event.h)

    def _handle_global(self, event: pygame.event.Event) -> bool:
        # pause/unpause
        if event.key == pygame.K_SPACE:
            self._game.pause_controller.toggle_paused()
            return True

        # select via keyboard (maybe from unselected)
        if not (event.mod & pygame.KMOD_ALT):
            if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                if event.key == pygame.K_LEFT:
                    inc = -1
                else:
                    inc = 1
                p = self._game.inspector.get_selected_point()
                if p is not None:
                    idx = self._game.points.index(p)
                    if idx is not None:
                        q = self._game.points.by_index(idx + inc)
                        if q is not None:
                            self._game.inspector.set_selected_point(q)
                else:
                    p = self._game.points.by_index(0)
                    if p is not None:
                        self._game.inspector.set_selected_point(p)
                return True

        return False

    def _handle_camera(self, event: pygame.event.Event) -> bool:
        if event.mod & pygame.KMOD_ALT:
            if event.key == pygame.K_LEFT:
                self._game.camera_controller.set_pan_direction_left()
            if event.key == pygame.K_RIGHT:
                self._game.camera_controller.set_pan_direction_right()
            if event.key == pygame.K_UP:
                self._game.camera_controller.set_pan_direction_up()
            if event.key == pygame.K_DOWN:
                self._game.camera_controller.set_pan_direction_down()
            if event.key == pygame.K_z:
                if event.mod & pygame.KMOD_SHIFT:
                    self._game.camera_controller.set_zoom_direction_out()
                else:
                    self._game.camera_controller.set_zoom_direction_in()
            if event.key == pygame.K_f:
                if self._game.camera_controller.is_follow_selected_mass_mode():
                    self._game.camera_controller.unset_follow_mode()
                else:
                    if self._game.inspector.get_selected_point() is not None:
                        self._game.camera_controller.set_follow_mode_selected_mass()
            if event.key == pygame.K_c:
                if self._game.camera_controller.is_follow_center_of_mass_mode():
                    self._game.camera_controller.unset_follow_mode()
                else:
                    self._game.camera_controller.set_follow_mode_center_of_mass()
            return True

        return False

    def _handle_camera_keyup(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_LEFT:
            self._game.camera_controller.reset_pan_direction_left()
        if event.key == pygame.K_RIGHT:
            self._game.camera_controller.reset_pan_direction_right()
        if event.key == pygame.K_UP:
            self._game.camera_controller.reset_pan_direction_up()
        if event.key == pygame.K_DOWN:
            self._game.camera_controller.reset_pan_direction_down()
        if event.key == pygame.K_z:
            self._game.camera_controller.reset_zoom_direction()

    def _handle_inspector(self, event: pygame.event.Event, p: PointMass) -> bool:
        # delete selection
        if event.key == pygame.K_DELETE:
            self._game.inspector.unselect_point()
            self._game.points.delete(p)
            return True

        # navigate inspector via tab
        if event.key == pygame.K_TAB:
            if event.mod & pygame.KMOD_SHIFT:
                self._game.inspector.cycle_backward()
            else:
                self._game.inspector.cycle_forward()
            return True

        # navigate inspector via up/down
        if not (event.mod & pygame.KMOD_ALT):
            if event.key == pygame.K_UP:
                self._game.inspector.cycle_backward()
                return True
            if event.key == pygame.K_DOWN:
                self._game.inspector.cycle_forward()
                return True

        # reset inspector state and unselect
        if event.key == pygame.K_ESCAPE:
            self._game.inspector.reset()
            return True

        return False

    def _handle_text_input(self, event: pygame.event.Event) -> bool:
        # remove latest inputted character
        if event.key == pygame.K_BACKSPACE:
            self._game.inspector.type_backspace()
            return True

        # commit typed text in inspector value
        if event.key == pygame.K_RETURN:
            self._game.inspector.try_commit()
            return True

        # input character if visible character
        char = event.unicode
        if char:
            self._game.inspector.type_input(char)
            return True

        return False

    def handle_events(self) -> None:
        for event in pygame.event.get():
            event_name = pygame.event.event_name(event.type)
            name_for_log_msg = f"{event_name} ({event.type})"

            logger.debug(f"process event: {name_for_log_msg}")
            callback = getattr(self, f"on_{event_name}", None)
            if callback is not None:
                callback(event)
