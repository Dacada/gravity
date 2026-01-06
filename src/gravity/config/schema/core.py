from pydantic import BaseModel


class Core(BaseModel):
    target_framerate: int
