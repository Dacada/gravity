from typing_extensions import Optional
import pygame
import logging
from typing import Iterable, Iterator
from dataclasses import dataclass
import math

WIDTH = 500
HEIGHT = 500

POINT_MASS_RENDER_COLOR = (255, 255, 255)
POINT_MASS_RENDER_SELECTED_COLOR = (255, 0, 0)
POINT_MASS_RENDER_RADIUS = 4
SELECTION_DISTANCE_SQUARED = 20

LEFT_MOUSE_BUTTON = 1
RIGHT_MOUSE_BUTTON = 3

logger = logging.getLogger(__name__)

@dataclass
class PauseIconDefinition:
    width: int
    height: int
    color: tuple[int, int, int]
    bar_width: int
    gap: int

PAUSED_ANIMATION_SPEED = 2.5
PAUSE_ICON = PauseIconDefinition(
    width=40,
    height=50,
    color=(255, 255, 255),
    bar_width=10,
    gap=8,
)

@dataclass
class PointMass:
    x: float
    y: float
    mass: float


class PointMassDirector(Iterable[PointMass]):
    def __init__(self) -> None:
        self._masses: list[PointMass] = []
        self._selected: Optional[PointMass] = None

    def create(self, x: float, y: float) -> PointMass:
        p = PointMass(x, y, 1.0)
        self._masses.append(p)
        return p

    def select(self, x: float, y: float) -> None:
        best = None
        best_dist = SELECTION_DISTANCE_SQUARED + 1.0
        for p in self._masses:
            d = (p.x - x)**2 + (p.y - y)**2
            if d > SELECTION_DISTANCE_SQUARED:
                continue
            if d < best_dist:
                best = p
                best_dist = d
        self._selected = best

    def is_selected(self, p: PointMass) -> bool:
        return p is self._selected

    def __iter__(self) -> Iterator[PointMass]:
        return iter(self._masses)

class GameState:
    def __init__(self):
        self._running = True

        self._paused = True
        self._paused_timer = 0.0
        self.paused_alpha = 255

        self.points = PointMassDirector()

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
            self.game.points.create(*event.pos)
        elif event.button == RIGHT_MOUSE_BUTTON:
            self.game.points.select(*event.pos)

    def on_KeyDown(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_SPACE:
            self.game.toggle_paused()

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

    def render(self, game: GameState) -> None:
        self._clear()
        self._render(game)
        pygame.display.flip()

    def _clear(self) -> None:
        self.screen.fill((0, 0, 0))

    def _render(self, game: GameState) -> None:
        self._render_point_masses(game.points)
        if game.is_paused():
            self._render_paused_icon(game.paused_alpha, (50, 50), PAUSE_ICON)

    def _render_point_masses(self, points: PointMassDirector) -> None:
        for p in points:
            color = POINT_MASS_RENDER_COLOR
            if points.is_selected(p):
                color = POINT_MASS_RENDER_SELECTED_COLOR

            pygame.draw.circle(
                self.screen,
                color,
                (p.x, p.y),
                POINT_MASS_RENDER_RADIUS,
            )

    def _render_paused_icon(self, alpha: int, center: tuple[int, int], icon: PauseIconDefinition) -> None:
        icon_surface = pygame.Surface(
            (icon.width, icon.height),
            pygame.SRCALPHA
        )
        color = (*icon.color, alpha)

        pygame.draw.rect(
            icon_surface,
            color,
            (0, 0, icon.bar_width, icon.height),
        )

        pygame.draw.rect(
            icon_surface,
            color,
            (icon.bar_width + icon.gap, 0, icon.bar_width, icon.height),
        )

        rect = icon_surface.get_rect(center=center)
        self.screen.blit(icon_surface, rect);



def main() -> int:
    logging.basicConfig(level=logging.INFO)

    pygame.init()
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
