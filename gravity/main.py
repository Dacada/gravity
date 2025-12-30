import logging
import pygame

from gravity.ui.layout import Layout, LayoutIcon, AnchorType
from gravity.ui import InspectorUIState, PauseController, CursorUIController
from gravity.physics import PointMassSimulator
from gravity.camera import Camera, CameraController
from gravity.core import GameState, EventHandler
from gravity.render.styles import (
    PauseIconStyle,
    TargetIconStyle,
    CenterOfMassRingIconStyle,
    InspectorStyle,
    PointMassStyle,
    RenderStyle,
)
from gravity.render import Renderer


def main() -> int:
    logging.basicConfig(level=logging.INFO)

    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("Gravity")

    clock = pygame.time.Clock()

    pause_icon_layout = LayoutIcon(
        offset_ratio=(1 / 20, 1 / 20),
        size=(40, 50),
        anchor=AnchorType.TOP_LEFT,
    )
    camera_state_icon_layout = LayoutIcon(
        offset_ratio=(1 / 50, 49 / 50),
        size=(50, 50),
        anchor=AnchorType.BOTTOM_LEFT,
    )
    layout = Layout(
        width=700,
        height=500,
        inspector_ratio=2 / 7,
        pause_icon=pause_icon_layout,
        camera_state_icon=camera_state_icon_layout,
    )
    points = PointMassSimulator(
        gravitational_constant=500.0,
        softening_factor=1.0,
        merge_distance_squared=0.75,
    )
    inspector = InspectorUIState()
    camera = Camera(
        layout=layout,
        pan_speed=100.0,
        zoom_factor=1.5,
    )
    camera_controller = CameraController()
    pause_controller = PauseController(
        animation_speed=2.5,
    )
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
        physics_timedelta=1 / 500,
    )
    events = EventHandler(
        game=game,
        layout=layout,
    )
    pause_icon_style = PauseIconStyle(
        color=(255, 255, 255),
        bar_width=10,
        bar_height=50,
        gap=8,
    )
    target_icon_style = TargetIconStyle(
        color=(255, 255, 255),
        size=48,
        center_radius=6,
        corner_length=14,
        corner_thickness=3,
    )
    com_icon_style = CenterOfMassRingIconStyle(
        color=(255, 255, 255),
        center_radius=12,
        center_thickness=3,
        dot_radius=3,
        dot_distance=20,
        dot_count=6,
    )
    inspector_style = InspectorStyle(
        bg_color=(30, 30, 30),
        border_color=(80, 80, 80),
        text_color=(255, 255, 255),
        padding=(20, 50),
        control_separation=15,
    )
    point_mass_style = PointMassStyle(
        color=(255, 255, 255),
        selected_color=(255, 0, 0),
        radius=4,
    )
    render_style = RenderStyle(
        pause_icon=pause_icon_style,
        target_icon=target_icon_style,
        com_icon=com_icon_style,
        inspector=inspector_style,
        point_mass=point_mass_style,
    )
    renderer = Renderer(
        layout=layout,
        style=render_style,
    )

    # initialize with a bunch of point masses
    import random

    w = 300
    h = 300
    for i in range(50):
        game.points.create(
            pygame.Vector2(
                random.uniform(-w // 2, w // 2),
                random.uniform(-h // 2, h // 2),
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
