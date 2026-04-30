from dataclasses import dataclass, field
from typing import List

@dataclass
class Plant:
    x: float
    y: float
    canopy_r: float = 0.26
    canopy_z: float = 0.58
    stem_r: float = 0.04
    stem_h: float = 0.32
    cr: float = 0.11
    cg: float = 0.50
    cb: float = 0.08


@dataclass
class Box:
    name: str
    x: float; y: float; z: float
    sx: float; sy: float; sz: float
    r: float = 0.55; g: float = 0.33; b: float = 0.10


@dataclass
class World:
    name: str
    robot_x: float = -0.5
    robot_y: float = 0.0
    ambient: tuple = (0.65, 0.65, 0.65, 1.0)
    sun_dir: tuple = (-0.5, 0.1, -0.9)
    fog_density: float = 0.0
    fog_start: float = 1.5
    fog_end: float = 14.0
    plants: List[Plant] = field(default_factory=list)
    boxes: List[Box] = field(default_factory=list)
    lights: List[str] = field(default_factory=list)
