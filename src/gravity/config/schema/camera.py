from pydantic import BaseModel


class Camera(BaseModel):
    pan_speed: float
    zoom_factor: float
