from utils.data_classes import World
from utils.generators import add_natural_row, add_end_posts
from utils.data_classes import Box

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
