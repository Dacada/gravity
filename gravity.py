from enum import Enum, auto
import pygame
import logging
from typing import Iterable, Iterator, Optional
from dataclasses import dataclass
import math

PAUSE_ICON_WIDTH = 40
PAUSE_ICON_HEIGHT = 50
PAUSE_ICON_COLOR = (255, 255, 255)
PAUSE_ICON_BAR_WIDTH = 10
PAUSE_ICON_GAP = 8
PAUSED_ANIMATION_SPEED = 2.5

INSPECTOR_BG_COLOR = (30, 30, 30)
INSPECTOR_BORDER_COLOR = (80, 80, 80)
INSPECTOR_TEXT_COLOR = (255, 255, 255)
INSPECTOR_PADDING_X = 20
INSPECTOR_PADDING_Y = 50
INSPECTOR_CONTROL_SEPARATION = 15

POINT_MASS_RENDER_COLOR = (255, 255, 255)
POINT_MASS_RENDER_SELECTED_COLOR = (255, 0, 0)
POINT_MASS_RENDER_RADIUS = 4

CAMERA_PAN_SPEED = 100
ZOOM_FACTOR = 1.5

LEFT_MOUSE_BUTTON = 1
RIGHT_MOUSE_BUTTON = 3

logger = logging.getLogger(__name__)

class Layout:
    def __init__(self, height: int, viewport_width: int, inspector_width: int, pause_icon_offset: tuple[int, int], pause_icon_dimensions: tuple[int, int]):
        self._height = height
        self._viewport_width = viewport_width
        self._inspector_width = inspector_width
        self._pause_icon_offset = pause_icon_offset
        self._pause_icon_dimensions = pause_icon_dimensions

    def get_viewport_center(self) -> pygame.Vector2:
        return pygame.Vector2(self._viewport_width / 2, self._height / 2)

    def get_dimensions(self) -> tuple[int, int]:
        return (self._viewport_width + self._inspector_width, self._height)

    def get_inspector_panel_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self._viewport_width, 0,
            self._inspector_width, self._height,
        )

    def get_viewport_rect(self) -> pygame.Rect:
        return pygame.Rect(
            0, 0,
            self._viewport_width, self._height,
        )

    def get_pause_icon_center_location(self) -> pygame.Vector2:
        return pygame.Vector2(
            self._pause_icon_offset[0] + self._pause_icon_dimensions[0] / 2,
            self._pause_icon_offset[1] + self._pause_icon_dimensions[1] / 2,
        )


@dataclass
class PointMass:
    pos: pygame.Vector2
    vel: pygame.Vector2
    mass: float

    @property
    def x(self) -> float:
        return self.pos.x

    @x.setter
    def x(self, value: float) -> None:
        self.pos.x = value

    @property
    def y(self) -> float:
        return self.pos.y

    @y.setter
    def y(self, value: float) -> None:
        self.pos.y = value

    @property
    def vx(self) -> float:
        return self.vel.x

    @vx.setter
    def vx(self, value: float) -> None:
        self.vel.x = value

    @property
    def vy(self) -> float:
        return self.vel.y

    @vy.setter
    def vy(self, value: float) -> None:
        self.vel.y = value


