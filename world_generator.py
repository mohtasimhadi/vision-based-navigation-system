import argparse
import os
from utils import World, nominal, challenging, assemble


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="worlds")
    ap.add_argument("--row", type=int, choices=[0, 1, 2], default=0,
                    help="Starting corridor: 0=C2_left  1=C1_inner  2=C3_right")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    scenarios = {
        "crop_nominal.sdf":     nominal(args.row),
        "crop_challenging.sdf": challenging(args.row),
    }

    for fname, world in scenarios.items():
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
