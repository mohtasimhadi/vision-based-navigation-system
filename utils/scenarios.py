from utils.data_classes import World, Box
from utils.generators import (
    add_natural_row, add_terrain_tile, add_row_light, add_end_posts,
    add_grass_field, add_loose_gravel,
)

# ── Field geometry ────────────────────────────────────────────────────────────
ROW_LENGTH = 9.0          # m — all plant rows run from x=0 to x=ROW_LENGTH
X_MID      = ROW_LENGTH / 2.0
ROW_SEP    = 1.30         # m between adjacent row centre-lines

INNER_Y    = 0.65         # inner rows at ±INNER_Y  (define the C1_inner corridor)
OUTER_Y    = 1.95         # outer rows at ±OUTER_Y  (define C2_left / C3_right)

# gap = ROW_SEP - 2 * canopy_r  →  1.30 - 2*0.18 ≈ 0.94 m
# Rover track width ≈ 0.57 m → ~19 cm clearance per side


def _add_corridor_tiles(w: World, brightness: float = 1.0):
    """
    Add a differently-coloured ground tile for each of the three corridors so
    each row visually runs over a distinct terrain type.
    """
    c2_y = -(INNER_Y + OUTER_Y) / 2   # centre of C2_left  corridor
    c3_y =  (INNER_Y + OUTER_Y) / 2   # centre of C3_right corridor

    bf = brightness
    # C2_left  — dry reddish-brown soil
    add_terrain_tile(w, X_MID, c2_y, ROW_LENGTH, ROW_SEP,
                     r=round(0.45 * bf, 3), g=round(0.24 * bf, 3), b=round(0.10 * bf, 3),
                     name="terrain_c2_left")
    # C1_inner — gravel field
    add_terrain_tile(w, X_MID, 0.0, ROW_LENGTH, ROW_SEP,
                     r=round(0.55 * bf, 3), g=round(0.52 * bf, 3), b=round(0.48 * bf, 3),
                     name="terrain_c1_inner")
    # C3_right — dark moist clay
    add_terrain_tile(w, X_MID, c3_y, ROW_LENGTH, ROW_SEP,
                     r=round(0.28 * bf, 3), g=round(0.16 * bf, 3), b=round(0.07 * bf, 3),
                     name="terrain_c3_right")


# Uniform row spacing: 1.3 m between every adjacent row
# Inner corridor = 1.3 m  (rows at +/-0.65)
# Outer rows    = +/-1.95


def nominal() -> World:
    w = World(
        name="crop_nominal",
        robot_x=-0.5, robot_y=-1.3,
        ambient=(0.68, 0.68, 0.68, 1.0),
        sun_dir=(-0.5, 0.1, -0.9),
    )
    # C2_left — bumpy grassfield
    add_grass_field(w, X_MID, -(INNER_Y + OUTER_Y) / 2,
                    ROW_LENGTH, ROW_SEP, seed=100)
    # C1_inner — flat gravel field
    add_terrain_tile(w, X_MID, 0.0, ROW_LENGTH, ROW_SEP,
                     r=0.55, g=0.52, b=0.48, name="terrain_c1_inner")
    # C3_right — loose gravels
    add_loose_gravel(w, X_MID, (INNER_Y + OUTER_Y) / 2,
                     ROW_LENGTH, ROW_SEP, n_stones=100, seed=200)
    add_natural_row(w, y_center=-0.65, curve_amp=0.10, curve_period=6.0,
                    y_jitter=0.06, x_jitter=0.03, size_var=0.10,
                    colour_var=0.06, canopy_r_base=0.18, seed=10)
    add_natural_row(w, y_center= 0.65, curve_amp=0.10, curve_period=6.0,
                    y_jitter=0.06, x_jitter=0.03, size_var=0.10,
                    colour_var=0.06, canopy_r_base=0.18, seed=20)
    add_natural_row(w, y_center=-1.95, curve_amp=0.08, curve_period=7.0,
                    y_jitter=0.05, x_jitter=0.03, size_var=0.10,
                    colour_var=0.06, canopy_r_base=0.18, seed=30)
    add_natural_row(w, y_center= 1.95, curve_amp=0.08, curve_period=7.0,
                    y_jitter=0.05, x_jitter=0.03, size_var=0.10,
                    colour_var=0.06, canopy_r_base=0.18, seed=40)

    add_end_posts(w, x=9.4, y_pairs=[(-0.65, 0.65)])
    return w


def challenging() -> World:
    w = World(
        name="crop_challenging",
        robot_x=-0.5, robot_y=-1.3,
        ambient=(0.28, 0.28, 0.28, 1.0),
        sun_dir=(-0.2, 0.5, -0.45),
        fog_density=0.055,
        fog_start=1.5,
        fog_end=14.0,
    )
    # C2_left — bumpy grassfield (darker under low light)
    add_grass_field(w, X_MID, -(INNER_Y + OUTER_Y) / 2,
                    ROW_LENGTH, ROW_SEP, seed=110)
    # C1_inner — flat gravel field
    add_terrain_tile(w, X_MID, 0.0, ROW_LENGTH, ROW_SEP,
                     r=0.55, g=0.52, b=0.48, name="terrain_c1_inner")
    # C3_right — loose gravels
    add_loose_gravel(w, X_MID, (INNER_Y + OUTER_Y) / 2,
                     ROW_LENGTH, ROW_SEP, n_stones=100, seed=210)
    add_natural_row(w, y_center=-0.65, curve_amp=0.16, curve_period=4.5,
                    y_jitter=0.12, x_jitter=0.07, size_var=0.20,
                    colour_var=0.14, canopy_r_base=0.20,
                    skip=[4, 5, 11], seed=11)
    add_natural_row(w, y_center= 0.65, curve_amp=0.16, curve_period=4.5,
                    y_jitter=0.12, x_jitter=0.07, size_var=0.20,
                    colour_var=0.14, canopy_r_base=0.20,
                    skip=[7, 8, 9], seed=21)
    add_natural_row(w, y_center=-1.95, curve_amp=0.12, curve_period=5.5,
                    y_jitter=0.09, x_jitter=0.05, size_var=0.16,
                    colour_var=0.10, canopy_r_base=0.20, seed=31)
    add_natural_row(w, y_center= 1.95, curve_amp=0.12, curve_period=5.5,
                    y_jitter=0.09, x_jitter=0.05, size_var=0.16,
                    colour_var=0.10, canopy_r_base=0.20, seed=41)

    add_end_posts(w, x=9.4, y_pairs=[(-0.65, 0.65)])

    # Obstacles sit inside the corridor so the robot must detect their edges
    w.boxes.append(Box("crate",  4.5,  0.30, 0.15, 0.25, 0.25, 0.25,
                        r=0.50, g=0.30, b=0.10))
    w.boxes.append(Box("debris", 6.8, -0.30, 0.03, 0.60, 0.06, 0.06,
                        r=0.32, g=0.20, b=0.08))
    return w
