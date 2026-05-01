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

            # Blueberry bush — low, wide shrub proportions
            canopy_z = float(np.clip((0.14 + rng.uniform(0, 0.10)) * sc + 0.10, 0.18, 0.45))
            stem_h   = float(np.clip(0.10 * sc + rng.uniform(-0.02, 0.04), 0.06, 0.22))   # crown height
            stem_r   = float(np.clip(0.09 + rng.uniform(-0.02, 0.02), 0.05, 0.14))        # crown radius (wider)

            # Dark blue-green blueberry foliage
            cv  = rng.uniform(-colour_var, colour_var)
            cr  = float(np.clip(0.07 + cv * 0.25, 0.03, 0.14))
            cg  = float(np.clip(0.30 + cv * 0.28, 0.16, 0.44))
            cb  = float(np.clip(0.14 + cv * 0.18, 0.06, 0.24))

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


def add_terrain_tile(
    world: World,
    x_center: float,
    y_center: float,
    x_length: float,
    y_width: float,
    r: float, g: float, b: float,
    name: str = None,
):
    """Flat coloured ground patch to visually differentiate corridor terrain."""
    nm = name or f"terrain_{len(world.boxes)}"
    world.boxes.append(Box(
        name=nm,
        x=x_center, y=y_center, z=0.005,
        sx=x_length, sy=y_width, sz=0.01,
        r=r, g=g, b=b,
    ))


def add_end_posts(world: World, x: float, y_pairs: list):
    for i, (y0, y1) in enumerate(y_pairs):
        world.boxes.append(Box(
            name=f"end_post_{i}",
            x=x, y=(y0+y1)/2, z=0.50,
            sx=0.10, sy=0.10, sz=1.00,
            r=0.90, g=0.45, b=0.00,
        ))


def add_grass_field(
    world: World,
    x_center: float,
    y_center: float,
    x_length: float,
    y_width: float,
    seed: Optional[int] = None,
):
    """Dense field of tiny cylindrical grass tufts inside a single static model."""
    rng = np.random.default_rng(seed)
    nx = max(1, int(x_length / 0.35))
    ny = max(1, int(y_width / 0.25))

    links = []
    idx = 0
    for i in range(nx):
        for j in range(ny):
            px = x_center - x_length / 2 + (i + 0.5) * (x_length / nx)
            py = y_center - y_width / 2 + (j + 0.5) * (y_width / ny)
            px += rng.uniform(-0.06, 0.06)
            py += rng.uniform(-0.06, 0.06)

            # Mostly flat disks, occasional taller tufts
            if rng.random() < 0.75:
                r = rng.uniform(0.035, 0.065)
                h = rng.uniform(0.003, 0.012)
            else:
                r = rng.uniform(0.020, 0.040)
                h = rng.uniform(0.012, 0.030)
            z = h / 2 + 0.0005

            # Green with occasional brown/yellow patches
            if rng.random() < 0.85:
                cr = float(np.clip(0.12 + rng.uniform(-0.04, 0.05), 0.05, 0.25))
                cg = float(np.clip(0.35 + rng.uniform(-0.08, 0.10), 0.18, 0.55))
                cb = float(np.clip(0.06 + rng.uniform(-0.02, 0.03), 0.02, 0.14))
            else:
                cr = float(np.clip(0.22 + rng.uniform(-0.05, 0.05), 0.12, 0.32))
                cg = float(np.clip(0.28 + rng.uniform(-0.06, 0.06), 0.15, 0.38))
                cb = float(np.clip(0.05 + rng.uniform(-0.02, 0.02), 0.02, 0.10))

            link_lines = [
                f'  <link name="patch_{idx}">',
                f'    <pose>{px:.3f} {py:.3f} {z:.4f} 0 0 0</pose>',
                '    <collision name="c">',
                '      <geometry>',
                f'        <cylinder><radius>{r:.3f}</radius><length>{h:.4f}</length></cylinder>',
                '      </geometry>',
                '    </collision>',
                '    <visual name="v">',
                '      <geometry>',
                f'        <cylinder><radius>{r:.3f}</radius><length>{h:.4f}</length></cylinder>',
                '      </geometry>',
                '      <material>',
                f'        <ambient>{cr:.3f} {cg:.3f} {cb:.3f} 1</ambient>',
                f'        <diffuse>{cr:.3f} {cg:.3f} {cb:.3f} 1</diffuse>',
                '      </material>',
                '    </visual>',
                '  </link>',
            ]
            links.append("\n".join(link_lines))
            idx += 1

    model_name = f"grassfield_{len(world.decorations)}"
    world.decorations.append(
        f'<model name="{model_name}">\n  <static>true</static>\n'
        + "\n".join(links)
        + "\n</model>"
    )


