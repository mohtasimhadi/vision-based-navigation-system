import numpy as np
from utils.data_classes import Plant, Box

def load_template(path):
    with open(path, "r") as f:
        return f.read()

def _plant_sdf(p: Plant, idx: int) -> str:
    template = load_template("templates/plant.sdf")

    crown_z  = round(p.stem_h / 2, 3)
    crown_r  = round(p.stem_r, 3)
    crown_h  = round(p.stem_h, 3)
    canopy_z = round(p.canopy_z, 3)
    canopy_r = round(p.canopy_r, 3)

    # Secondary lobe — seeded per-plant so the world is deterministic
    rng = np.random.default_rng(idx)
    sec_off_x = rng.uniform(-canopy_r * 0.5, canopy_r * 0.5)
    sec_off_y = rng.uniform(-canopy_r * 0.5, canopy_r * 0.5)
    sec_r     = float(canopy_r * rng.uniform(0.55, 0.75))
    sec_x     = round(p.x + sec_off_x, 4)
    sec_y     = round(p.y + sec_off_y, 4)
    sec_z     = round(p.canopy_z - canopy_r * 0.25 + rng.uniform(-0.05, 0.05), 4)
    sec_r     = round(sec_r, 4)

    # Secondary lobe is a slightly darker shade
    cr2 = round(float(np.clip(p.cr * 0.80, 0.0, 1.0)), 4)
    cg2 = round(float(np.clip(p.cg * 0.85, 0.0, 1.0)), 4)
    cb2 = round(float(np.clip(p.cb * 0.90, 0.0, 1.0)), 4)

    return template.format(
        idx=idx,
        x=p.x,
        y=p.y,
        crown_z=crown_z,
        crown_r=crown_r,
        crown_h=crown_h,
        canopy_z=canopy_z,
        canopy_r=canopy_r,
        sec_x=sec_x,
        sec_y=sec_y,
        sec_z=sec_z,
        sec_r=sec_r,
        cr=p.cr,
        cg=p.cg,
        cb=p.cb,
        cr2=cr2,
        cg2=cg2,
        cb2=cb2,
    )

def _box_sdf(b: Box) -> str:
    with open("templates/box.sdf") as f:
        template = f.read()

    return template.format(
        name=b.name,
        x=f"{b.x:.3f}",
        y=f"{b.y:.3f}",
        z=f"{b.z:.3f}",
        sx=b.sx,
        sy=b.sy,
        sz=b.sz,
        r=f"{b.r:.3f}",
        g=f"{b.g:.3f}",
        b=f"{b.b:.3f}"
    )

def _robot_sdf(rx: float, ry: float) -> str:
    with open("templates/robot.sdf") as f:
        robot_template = f.read()

    with open("templates/wheel.sdf") as f:
        wheel_template = f.read()

    def make_wheel(name, jx, jy):
        return wheel_template.format(
            name=name,
            jx=f"{jx:.3f}",
            jy=f"{jy:.3f}"
        )

    wheels = "\n".join([
        make_wheel("front_left",  0.169,  0.190),
        make_wheel("front_right", 0.169, -0.190),
        make_wheel("rear_left",  -0.169,  0.190),
        make_wheel("rear_right", -0.169, -0.190),
    ])

    return robot_template.format(
        rx=f"{rx:.3f}",
        ry=f"{ry:.3f}",
        wheels=wheels
    )
