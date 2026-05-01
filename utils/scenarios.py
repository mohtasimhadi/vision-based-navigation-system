import math
from utils.data_classes import World, Box
from utils.generators import (
    add_natural_row, add_terrain_tile, add_row_light, add_end_posts,
    add_grass_field, add_loose_gravel, add_corridor_light_strip,
)

# ── Field geometry ────────────────────────────────────────────────────────────
ROW_LENGTH = 9.0          # m — all plant rows run from x=0 to x=ROW_LENGTH
X_MID      = ROW_LENGTH / 2.0

# Asymmetric row layout: corridor widths + plant sizes work together so the
# *navigable gap* (corridor − left canopy − right canopy) graduates left→right.
#
# Nominal navigable gaps:
#   C2_left  ≈ 1.15 − 0.11 − 0.14 = 0.90 m
#   C1_inner ≈ 1.00 − 0.14 − 0.17 = 0.69 m
#   C3_right ≈ 1.00 − 0.17 − 0.20 = 0.63 m
ROW_Y = [-1.25, -0.10, +0.90, +1.90]   # outer_L, inner_L, inner_R, outer_R

C2_CENTRE = (ROW_Y[0] + ROW_Y[1]) / 2   # -0.675
C1_CENTRE = (ROW_Y[1] + ROW_Y[2]) / 2   # +0.40
C3_CENTRE = (ROW_Y[2] + ROW_Y[3]) / 2   # +1.40

# ── Robot start positions ─────────────────────────────────────────────────────
ROBOT_ROWS = [
    {'x': -0.5,        'y': C2_CENTRE, 'yaw': 0.0},      # 0: C2_left,  facing +X
    {'x':  ROW_LENGTH, 'y': C1_CENTRE, 'yaw': math.pi},  # 1: C1_inner, facing -X
    {'x': -0.5,        'y': C3_CENTRE, 'yaw': 0.0},      # 2: C3_right, facing +X
]


def _add_corridor_tiles(w: World, row_y: list, brightness: float = 1.0):
    """
    Add a differently-coloured ground tile for each of the three corridors.
    row_y: [outer_L, inner_L, inner_R, outer_R]
    """
    bf = brightness
    # C2_left  — dry reddish-brown soil
    add_terrain_tile(w, X_MID, (row_y[0] + row_y[1]) / 2, ROW_LENGTH, row_y[1] - row_y[0],
                     r=round(0.45 * bf, 3), g=round(0.24 * bf, 3), b=round(0.10 * bf, 3),
                     name="terrain_c2_left")
    # C1_inner — gravel field
    add_terrain_tile(w, X_MID, (row_y[1] + row_y[2]) / 2, ROW_LENGTH, row_y[2] - row_y[1],
                     r=round(0.55 * bf, 3), g=round(0.52 * bf, 3), b=round(0.48 * bf, 3),
                     name="terrain_c1_inner")
    # C3_right — dark moist clay
    add_terrain_tile(w, X_MID, (row_y[2] + row_y[3]) / 2, ROW_LENGTH, row_y[3] - row_y[2],
                     r=round(0.28 * bf, 3), g=round(0.16 * bf, 3), b=round(0.07 * bf, 3),
                     name="terrain_c3_right")