def add_loose_gravel(
    world: World,
    x_center: float,
    y_center: float,
    x_length: float,
    y_width: float,
    n_stones: int = 90,
    seed: Optional[int] = None,
):
    """Scattered small spherical stones inside a single static model."""
    rng = np.random.default_rng(seed)

    links = []
    for i in range(n_stones):
        px = rng.uniform(x_center - x_length / 2, x_center + x_length / 2)
        py = rng.uniform(y_center - y_width / 2, y_center + y_width / 2)

        r = rng.uniform(0.012, 0.032)
        z = r + 0.0005

        base = rng.uniform(0.38, 0.52)
        cr = float(np.clip(base + rng.uniform(-0.06, 0.06), 0.22, 0.62))
        cg = float(np.clip(base - 0.05 + rng.uniform(-0.06, 0.06), 0.18, 0.58))
        cb = float(np.clip(base - 0.10 + rng.uniform(-0.06, 0.06), 0.12, 0.52))

        link_lines = [
            f'  <link name="stone_{i}">',
            f'    <pose>{px:.3f} {py:.3f} {z:.4f} 0 0 0</pose>',
            '    <collision name="c">',
            '      <geometry>',
            f'        <sphere><radius>{r:.3f}</radius></sphere>',
            '      </geometry>',
            '    </collision>',
            '    <visual name="v">',
            '      <geometry>',
            f'        <sphere><radius>{r:.3f}</radius></sphere>',
            '      </geometry>',
            '      <material>',
            f'        <ambient>{cr:.3f} {cg:.3f} {cb:.3f} 1</ambient>',
            f'        <diffuse>{cr:.3f} {cg:.3f} {cb:.3f} 1</diffuse>',
            '      </material>',
            '    </visual>',
            '  </link>',
        ]
        links.append("\n".join(link_lines))

    model_name = f"gravel_{len(world.decorations)}"
    world.decorations.append(
        f'<model name="{model_name}">\n  <static>true</static>\n'
        + "\n".join(links)
        + "\n</model>"
    )


def add_row_light(world, name, x, y, z, r, g, b, intensity=1.0, spot=True):
    """Append a raw SDF light string to world.lights (list of str)."""
    if spot:
        sdf = f"""    <light name="{name}" type="spot">
      <pose>{x:.2f} {y:.2f} {z:.2f} 0 1.5708 0</pose>
      <diffuse>{r*intensity:.3f} {g*intensity:.3f} {b*intensity:.3f} 1</diffuse>
      <specular>0.05 0.05 0.05 1</specular>
      <attenuation><range>12</range><constant>0.4</constant><linear>0.01</linear><quadratic>0.002</quadratic></attenuation>
      <direction>0 0 -1</direction>
      <spot><inner_angle>0.9</inner_angle><outer_angle>1.3</outer_angle><falloff>1.5</falloff></spot>
      <cast_shadows>false</cast_shadows>
    </light>"""
    else:
        sdf = f"""    <light name="{name}" type="point">
      <pose>{x:.2f} {y:.2f} {z:.2f} 0 0 0</pose>
      <diffuse>{r*intensity:.3f} {g*intensity:.3f} {b*intensity:.3f} 1</diffuse>
      <specular>0.05 0.05 0.05 1</specular>
      <attenuation><range>8</range><constant>0.5</constant><linear>0.02</linear><quadratic>0.003</quadratic></attenuation>
      <cast_shadows>false</cast_shadows>
    </light>"""
    world.lights.append(sdf)
