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

