from pathlib import Path
from .data_classes import World
from utils.sdf_snippets import _plant_sdf, _box_sdf, _robot_sdf

def assemble(w: World) -> str:
    template = "templates/world.sdf"

    fog = ""
    if w.fog_density > 0:
        fog = f"""
      <fog>
        <color>0.75 0.75 0.75 1</color>
        <type>linear</type>
        <start>{w.fog_start}</start>
        <end>{w.fog_end}</end>
        <density>{w.fog_density:.4f}</density>
      </fog>"""

    plants = "\n\n".join(_plant_sdf(p, i) for i, p in enumerate(w.plants))
    boxes  = "\n\n".join(_box_sdf(b) for b in w.boxes)

    objects = "\n\n".join(x for x in [plants, boxes] if x)

    robot = _robot_sdf(w.robot_x, w.robot_y)

    return template.format(
        name=w.name,
        sun_dir_x=w.sun_dir[0],
        sun_dir_y=w.sun_dir[1],
        sun_dir_z=w.sun_dir[2],
        ambient_r=w.ambient[0],
        ambient_g=w.ambient[1],
        ambient_b=w.ambient[2],
        ambient_a=w.ambient[3],
        fog=fog,
        objects=objects,
        robot=robot,
    )