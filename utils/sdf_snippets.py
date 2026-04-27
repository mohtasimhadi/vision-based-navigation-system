from .data_classes import Plant, Box

def load_template(path):
    with open(path, "r") as f:
        return f.read()

def _plant_sdf(p: Plant, idx: int) -> str:
    template = load_template("templates/plant.sdf")
    return template.format(
        idx=idx,
        x=p.x,
        y=p.y,
        canopy_z=p.canopy_z,
        canopy_r=p.canopy_r,
        cr=p.cr,
        cg=p.cg,
        cb=p.cb
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
        r=b.r,
        g=b.g,
        b=b.b
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
        make_wheel("front_left",  0.254,  0.285),
        make_wheel("front_right", 0.254, -0.285),
        make_wheel("rear_left",  -0.254,  0.285),
        make_wheel("rear_right", -0.254, -0.285),
    ])

    return robot_template.format(
        rx=f"{rx:.3f}",
        ry=f"{ry:.3f}",
        wheels=wheels
    )