def nominal(row: int = 0) -> World:
    r = ROBOT_ROWS[row]
    w = World(
        name="crop_nominal",
        robot_x=r['x'], robot_y=r['y'], robot_yaw=r['yaw'],
        ambient=(0.68, 0.68, 0.68, 1.0),
        sun_dir=(-0.5, 0.1, -0.9),
    )
    # Simple flat ground tiles — no grass or gravel
    _add_corridor_tiles(w, ROW_Y, brightness=1.0)

    # Plants graduate in size left→right so the *navigable gap* tightens.
    add_natural_row(w, y_center=ROW_Y[0], curve_amp=0.08, curve_period=7.0,
                    y_jitter=0.05, x_jitter=0.03, size_var=0.10,
                    colour_var=0.06, canopy_r_base=0.11, seed=30)
    add_natural_row(w, y_center=ROW_Y[1], curve_amp=0.10, curve_period=6.0,
                    y_jitter=0.06, x_jitter=0.03, size_var=0.10,
                    colour_var=0.06, canopy_r_base=0.14, seed=10)
    add_natural_row(w, y_center=ROW_Y[2], curve_amp=0.10, curve_period=6.0,
                    y_jitter=0.06, x_jitter=0.03, size_var=0.10,
                    colour_var=0.06, canopy_r_base=0.17, seed=20)
    add_natural_row(w, y_center=ROW_Y[3], curve_amp=0.08, curve_period=7.0,
                    y_jitter=0.05, x_jitter=0.03, size_var=0.10,
                    colour_var=0.06, canopy_r_base=0.20, seed=40)

    add_end_posts(w, x=9.4, y_pairs=[(ROW_Y[1], ROW_Y[2])])

    # Per-corridor lighting moods
    add_corridor_light_strip(w, y=(ROW_Y[0] + ROW_Y[1]) / 2,
                             r=1.00, g=0.40, b=0.05, intensity=1.5,
                             name_prefix="nom_sunset")
    add_corridor_light_strip(w, y=(ROW_Y[1] + ROW_Y[2]) / 2,
                             r=1.00, g=0.98, b=0.85, intensity=1.8,
                             name_prefix="nom_noon")
    add_corridor_light_strip(w, y=(ROW_Y[2] + ROW_Y[3]) / 2,
                             r=0.05, g=0.05, b=0.08, intensity=0.05,
                             name_prefix="nom_overcast")

    return w


def challenging(row: int = 0) -> World:
    r = ROBOT_ROWS[row]
    w = World(
        name="crop_challenging",
        robot_x=r['x'], robot_y=r['y'], robot_yaw=r['yaw'],
        ambient=(0.28, 0.28, 0.28, 1.0),
        sun_dir=(-0.2, 0.5, -0.45),
        fog_density=0.055,
        fog_start=1.5,
        fog_end=14.0,
    )
    # C1_inner — loose gravel (2nd corridor)
    add_loose_gravel(w, X_MID, (ROW_Y[1] + ROW_Y[2]) / 2,
                     ROW_LENGTH, ROW_Y[2] - ROW_Y[1], n_stones=400,
                     r_min=0.003, r_max=0.008, seed=110)
    # C3_right — bumpy grassfield (3rd/last corridor)
    add_grass_field(w, X_MID, (ROW_Y[2] + ROW_Y[3]) / 2,
                    ROW_LENGTH, ROW_Y[3] - ROW_Y[2], seed=210)
    # Challenging: smaller uniform plants so every corridor stays passable
    # (~0.78 m gap in all corridors typical, >0.50 m even in worst case)
    add_natural_row(w, y_center=ROW_Y[0], curve_amp=0.12, curve_period=5.5,
                    y_jitter=0.06, x_jitter=0.05, size_var=0.12,
                    colour_var=0.10, canopy_r_base=0.15, seed=31)
    add_natural_row(w, y_center=ROW_Y[1], curve_amp=0.16, curve_period=4.5,
                    y_jitter=0.08, x_jitter=0.07, size_var=0.12,
                    colour_var=0.14, canopy_r_base=0.15,
                    skip=[4, 5, 11], seed=11, clear_end_m=1.5)
    add_natural_row(w, y_center=ROW_Y[2], curve_amp=0.16, curve_period=4.5,
                    y_jitter=0.08, x_jitter=0.07, size_var=0.12,
                    colour_var=0.14, canopy_r_base=0.15,
                    skip=[7, 8, 9], seed=21, clear_end_m=1.5)
    add_natural_row(w, y_center=ROW_Y[3], curve_amp=0.12, curve_period=5.5,
                    y_jitter=0.06, x_jitter=0.05, size_var=0.12,
                    colour_var=0.10, canopy_r_base=0.15, seed=41)

    add_end_posts(w, x=9.4, y_pairs=[(ROW_Y[1], ROW_Y[2])])

    # Per-corridor lighting moods (complement the global dim ambient + fog)
    add_corridor_light_strip(w, y=(ROW_Y[0] + ROW_Y[1]) / 2,
                             r=0.90, g=0.62, b=0.18, intensity=1.0,
                             name_prefix="chal_dusk")
    add_corridor_light_strip(w, y=(ROW_Y[1] + ROW_Y[2]) / 2,
                             r=0.22, g=0.28, b=0.60, intensity=0.6,
                             name_prefix="chal_moon")
    add_corridor_light_strip(w, y=(ROW_Y[2] + ROW_Y[3]) / 2,
                             r=0.42, g=0.48, b=0.58, intensity=0.55,
                             name_prefix="chal_storm")

    return w
