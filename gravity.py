from typing_extensions import Optional
import pygame
import logging
from typing import Iterable, Iterator
from dataclasses import dataclass
import math

WIDTH = 700
HEIGHT = 500

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
INSPECTOR_PADDING_X = 50
INSPECTOR_PADDING_Y = 50
INSPECTOR_CONTROL_SEPARATION = 30

POINT_MASS_RENDER_COLOR = (255, 255, 255)
POINT_MASS_RENDER_SELECTED_COLOR = (255, 0, 0)
POINT_MASS_RENDER_RADIUS = 4
SELECTION_DISTANCE_SQUARED = 20

LEFT_MOUSE_BUTTON = 1
RIGHT_MOUSE_BUTTON = 3

logger = logging.getLogger(__name__)

@dataclass
class PointMass:
    x: float
    y: float
    mass: float


class PointMassDirector(Iterable[PointMass]):
    def __init__(self) -> None:
        self._masses: list[PointMass] = []

    def create(self, x: float, y: float) -> PointMass:
        p = PointMass(x, y, 1.0)
        self._masses.append(p)
        return p

    def delete(self, p: PointMass):
        for i, pp in enumerate(self._masses):
            if pp is p:
                del self._masses[i]
                return

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
        self._selected_point_mass: Optional[PointMass] = None
        self.controls = [
            InspectorUIControlState(self, "X Coord", 'x'),
            InspectorUIControlState(self, "Y Coord", 'y'),
            InspectorUIControlState(self, "Mass", 'mass'),
        ]
        self._current_idx = 0

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

class GameState:
    def __init__(self):
        self._running = True

        self._paused = True
        self._paused_timer = 0.0
        self.paused_alpha = 255

        self.points = PointMassDirector()
        self.inspector = InspectorUIState()

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
        self.font = pygame.font.Font(None, 24)
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
        self._render_point_masses(game.points, game.inspector)
        self._render_inspector_panel(game.inspector)
        if game.is_paused():
            self._render_paused_icon(game.paused_alpha, (50, 50))

    def _render_point_masses(self, points: Iterable[PointMass], inspector: InspectorUIState) -> None:
        for p in points:
            color = POINT_MASS_RENDER_COLOR
            if inspector.get_selected_point() is p:
                color = POINT_MASS_RENDER_SELECTED_COLOR

            pygame.draw.circle(
                self.screen,
                color,
                (p.x, p.y),
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

    def _render_inspector_panel(self, inspector: InspectorUIState):
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

        if inspector.get_selected_point() is None:
            return

        offset_y = 0
        for i, control in enumerate(inspector.controls):
            text = f"{control.label}: {control.get()}"

            if i == inspector.get_current_idx():
                text += ' ← '

            text_surface = self.font.render(
                text,
                True,
                INSPECTOR_TEXT_COLOR,
            )

            text_rect = text_surface.get_rect(
                topleft=(
                    self.inspector_panel_rect.x + INSPECTOR_PADDING_X,
                    self.inspector_panel_rect.y + INSPECTOR_PADDING_Y + offset_y,
                )
            )

            offset_y += INSPECTOR_CONTROL_SEPARATION

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
