import pygame
import logging
from typing import Iterable, Iterator, Optional, SupportsFloat
from dataclasses import dataclass
import math

WIDTH = 700
HEIGHT = 500

GRAVITATIONAL_CONSTANT = 500
SOFTENING_FACTOR = 1
MASS_MERGE_DISTANCE_SQUARED = 0.5

PAUSE_ICON_WIDTH = 40
PAUSE_ICON_HEIGHT = 50
PAUSE_ICON_COLOR = (255, 255, 255)
PAUSE_ICON_BAR_WIDTH = 10
PAUSE_ICON_GAP = 8
PAUSED_ANIMATION_SPEED = 2.5

INSPECTOR_MARGIN_FOR_POINT_CREATION = 5
INSPECTOR_WIDTH = 200
INSPECTOR_BG_COLOR = (30, 30, 30)
INSPECTOR_BORDER_COLOR = (80, 80, 80)
INSPECTOR_TEXT_COLOR = (255, 255, 255)
INSPECTOR_PADDING_X = 20
INSPECTOR_PADDING_Y = 50
INSPECTOR_CONTROL_SEPARATION = 15

POINT_MASS_RENDER_COLOR = (255, 255, 255)
POINT_MASS_RENDER_SELECTED_COLOR = (255, 0, 0)
POINT_MASS_RENDER_RADIUS = 4
SELECTION_DISTANCE_SQUARED = 20

LEFT_MOUSE_BUTTON = 1
RIGHT_MOUSE_BUTTON = 3

logger = logging.getLogger(__name__)

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

    def update(self, dt: float):
        self.pos += self.vel * dt


