from utils.data_classes import World, Box
from utils.generators import add_natural_row, add_terrain_tile, add_row_light

# ── Field geometry ────────────────────────────────────────────────────────────
ROW_LENGTH = 9.0          # m — all plant rows run from x=0 to x=ROW_LENGTH
X_MID      = ROW_LENGTH / 2.0
ROW_SEP    = 1.80         # m between adjacent row centre-lines

INNER_Y    = 0.90         # inner rows at ±INNER_Y  (define the C1_inner corridor)
OUTER_Y    = 2.70         # outer rows at ±OUTER_Y  (define C2_left / C3_right)

# gap = ROW_SEP - 2 * CANOPY_R_INNER  →  1.80 - 2*0.23 = 1.34 m
# Rover track width ≈ 0.57 m → ~38 cm clearance per side (very comfortable)
CANOPY_R_INNER = 0.23
CANOPY_R_OUTER = 0.23

# Corridor side offset — obstacles sit near the row edges, well clear of centre
SIDE_OFFSET = 0.55


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


def nominal() -> World:
    w = World(
        name="crop_nominal",
        robot_x=-0.5, robot_y=-1.8,
        ambient=(0.68, 0.68, 0.68, 1.0),
        sun_dir=(-0.5, 0.1, -0.9),
    )

    _add_corridor_tiles(w, brightness=1.0)

    # ── Row 1: outer left — tall, stately plants with gentle long curves ──────
    add_natural_row(w, y_center=-OUTER_Y,
                    curve_amp=0.12, curve_period=8.0,
                    spacing=0.60,
                    y_jitter=0.04, x_jitter=0.03,
                    size_var=0.08, colour_var=0.05,
                    canopy_r_base=CANOPY_R_OUTER + 0.02, seed=10)

    # ── Row 2: inner left — classic medium bushes, moderate curves ────────────
    add_natural_row(w, y_center=-INNER_Y,
                    curve_amp=0.10, curve_period=5.5,
                    spacing=0.52,
                    y_jitter=0.05, x_jitter=0.03,
                    size_var=0.10, colour_var=0.06,
                    canopy_r_base=CANOPY_R_INNER, seed=20)

    # ── Row 3: inner right — dense low hedges, tight zig-zags ─────────────────
    add_natural_row(w, y_center= INNER_Y,
                    curve_amp=0.08, curve_period=4.0,
                    spacing=0.45,
                    y_jitter=0.04, x_jitter=0.02,
                    size_var=0.06, colour_var=0.04,
                    canopy_r_base=CANOPY_R_INNER - 0.02, seed=30)

    # ── Row 4: outer right — wild mixed growth, high variation ────────────────
    add_natural_row(w, y_center= OUTER_Y,
                    curve_amp=0.14, curve_period=6.5,
                    spacing=0.55,
                    y_jitter=0.06, x_jitter=0.04,
                    size_var=0.18, colour_var=0.10,
                    canopy_r_base=CANOPY_R_OUTER + 0.01, seed=40)

    # ── Per-corridor lights (nominal — warm morning conditions) ───────────────
    add_row_light(w, "light_c2_left",  4.5, -1.8, 3.5,
                  r=1.0, g=0.88, b=0.65, intensity=0.55)
    add_row_light(w, "light_c1_inner", 4.5,  0.0, 3.5,
                  r=0.95, g=0.95, b=1.0, intensity=0.65)
    add_row_light(w, "light_c3_right", 4.5,  1.8, 3.5,
                  r=0.80, g=0.90, b=1.0, intensity=0.50)

    # ── Per-corridor obstacles (placed near row edges, centre lane kept clear) ─
    # C2_left: wooden stake post near inner row edge
    w.boxes.append(Box("stake_c2", 3.5, -INNER_Y - SIDE_OFFSET, 0.35,
                        0.06, 0.06, 0.70, r=0.65, g=0.50, b=0.25))
    # C1_inner: small crate near right row edge
    w.boxes.append(Box("crate_c1", 5.0,  INNER_Y - SIDE_OFFSET, 0.10,
                        0.18, 0.18, 0.20, r=0.50, g=0.30, b=0.10))
    # C3_right: small rock near inner row edge
    w.boxes.append(Box("rock_c3",  6.5,  INNER_Y + SIDE_OFFSET, 0.06,
                        0.14, 0.11, 0.12, r=0.55, g=0.52, b=0.48))

    return w


