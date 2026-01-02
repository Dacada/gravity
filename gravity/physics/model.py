from dataclasses import dataclass
from typing import Optional

import pygame

from gravity.types import Color


@dataclass
class SimulatedEntity:
    pos: pygame.Vector2
    color: Color
    name: Optional[str]
    index: int