class PointMassDirector(Iterable[PointMass]):
    def __init__(self) -> None:
        self._masses: list[PointMass] = []

    def create(self, x: SupportsFloat, y: SupportsFloat, mass: float = 1.0) -> PointMass:
        p = PointMass(
            pygame.Vector2(float(x), float(y)),
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

    def get_point_for_selection(self, x: float, y: float) -> Optional[PointMass]:
        best = None
        best_dist = SELECTION_DISTANCE_SQUARED + 1.0
        for p in self._masses:
            d = (p.x - x)**2 + (p.y - y)**2
            if d > SELECTION_DISTANCE_SQUARED:
                continue
            if d < best_dist:
                best = p
                best_dist = d
        return best

    def update(self, dt: float) -> None:
        self._merge_all_masses()

        n = len(self._masses)

        acc = [pygame.Vector2(0.0, 0.0) for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                r = self._masses[j].pos - self._masses[i].pos
                dist_sq = r.length_squared() + SOFTENING_FACTOR
                inv_dist = 1.0 / dist_sq**0.5

                factor = GRAVITATIONAL_CONSTANT * inv_dist / dist_sq

                a_i = r * (factor * self._masses[j].mass)
                a_j = r * (-factor * self._masses[i].mass)

                acc[i] += a_i
                acc[j] += a_j

        for i in range(n):
            self._masses[i].vel += acc[i] * dt

        for p in self._masses:
            p.update(dt)

    def _merge_all_masses(self) -> None:
        while self._merge_masses():
            pass

    def _merge_masses(self) -> bool:
        n = len(self._masses)

        for i in range(n):
            for j in range(i + 1, n):
                r = self._masses[j].pos - self._masses[i].pos
                if r.length_squared() <= MASS_MERGE_DISTANCE_SQUARED:
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
    def __init__(self) -> None:
        self._screen_center = pygame.Vector2((WIDTH - INSPECTOR_WIDTH) / 2, HEIGHT / 2)
        self._world_center = pygame.Vector2(0, 0)
        self._zoom = 1

    def world_to_screen(self, world_pos: pygame.Vector2) -> pygame.Vector2:
        return (world_pos - self._world_center) * self._zoom + self._screen_center

    def screen_to_world(self, screen_pos: pygame.Vector2) -> pygame.Vector2:
        return (screen_pos - self._screen_center) / self._zoom + self._world_center


class GameState:
    def __init__(self):
        self._running = True

        self._paused = True
        self._paused_timer = 0.0
        self.paused_alpha = 255

        self.points = PointMassDirector()
        self.inspector = InspectorUIState()
        self.camera = Camera()

    def stop(self) -> None:
        self._running = False

    def toggle_paused(self) -> None:
        self._paused = not self._paused

    def is_running(self) -> bool:
        return self._running

    def is_paused(self) -> bool:
        return self._paused

    def update(self, dt: float) -> None:
        if self.is_paused():
            self._paused_timer += dt;
            alpha = 0.5 * (1 + math.cos(PAUSED_ANIMATION_SPEED * self._paused_timer))
            self.paused_alpha = round(255 * alpha)
        else:
            self._paused_timer = 0

        if not self.is_paused():
            self.points.update(dt)

        p = self.inspector.get_selected_point()
        if p is not None:
            idx = self.points.index(p)
            if idx is None:
                self.inspector.unselect_point()


class EventHandler:
    def __init__(self, game: GameState) -> None:
        self.game = game

    def on_Quit(self, event: pygame.event.Event) -> None:
        logger.info("received quit event")
        self.game.stop()

    def on_MouseButtonDown(self, event: pygame.event.Event) -> None:
        if event.button == LEFT_MOUSE_BUTTON:
            if event.pos[0] < WIDTH - INSPECTOR_WIDTH - INSPECTOR_MARGIN_FOR_POINT_CREATION:
                self.game.points.create(*event.pos)
        elif event.button == RIGHT_MOUSE_BUTTON:
            p = self.game.points.get_point_for_selection(*event.pos)
            if p is None:
                self.game.inspector.unselect_point()
            else:
                self.game.inspector.set_selected_point(p)

    def on_KeyDown(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_SPACE:
            self.game.toggle_paused()
        elif event.key == pygame.K_DELETE:
            p = self.game.inspector.get_selected_point()
            if p is not None:
                self.game.inspector.unselect_point()
                self.game.points.delete(p)
        elif event.key == pygame.K_TAB:
            if event.mod & pygame.KMOD_SHIFT:
                self.game.inspector.cycle_backward()
            else:
                self.game.inspector.cycle_forward()
        elif event.key == pygame.K_BACKSPACE:
            self.game.inspector.type_backspace()
        elif event.key == pygame.K_ESCAPE:
            self.game.inspector.reset()
        elif event.key == pygame.K_RETURN:
            self.game.inspector.try_commit()
        elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
            if event.key == pygame.K_LEFT:
                inc = -1
            else:
                inc = 1
            p = self.game.inspector.get_selected_point()
            if p is not None:
                idx = self.game.points.index(p)
                if idx is not None:
                    q = self.game.points.by_index(idx + inc)
                    if q is not None:
                        self.game.inspector.set_selected_point(q)
            else:
                p = self.game.points.by_index(0)
                if p is not None:
                    self.game.inspector.set_selected_point(p)
        else:
            char = event.unicode
            if char and self.game.inspector.get_selected_point() is not None:
                self.game.inspector.type_input(char)

    def handle_events(self) -> None:
        for event in pygame.event.get():
            event_name = pygame.event.event_name(event.type)
            name_for_log_msg = f"{event_name} ({event.type})"

            logger.debug(f"process event: {name_for_log_msg}")
            callback = getattr(self, f"on_{event_name}", None)
            if callback is not None:
                callback(event)

class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.SysFont("notosansmono", 12)
        self.inspector_panel_rect = pygame.Rect(
            WIDTH - INSPECTOR_WIDTH,
            0,
            INSPECTOR_WIDTH,
            HEIGHT,
        )

    def render(self, game: GameState) -> None:
        self._clear()
        self._render(game)
        pygame.display.flip()

    def _clear(self) -> None:
        self.screen.fill((0, 0, 0))

    def _render(self, game: GameState) -> None:
        self._render_point_masses(game.points, game.inspector, game.camera)
        self._render_inspector_panel(game.inspector, game.points)
        if game.is_paused():
            self._render_paused_icon(game.paused_alpha, (50, 50))

    def _render_point_masses(self, points: Iterable[PointMass], inspector: InspectorUIState, camera: Camera) -> None:
        for p in points:
            color = POINT_MASS_RENDER_COLOR
            if inspector.get_selected_point() is p:
                color = POINT_MASS_RENDER_SELECTED_COLOR

            screen_space_pos = camera.world_to_screen(p.pos)

            pygame.draw.circle(
                self.screen,
                color,
                (screen_space_pos.x, screen_space_pos.y),
                POINT_MASS_RENDER_RADIUS,
            )

    def _render_paused_icon(self, alpha: int, center: tuple[int, int]) -> None:
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

        rect = icon_surface.get_rect(center=center)
        self.screen.blit(icon_surface, rect);

    def _render_inspector_panel(self, inspector: InspectorUIState, points: PointMassDirector):
        pygame.draw.rect(
            self.screen,
            INSPECTOR_BG_COLOR,
            self.inspector_panel_rect,
        )

        pygame.draw.line(
            self.screen,
            INSPECTOR_BORDER_COLOR,
            self.inspector_panel_rect.topleft,
            self.inspector_panel_rect.bottomleft,
            1,
        )

        selected_point = inspector.get_selected_point()
        if selected_point is None:
            return

        total = points.get_total()
        curr = points.index(selected_point)
        if curr is not None:
            curr += 1

        self._render_text(
            f"{curr} / {total}",
            self.inspector_panel_rect.x + INSPECTOR_PADDING_X,
            self.inspector_panel_rect.y + INSPECTOR_PADDING_Y,
            INSPECTOR_TEXT_COLOR,
        )

        offset_y = INSPECTOR_CONTROL_SEPARATION * 2
        for i, control in enumerate(inspector.controls):
            text = f"{control.label}: {control.get():.3f}"
            if i == inspector.get_current_idx():
                text += ' ◀ '
                text += inspector.get_typing_input()

            self._render_text(
                text,
                self.inspector_panel_rect.x + INSPECTOR_PADDING_X,
                self.inspector_panel_rect.y + INSPECTOR_PADDING_Y + offset_y,
                INSPECTOR_TEXT_COLOR,
            )

            offset_y += INSPECTOR_CONTROL_SEPARATION


    def _render_text(self, text: str, x: int, y: int, color: tuple[int, int, int]):
        text_surface = self.font.render(text, True, color)
        text_rect = text_surface.get_rect(topleft=(x, y))
        self.screen.blit(text_surface, text_rect)



def main() -> int:
    logging.basicConfig(level=logging.INFO)

    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Gravity")
    clock = pygame.time.Clock()

    game = GameState()
    events = EventHandler(game)
    renderer = Renderer(screen)

    #initialize with a bunch of point masses
    import random
    w = (WIDTH - INSPECTOR_WIDTH)//2
    h = HEIGHT//2
    for i in range(25):
        game.points.create(
            random.randint(0, w) + w//2,
            random.randint(0, h) + h//2,
            abs(random.gauss()),
        )

    while game.is_running():
        dt = clock.get_time() / 1000.0
        events.handle_events()
        renderer.render(game)
        game.update(dt)
        clock.tick(60)

    pygame.quit()
    logging.shutdown()
    return 0


if __name__ == "__main__":
    exit(main())
