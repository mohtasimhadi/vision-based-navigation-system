import argparse
import os
from utils import World, nominal, challenging, assemble

# Spawn poses for each row: (x, y, yaw)
# Must match the corridor centres defined in utils/scenarios.py
ROW_SPAWNS = {
    "0": {"name": "C2_left",  "x": -0.5, "y": -1.00, "yaw": 0.0},
    "1": {"name": "C1_inner", "x":  9.4, "y":  0.00, "yaw": 3.14159},
    "2": {"name": "C3_right", "x": -0.5, "y":  1.00, "yaw": 0.0},
}


def apply_row_spawn(world: World, row: str):
    if row not in ROW_SPAWNS:
        raise ValueError(f"Invalid row '{row}'. Choose from: {', '.join(ROW_SPAWNS.keys())}")
    spawn = ROW_SPAWNS[row]
    world.robot_x = spawn["x"]
    world.robot_y = spawn["y"]
    world.robot_yaw = spawn["yaw"]
    return world


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="worlds")
    ap.add_argument(
        "--row", default="0",
        help="Starting row index: 0=C2_left, 1=C1_inner, 2=C3_right"
    )
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    scenarios = {
        "crop_nominal.sdf": nominal(),
        "crop_challenging.sdf": challenging(),
    }

    for fname, world in scenarios.items():
        world = apply_row_spawn(world, args.row)
        path = os.path.join(args.output_dir, fname)
        out = assemble(world)

        with open(path, "w") as f:
            f.write(out)

        fog = f"fog=d{world.fog_density:.3f}" if world.fog_density else "fog=none"
        print(f"[OK] {path} plants={len(world.plants)} boxes={len(world.boxes)} {fog}")
        print(f"    robot=({world.robot_x}, {world.robot_y}, yaw={world.robot_yaw:.2f})")
        print(f"    SDF SIZE: {len(out)}")

if __name__ == "__main__":
    main()
