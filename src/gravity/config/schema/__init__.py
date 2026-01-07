from pydantic import BaseModel

from gravity.config.schema import (
    camera,
    core,
    initial_conditions,
    layout,
    render,
    render_styles,
    simulation,
    ui,
)


class AppConfig(BaseModel):
    core: core.Core
    layout: layout.Layout
    simulation: simulation.Simulation
    ui: ui.Ui
    camera: camera.Camera
    render: render.Render


__all__ = [
    "AppConfig",
    "camera",
    "core",
    "initial_conditions",
    "layout",
    "render",
    "render_styles",
    "simulation",
    "ui",
]
