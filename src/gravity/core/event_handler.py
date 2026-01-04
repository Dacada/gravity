import logging

import pygame

from gravity.core import GameState
from gravity.layout import Layout

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
                self._game.simulation.create(pos=pos_world)
        elif event.button == RIGHT_MOUSE_BUTTON:
            handle = self._game.cursor_ui_controller.find_closest_point_screen_space(
                self._game.camera,
                self._game.simulation,
                pygame.Vector2(event.pos),
            )
            if handle is None:
                self._game.inspector.unselect_entity_handle()
            else:
                self._game.inspector.set_selected_entity_handle(handle)

    def on_KeyDown(self, event: pygame.event.Event) -> None:
        is_control = bool(event.mod & pygame.KMOD_CTRL)
        is_camera = bool(event.mod & pygame.KMOD_ALT)

        if is_control and is_camera:
            return

        if is_control and self._handle_control(event):
            return

        if is_camera and self._handle_camera(event):
            return

        if self._handle_inspector(event):
            return

        if self._handle_text_input(event):
            return

    def on_KeyUp(self, event: pygame.event.Event) -> None:
        self._handle_camera_keyup(event)

    def on_VideoResize(self, event: pygame.event.Event) -> None:
        self._game.resize(event.w, event.h)

    def _handle_control(self, event: pygame.event.Event) -> bool:
        # pause/unpause
        if event.key == pygame.K_SPACE:
            self._game.pause_controller.toggle_paused()
            return True

        # select via keyboard (maybe from unselected)
        if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
            left = event.key == pygame.K_LEFT

            handle = self._game.inspector.get_selected_entity_handle()
            if handle is None:
                if left:
                    handle = self._game.simulation.get_last_point()
                else:
                    handle = self._game.simulation.get_first_point()
            else:
                if left:
                    handle = self._game.simulation.get_prev_point(handle)
                else:
                    handle = self._game.simulation.get_next_point(handle)

            if handle is not None:
                self._game.inspector.set_selected_entity_handle(handle)

            return True

        return False

    def _handle_camera(self, event: pygame.event.Event) -> bool:
        moved = False
        if event.key == pygame.K_LEFT:
            self._game.camera_controller.set_pan_direction_left()
            moved = True
        if event.key == pygame.K_RIGHT:
            self._game.camera_controller.set_pan_direction_right()
            moved = True
        if event.key == pygame.K_UP:
            self._game.camera_controller.set_pan_direction_up()
            moved = True
        if event.key == pygame.K_DOWN:
            self._game.camera_controller.set_pan_direction_down()
            moved = True
        if event.key == pygame.K_z:
            if event.mod & pygame.KMOD_SHIFT:
                self._game.camera_controller.set_zoom_direction_out()
            else:
                self._game.camera_controller.set_zoom_direction_in()
            moved = True
        if moved:
            return True

        if event.key == pygame.K_f:
            if self._game.camera_controller.is_follow_selected_mass_mode():
                self._game.camera_controller.unset_follow_mode()
            else:
                if self._game.inspector.get_selected_entity_handle() is not None:
                    self._game.camera_controller.set_follow_mode_selected_mass()
            return True

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

    def _handle_inspector(self, event: pygame.event.Event) -> bool:
        handle = self._game.inspector.get_selected_entity_handle()
        if handle is None:
            return False

        # delete selection
        if event.key == pygame.K_DELETE:
            self._game.inspector.unselect_entity_handle()
            self._game.simulation.delete(handle)
            return True

        # navigate inspector via tab
        if event.key == pygame.K_TAB:
            if event.mod & pygame.KMOD_SHIFT:
                self._game.inspector.cycle_backward()
            else:
                self._game.inspector.cycle_forward()
            return True

        # navigate inspector via up/down
        if event.key == pygame.K_UP:
            self._game.inspector.cycle_backward()
            return True
        if event.key == pygame.K_DOWN:
            self._game.inspector.cycle_forward()
            return True

        # reset inspector state
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
            self._game.inspector.try_commit(self._game.simulation)
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
            callback = getattr(self, f"on_{event_name}", None)
            if callback is not None:
                callback(event)