class PointMassSimulator(Iterable[PointMass]):
    def __init__(self, gravitational_constant: float, softening_factor: float, merge_distance_squared: float) -> None:
        self._gravitational_constant = gravitational_constant
        self._softening_factor = softening_factor
        self._merge_distance_squared = merge_distance_squared

        self._masses: list[PointMass] = []

    def create(self, pos: pygame.Vector2, mass: float = 1.0) -> PointMass:
        p = PointMass(
            pos,
            pygame.Vector2(0.0, 0.0),
            mass,
        )
        self._masses.append(p)
        return p

    def delete(self, p: PointMass):
        for i, pp in enumerate(self._masses):
            if pp is p:
                del self._masses[i]
                return

    def index(self, p: PointMass) -> Optional[int]:
        for i, q in enumerate(self._masses):
            if q is p:
                return i
        return None

    def by_index(self, idx: int) -> Optional[PointMass]:
        try:
            return self._masses[idx % self.get_total()]
        except IndexError:
            return None

    def get_total(self) -> int:
        return len(self._masses)

    def center_of_mass(self) -> pygame.Vector2:
        total_mass = 0.0
        com = pygame.Vector2(0.0, 0.0)

        for p in self._masses:
            com += p.pos * p.mass
            total_mass += p.mass

        if total_mass > 0:
            com /= total_mass

        return com


    def update(self, dt: float) -> None:
        self._merge_all_masses()

        acc_old = self._compute_accelerations()

        for i, p in enumerate(self._masses):
            p.pos += p.vel * dt + 0.5 * acc_old[i] * dt * dt

        acc_new = self._compute_accelerations()

        for i, p in enumerate(self._masses):
            p.vel += 0.5 * (acc_old[i] + acc_new[i]) * dt

    def _compute_accelerations(self) -> list[pygame.Vector2]:
        n = len(self._masses)
        acc = [pygame.Vector2(0.0, 0.0) for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                r = self._masses[j].pos - self._masses[i].pos
                dist_sq = r.length_squared() + self._softening_factor
                inv_dist = 1.0 / math.sqrt(dist_sq)

                factor = self._gravitational_constant * inv_dist / dist_sq

                a_i = r * (factor * self._masses[j].mass)
                a_j = r * (-factor * self._masses[i].mass)

                acc[i] += a_i
                acc[j] += a_j

        return acc

    def _merge_all_masses(self) -> None:
        while self._merge_masses():
            pass

    def _merge_masses(self) -> bool:
        n = len(self._masses)

        for i in range(n):
            for j in range(i + 1, n):
                r = self._masses[j].pos - self._masses[i].pos
                if r.length_squared() <= self._merge_distance_squared:
                    self._do_merge_masses(i, j)
                    return True
        return False

    def _do_merge_masses(self, i: int, j: int) -> None:
        pi = self._masses[i]
        pj = self._masses[j]

        p_new = PointMass(
            (pi.mass * pi.pos + pj.mass * pj.pos) / (pi.mass + pj.mass),
            (pi.mass * pi.vel + pj.mass * pj.vel) / (pi.mass + pj.mass),
            pi.mass + pj.mass,
        )

        self._masses[i] = p_new
        del self._masses[j]

    def __iter__(self) -> Iterator[PointMass]:
        return iter(self._masses)

class InspectorUIControlState:
    def __init__(self, inspector: "InspectorUIState", label: str, attr_name: str) -> None:
        self.label = label
        self._inspector = inspector
        self._attr_name = attr_name

    def get(self) -> float:
        p = self._inspector.get_selected_point()
        if p is None:
            return 0.0
        return getattr(p, self._attr_name, 0.0)

    def set(self, v: float):
        p = self._inspector.get_selected_point()
        if p is None:
            return
        return setattr(p, self._attr_name, v)

class InspectorUIState:
    def __init__(self) -> None:
        self.controls = [
            InspectorUIControlState(self, "X Pos", 'x'),
            InspectorUIControlState(self, "Y Pos", 'y'),
            InspectorUIControlState(self, "X Vel", 'vx'),
            InspectorUIControlState(self, "Y Vel", 'vy'),
            InspectorUIControlState(self, "Mass", 'mass'),
        ]
        self._selected_point_mass: Optional[PointMass] = None
        self._current_idx = 0
        self._typing = ""

    def reset(self) -> None:
        self._selected_point_mass = None
        self._current_idx = 0
        self._typing = ""

    def get_selected_point(self) -> Optional[PointMass]:
        return self._selected_point_mass

    def set_selected_point(self, point: PointMass) -> None:
        self._selected_point_mass = point

    def unselect_point(self) -> None:
        self._selected_point_mass = None

    def get_current_idx(self) -> int:
        return self._current_idx

    def cycle_forward(self) -> None:
        self._current_idx += 1
        self._current_idx %= len(self.controls)

    def cycle_backward(self) -> None:
        self._current_idx -= 1
        self._current_idx %= len(self.controls)

    def type_input(self, char: str) -> None:
        self._typing += char

    def type_backspace(self) -> None:
        if self._typing:
            self._typing = self._typing[:-1]

    def get_typing_input(self) -> str:
        return self._typing

    def try_commit(self) -> None:
        try:
            val = float(self._typing)
        except ValueError:
            logger.info(f"failed to parse '{self._typing}' as float")
            return

        self.controls[self._current_idx].set(val)
        self._typing = ""



class Camera:
    def __init__(self, layout: Layout, world_center: Optional[pygame.Vector2] = None, zoom: Optional[float] = None) -> None:
        self._layout = layout

        self._world_center = pygame.Vector2(0, 0)
        if world_center is not None:
            self._world_center = world_center

        self._zoom = 1.0
        if zoom is not None:
            self._zoom = zoom

    def world_to_screen(self, world_pos: pygame.Vector2) -> pygame.Vector2:
        return (world_pos - self._world_center) * self._zoom + self._layout.get_viewport_center()

    def screen_to_world(self, screen_pos: pygame.Vector2) -> pygame.Vector2:
        return (screen_pos - self._layout.get_viewport_center()) / self._zoom + self._world_center

    def pan(self, direction: pygame.Vector2, dt: float) -> None:
        self._world_center += direction * dt * CAMERA_PAN_SPEED

    def set_world_center(self, world_center: pygame.Vector2):
        self._world_center = world_center

    def zoom(self, direction: int, dt: float) -> None:
        self._zoom *= ZOOM_FACTOR ** (float(direction) * dt)


class CameraFollowMode(Enum):
    NONE = auto()
    SELECTED_POINT_MASS = auto()
    CENTER_OF_MASS = auto()

class CameraController:
    def __init__(self):
        self._pan_direction_x = 0
        self._pan_direction_y = 0
        self._zoom_direction = 0
        self._follow_mode = CameraFollowMode.NONE

    def set_pan_direction_left(self):
        self._pan_direction_x -= 1

    def reset_pan_direction_left(self):
        if self._pan_direction_x < 0:
            self._pan_direction_x = 0

    def set_pan_direction_right(self):
        self._pan_direction_x += 1

    def reset_pan_direction_right(self):
        if self._pan_direction_x > 0:
            self._pan_direction_x = 0

    def set_pan_direction_up(self):
        self._pan_direction_y -= 1

    def reset_pan_direction_up(self):
        if self._pan_direction_y < 0:
            self._pan_direction_y = 0

    def set_pan_direction_down(self):
        self._pan_direction_y += 1

    def reset_pan_direction_down(self):
        if self._pan_direction_y > 0:
            self._pan_direction_y = 0

    def set_zoom_direction_in(self):
        self._zoom_direction = 1

    def set_zoom_direction_out(self):
        self._zoom_direction = -1

    def reset_zoom_direction(self):
        self._zoom_direction = 0

    def set_follow_mode_selected_mass(self):
        self._follow_mode = CameraFollowMode.SELECTED_POINT_MASS

    def set_follow_mode_center_of_mass(self):
        self._follow_mode = CameraFollowMode.CENTER_OF_MASS

    def unset_follow_mode(self):
        self._follow_mode = CameraFollowMode.NONE

    def is_follow_mode_set(self):
        return self._follow_mode != CameraFollowMode.NONE

    def is_follow_selected_mass_mode(self) -> bool:
        return self._follow_mode == CameraFollowMode.SELECTED_POINT_MASS

    def is_follow_center_of_mass_mode(self) -> bool:
        return self._follow_mode == CameraFollowMode.CENTER_OF_MASS

    def update(self, selected: Optional[PointMass], camera: Camera, points: PointMassSimulator, dt: float) -> None:
        if not self.is_follow_mode_set():
            if self._pan_direction_x or self._pan_direction_y:
                camera_dir = pygame.Vector2(self._pan_direction_x, self._pan_direction_y)
                camera_dir = camera_dir.normalize()
                camera.pan(camera_dir, dt)

        if self._zoom_direction:
            camera.zoom(self._zoom_direction, dt)

        if self.is_follow_selected_mass_mode():
            if selected is None:
                self._follow_mode = CameraFollowMode.NONE
            else:
                camera.set_world_center(selected.pos.copy())

        if self.is_follow_center_of_mass_mode():
            camera.set_world_center(points.center_of_mass())


class PauseController:
    def __init__(self):
        self._paused = True
        self._paused_timer = 0.0
        self.icon_alpha = 255

    def toggle_paused(self) -> None:
        self._paused = not self._paused

    def is_paused(self) -> bool:
        return self._paused

    def update(self, dt: float) -> None:
        if self.is_paused():
            self._paused_timer += dt;
            alpha = 0.5 * (1 + math.cos(PAUSED_ANIMATION_SPEED * self._paused_timer))
            self.icon_alpha = round(255 * alpha)
        else:
            self._paused_timer = 0


class CursorUIController:
    def __init__(self, layout: Layout, viewport_clickable_margin: int, selection_distance_squared: float):
        self._layout = layout
        self._viewport_clickable_margin = viewport_clickable_margin
        self._selection_distance_squared = selection_distance_squared

    def is_viewport_click_allowed(self, pos: tuple[int, int]):
        rect = self._layout.get_viewport_rect()
        return rect.collidepoint(pos) and pos[0] < rect.right - self._viewport_clickable_margin

    def find_closest_point_screen_space(self, points: Iterator[PointMass], camera: Camera, pos_cursor: tuple[int, int]) -> Optional[PointMass]:
        pos = pygame.Vector2(*pos_cursor)
        best = None
        best_dist = self._selection_distance_squared

        for p in points:
            point = camera.world_to_screen(p.pos)
            d = pos.distance_squared_to(point)
            if d < best_dist:
                best = p
                best_dist = d

        return best

class GameState:
    def __init__(self, points: PointMassSimulator, inspector: InspectorUIState, camera: Camera, camera_controller: CameraController, pause_controller: PauseController, cursor_ui_controller: CursorUIController, physics_timedelta: float):
        self._physics_timedelta = physics_timedelta
        self.points = points
        self.inspector = inspector
        self.camera = camera
        self.camera_controller = camera_controller
        self.pause_controller = pause_controller
        self.cursor_ui_controller = cursor_ui_controller

        self._running = True
        self._physics_loop_accumulator = 0.0

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def update(self, dt: float) -> None:
        self.pause_controller.update(dt)

        if not self.pause_controller.is_paused():
            self._update_physics_loop(dt)

        p = self.inspector.get_selected_point()
        if p is not None:
            idx = self.points.index(p)
            if idx is None:
                self.inspector.unselect_point()

        self.camera_controller.update(p, self.camera, self.points, dt)

    def _update_physics_loop(self, dt: float) -> None:
        # clamp to prevent runaway computation
        if dt > 0.25:
            dt = 0.35

        self._physics_loop_accumulator += dt
        while self._physics_loop_accumulator >= self._physics_timedelta:
            self.points.update(self._physics_timedelta)
            self._physics_loop_accumulator -= self._physics_timedelta


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
            p = self._game.cursor_ui_controller.find_closest_point_screen_space(self._game.points, self._game.camera, event.pos)
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

class Renderer:
    def __init__(self, layout: Layout) -> None:
        self._layout = layout
        self._screen = pygame.display.set_mode(layout.get_dimensions())
        self._font = pygame.font.SysFont("notosansmono", 12)

    def render(self, game: GameState) -> None:
        self._clear()
        self._render(game)
        pygame.display.flip()

    def _clear(self) -> None:
        self._screen.fill((0, 0, 0))

    def _render(self, game: GameState) -> None:
        self._render_viewport(game.camera, game.points, game.inspector.get_selected_point())
        self._render_inspector(game.inspector, game.points, game.camera_controller.is_follow_center_of_mass_mode(), game.camera_controller.is_follow_selected_mass_mode())
        self._render_overlay(game.pause_controller)

    def _render_viewport(self, camera: Camera, points: PointMassSimulator, selected_point: Optional[PointMass]) -> None:
        for p in points:
            color = POINT_MASS_RENDER_COLOR
            if selected_point is p:
                color = POINT_MASS_RENDER_SELECTED_COLOR

            screen_space_pos = camera.world_to_screen(p.pos)

            pygame.draw.circle(
                self._screen,
                color,
                (screen_space_pos.x, screen_space_pos.y),
                POINT_MASS_RENDER_RADIUS,
            )

    def _render_inspector(self, inspector: InspectorUIState, points: PointMassSimulator, show_follow_com_mode: bool, show_follow_selection_mode: bool):
        panel = self._layout.get_inspector_panel_rect()

        pygame.draw.rect(
            self._screen,
            INSPECTOR_BG_COLOR,
            panel,
        )

        pygame.draw.line(
            self._screen,
            INSPECTOR_BORDER_COLOR,
            panel.topleft,
            panel.bottomleft,
            1,
        )

        offset_y = 0
        if show_follow_com_mode:
            self._render_text("[ COM ]", panel, offset_y)
        offset_y += INSPECTOR_CONTROL_SEPARATION * 2

        selected_point = inspector.get_selected_point()
        if selected_point is None:
            return

        total = points.get_total()
        curr = points.index(selected_point)
        if curr is not None:
            curr += 1

        index_text = f"{curr} / {total}"
        if show_follow_selection_mode:
            index_text += " [F]"
        self._render_text(index_text, panel, offset_y)
        offset_y += INSPECTOR_CONTROL_SEPARATION * 2

        for i, control in enumerate(inspector.controls):
            text = f"{control.label}: {control.get():.3f}"
            if i == inspector.get_current_idx():
                text += ' ◀ '
                text += inspector.get_typing_input()

            self._render_text(text, panel, offset_y)
            offset_y += INSPECTOR_CONTROL_SEPARATION


    def _render_text(self, text: str, panel: pygame.Rect, y_offset: int):
        x = panel.x + INSPECTOR_PADDING_X
        y = panel.y + INSPECTOR_PADDING_Y + y_offset
        text_surface = self._font.render(text, True, INSPECTOR_TEXT_COLOR)
        text_rect = text_surface.get_rect(topleft=(x, y))
        self._screen.blit(text_surface, text_rect)

    def _render_overlay(self, pause_controller: PauseController) -> None:
        if pause_controller.is_paused():
            self._render_paused_icon(pause_controller.icon_alpha)

    def _render_paused_icon(self, alpha: int) -> None:
        icon_surface = pygame.Surface(
            (PAUSE_ICON_WIDTH, PAUSE_ICON_HEIGHT),
            pygame.SRCALPHA
        )
        color = (*PAUSE_ICON_COLOR, alpha)

        pygame.draw.rect(
            icon_surface,
            color,
            (0, 0, PAUSE_ICON_BAR_WIDTH, PAUSE_ICON_HEIGHT),
        )

        pygame.draw.rect(
            icon_surface,
            color,
            (PAUSE_ICON_BAR_WIDTH + PAUSE_ICON_GAP, 0, PAUSE_ICON_BAR_WIDTH, PAUSE_ICON_HEIGHT),
        )

        rect = icon_surface.get_rect(center=self._layout.get_pause_icon_center_location())
        self._screen.blit(icon_surface, rect);



def main() -> int:
    logging.basicConfig(level=logging.INFO)

    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("Gravity")

    clock = pygame.time.Clock()

    layout = Layout(
        height=500,
        viewport_width=500,
        inspector_width=200,
        pause_icon_offset=(0,0),
        pause_icon_dimensions=(100,100)
    )
    points = PointMassSimulator(
        gravitational_constant=500.0,
        softening_factor=1.0,
        merge_distance_squared=0.75,
    )
    inspector = InspectorUIState()
    camera = Camera(layout)
    camera_controller = CameraController()
    pause_controller = PauseController()
    cursor_ui_controller = CursorUIController(
        layout=layout,
        viewport_clickable_margin=5,
        selection_distance_squared=20,
    )
    game = GameState(
        points=points,
        inspector=inspector,
        camera=camera,
        camera_controller=camera_controller,
        pause_controller=pause_controller,
        cursor_ui_controller=cursor_ui_controller,
        physics_timedelta=1/500,
    )
    events = EventHandler(game, layout)
    renderer = Renderer(layout)

    #initialize with a bunch of point masses
    import random
    w = 300
    h = 300
    for i in range(50):
        game.points.create(
            pygame.Vector2(
                random.uniform(-w//2, w//2),
                random.uniform(-h//2, h//2),
            ),
            abs(random.gauss(mu=0, sigma=1)),
        )

    while game.is_running():
        dt = clock.get_time() / 1000.0
        events.handle_events()
        game.update(dt)
        renderer.render(game)
        clock.tick(60)

    pygame.quit()
    logging.shutdown()
    return 0


if __name__ == "__main__":
    exit(main())
