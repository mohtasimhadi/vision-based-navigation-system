import numpy as np
from typing import List, Optional
from utils.data_classes import World, Plant, Box

def add_natural_row(
    world:            World,
    y_center:         float,
    length:           float = 9.0,
    spacing:          float = 0.55,
    y_jitter:         float = 0.05,
    x_jitter:         float = 0.03,
    size_var:         float = 0.15,
    curve_amp:        float = 0.06,
    curve_period:     float = 7.0,
    colour_var:       float = 0.08,
    canopy_r_base:    float = 0.20,
    skip:             Optional[List[int]] = None,
    seed:             Optional[int]       = None,
):
    rng      = np.random.default_rng(seed)
    skip_set = set(skip or [])

    x_pos = 0.0
    i = 0
    while x_pos < length:
        if i not in skip_set:
            y_curve = y_center + curve_amp * np.sin(2 * np.pi * x_pos / curve_period)

            px = x_pos + rng.normal(0, x_jitter)
            py = y_curve + rng.normal(0, y_jitter)

            sc = float(np.clip(1.0 + rng.normal(0, size_var), 0.65, 1.45))

            canopy_r = canopy_r_base * sc
            canopy_z = (0.32 + rng.uniform(0, 0.18)) * sc + 0.22
            stem_h   = float(np.clip(0.28 * sc + rng.uniform(-0.05, 0.08), 0.15, 0.55))
            stem_r   = float(np.clip(0.04 + rng.uniform(-0.01, 0.01), 0.02, 0.07))

            cv  = rng.uniform(-colour_var, colour_var)
            cr  = float(np.clip(0.11 + cv * 0.4,  0.05, 0.25))
            cg  = float(np.clip(0.50 + cv * 0.3,  0.30, 0.68))
            cb  = float(np.clip(0.08 - cv * 0.05, 0.03, 0.15))

            world.plants.append(Plant(
                x=px, y=py,
                canopy_r=round(canopy_r, 3),
                canopy_z=round(canopy_z, 3),
                stem_h=round(stem_h, 3),
                stem_r=round(stem_r, 3),
                cr=round(cr, 3), cg=round(cg, 3), cb=round(cb, 3),
            ))

        x_pos += max(0.30, spacing + rng.normal(0, x_jitter * 0.6))
        i += 1


def add_end_posts(world: World, x: float, y_pairs: list):
    for i, (y0, y1) in enumerate(y_pairs):
        world.boxes.append(Box(
            name=f"end_post_{i}",
            x=x, y=(y0+y1)/2, z=0.50,
            sx=0.10, sy=0.10, sz=1.00,
            r=0.90, g=0.45, b=0.00,
        ))
