from utils.data_classes import World
from utils.generators import add_natural_row, add_end_posts
from utils.data_classes import Box

def nominal() -> World:
    w = World(
        name="crop_nominal",
        robot_x=-0.5, robot_y=0.0,
        ambient=(0.68, 0.68, 0.68, 1.0),
        sun_dir=(-0.5, 0.1, -0.9),
    )

    add_natural_row(w, y_center=-0.9, curve_amp=0.06, curve_period=7.0,
                    y_jitter=0.05, x_jitter=0.03, size_var=0.12,
                    colour_var=0.06, seed=10)
    add_natural_row(w, y_center= 0.9, curve_amp=0.06, curve_period=7.0,
                    y_jitter=0.05, x_jitter=0.03, size_var=0.12,
                    colour_var=0.06, seed=20)
    add_natural_row(w, y_center=-2.1, curve_amp=0.05, curve_period=8.0,
                    y_jitter=0.05, x_jitter=0.03, size_var=0.12,
                    colour_var=0.06, seed=30)
    add_natural_row(w, y_center= 2.1, curve_amp=0.05, curve_period=8.0,
                    y_jitter=0.05, x_jitter=0.03, size_var=0.12,
                    colour_var=0.06, seed=40)

    add_end_posts(w, x=9.4, y_pairs=[(-0.9, 0.9)])
    return w


def challenging() -> World:
    w = World(
        name="crop_challenging",
        robot_x=-0.5, robot_y=0.0,
        ambient=(0.28, 0.28, 0.28, 1.0),
        sun_dir=(-0.2, 0.5, -0.45),
        fog_density=0.055,
        fog_start=1.5,
        fog_end=14.0,
    )

    add_natural_row(w, y_center=-0.9, curve_amp=0.14, curve_period=5.0,
                    y_jitter=0.13, x_jitter=0.08, size_var=0.25,
                    colour_var=0.14, skip=[4, 5, 11], seed=11)
    add_natural_row(w, y_center= 0.9, curve_amp=0.14, curve_period=5.0,
                    y_jitter=0.13, x_jitter=0.08, size_var=0.25,
                    colour_var=0.14, skip=[7, 8, 9], seed=21)
    add_natural_row(w, y_center=-2.1, curve_amp=0.10, curve_period=6.0,
                    y_jitter=0.10, x_jitter=0.06, size_var=0.20,
                    colour_var=0.10, seed=31)
    add_natural_row(w, y_center= 2.1, curve_amp=0.10, curve_period=6.0,
                    y_jitter=0.10, x_jitter=0.06, size_var=0.20,
                    colour_var=0.10, seed=41)

    add_end_posts(w, x=9.4, y_pairs=[(-0.9, 0.9)])

    w.boxes.append(Box("crate",  4.5,  0.55, 0.15, 0.25, 0.25, 0.25,
                        r=0.50, g=0.30, b=0.10))
    w.boxes.append(Box("debris", 6.8, -0.55, 0.03, 0.60, 0.06, 0.06,
                        r=0.32, g=0.20, b=0.08))
    return w