def challenging() -> World:
    w = World(
        name="crop_challenging",
        robot_x=-0.5, robot_y=-1.8,
        ambient=(0.28, 0.28, 0.28, 1.0),
        sun_dir=(-0.2, 0.5, -0.45),
        fog_density=0.055,
        fog_start=1.5,
        fog_end=14.0,
    )

    _add_corridor_tiles(w, brightness=0.55)

    # ── Row 1: outer left — storm-damaged, sparse with large gaps ─────────────
    add_natural_row(w, y_center=-OUTER_Y,
                    curve_amp=0.22, curve_period=9.0,
                    spacing=0.72,
                    y_jitter=0.07, x_jitter=0.06,
                    size_var=0.30, colour_var=0.20,
                    canopy_r_base=CANOPY_R_OUTER,
                    skip=[2, 3, 7, 11], seed=11)

    # ── Row 2: inner left — overgrown, aggressive short-period curves ─────────
    add_natural_row(w, y_center=-INNER_Y,
                    curve_amp=0.20, curve_period=3.8,
                    spacing=0.48,
                    y_jitter=0.06, x_jitter=0.08,
                    size_var=0.28, colour_var=0.18,
                    canopy_r_base=CANOPY_R_INNER,
                    skip=[3, 4, 5, 11, 12], seed=21)

    # ── Row 3: inner right — dying, erratic placement, brownish tinge ─────────
    add_natural_row(w, y_center= INNER_Y,
                    curve_amp=0.15, curve_period=5.2,
                    spacing=0.50,
                    y_jitter=0.08, x_jitter=0.07,
                    size_var=0.22, colour_var=0.22,
                    canopy_r_base=CANOPY_R_INNER - 0.03,
                    skip=[7, 8, 9, 14], seed=31)

    # ── Row 4: outer right — weeds, very irregular, mixed sizes ───────────────
    add_natural_row(w, y_center= OUTER_Y,
                    curve_amp=0.18, curve_period=6.8,
                    spacing=0.65,
                    y_jitter=0.07, x_jitter=0.05,
                    size_var=0.38, colour_var=0.24,
                    canopy_r_base=CANOPY_R_OUTER + 0.04,
                    skip=[5, 10, 13], seed=41)

    # ── Per-corridor lights (challenging — degraded conditions) ───────────────
    add_row_light(w, "light_c2_left",  4.5, -1.8, 2.5,
                  r=0.90, g=0.70, b=0.40, intensity=0.35)
    add_row_light(w, "light_c1_inner", 4.5,  0.0, 3.0,
                  r=0.75, g=0.80, b=0.75, intensity=0.28)
    add_row_light(w, "light_c3_right", 4.5,  1.8, 2.8,
                  r=0.60, g=0.65, b=0.80, intensity=0.30)

    # ── Per-corridor obstacles (placed near row edges, centre lane kept clear) ─
    # C2_left: rock cluster — one near inner row, one near outer row
    w.boxes.append(Box("rock_c2_a", 2.2, -INNER_Y - SIDE_OFFSET, 0.06,
                        0.16, 0.13, 0.12, r=0.50, g=0.47, b=0.43))
    w.boxes.append(Box("rock_c2_b", 2.5, -OUTER_Y + SIDE_OFFSET, 0.04,
                        0.10, 0.09, 0.08, r=0.50, g=0.47, b=0.43))
    # C1_inner: crate near right row edge + debris plank near left row edge
    w.boxes.append(Box("crate_c1",   3.5,  INNER_Y - SIDE_OFFSET, 0.15,
                        0.22, 0.22, 0.22, r=0.50, g=0.30, b=0.10))
    w.boxes.append(Box("debris_c1",  6.2, -INNER_Y + SIDE_OFFSET, 0.03,
                        0.55, 0.06, 0.06, r=0.32, g=0.20, b=0.08))
    # C3_right: fallen branch near inner row edge
    w.boxes.append(Box("branch_c3",  5.5,  INNER_Y + SIDE_OFFSET, 0.03,
                        0.80, 0.08, 0.06, r=0.28, g=0.18, b=0.08))

    return w
