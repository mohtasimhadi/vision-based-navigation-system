import argparse
import os
from utils import World, nominal, challenging, assemble

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="worlds")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    scenarios = {
        "crop_nominal.sdf": nominal(),
        "crop_challenging.sdf": challenging(),
    }

    for fname, world in scenarios.items():
        path = os.path.join(args.output_dir, fname)

        with open(path, "w") as f:
            f.write(assemble(world))

        fog = f"fog=d{world.fog_density:.3f}" if world.fog_density else "fog=none"
        print(f"[OK] {path} plants={len(world.plants)} boxes={len(world.boxes)} {fog}")


if __name__ == "__main__":
    main()