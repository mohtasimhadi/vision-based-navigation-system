# Vision-Based Navigation System

A procedural world generator for simulating autonomous robot navigation through crop fields. Produces Gazebo-compatible SDF world files with configurable plant rows, environmental conditions, and a differential-drive robot equipped with a camera sensor.

## Overview

This tool generates two simulation scenarios for training and evaluating vision-based navigation algorithms in agricultural environments:

- **Nominal** — ideal lighting, clear visibility, uniform plant rows
- **Challenging** — reduced ambient light, fog, sparse plants, and added obstacles

Both scenarios place a Husky-style robot at the start of a crop field and are ready to load directly into Gazebo Sim.

## Project Structure

```
vision-based-navigation-system/
├── world_generator.py      # Entry point — generates SDF world files
├── templates/              # SDF templates for world components
│   ├── world.sdf           # Base world (lighting, physics, fog)
│   ├── plant.sdf           # Crop plant model (stem + canopy sphere)
│   ├── robot.sdf           # Husky robot with camera and drive plugin
│   ├── box.sdf             # Generic obstacle/post model
│   └── wheel.sdf           # Robot wheel model
├── utils/                  # Python modules
│   ├── data_classes.py     # Plant, Box, and World dataclasses
│   ├── scenarios.py        # Scenario definitions (nominal, challenging)
│   ├── generators.py       # Row population and post placement
│   ├── assembler.py        # SDF template assembly engine
│   └── sdf/
│       └── snippets.py     # Per-component SDF string generators
└── worlds/                 # Output directory for generated SDF files
```

## Requirements

- Python 3.10+
- NumPy

```bash
pip install numpy
```

No other dependencies are required. The generated SDF files target **Gazebo SDF 1.10** with the ODE physics engine.

## Usage

```bash
# Generate both worlds to the default worlds/ directory
python world_generator.py

# Specify a custom output directory
python world_generator.py --output-dir /path/to/output
```

Expected output:

```
[OK] worlds/crop_nominal.sdf     plants=81  boxes=1  fog=none
    SDF SIZE: 89444
[OK] worlds/crop_challenging.sdf plants=64  boxes=3  fog=d0.055
    SDF SIZE: 83365
```

Load either file into Gazebo Sim:

```bash
gz sim worlds/crop_nominal.sdf
```

## Scenarios

### Nominal

| Parameter | Value |
|-----------|-------|
| Ambient light | 0.68 |
| Fog | None |
| Plant rows | 4 (sinusoidal, naturally spaced) |
| Obstacles | 1 end-of-row post |

### Challenging

| Parameter | Value |
|-----------|-------|
| Ambient light | 0.28 |
| Fog density | 0.055 (range 1.5–14 m) |
| Plant rows | 4 (increased positional jitter, missing plants) |
| Obstacles | Crate, debris, end-of-row post |

## How It Works

1. **Scenario definition** (`utils/scenarios.py`) — configures lighting, fog, and plant row parameters, then calls the generators to populate a `World` object.
2. **Row generation** (`utils/generators.py`) — places plants along each row with seed-controlled randomization for reproducible results. Applies sinusoidal curves, spacing jitter, and size/color variance per plant.
3. **SDF assembly** (`utils/assembler.py`) — fills the `world.sdf` template with rendered plant, box, and robot SDF snippets produced by `utils/sdf/snippets.py`.
4. **Output** (`world_generator.py`) — writes the assembled SDF to disk and prints generation statistics.

## Robot Model

The simulated robot is a four-wheeled differential-drive platform modeled after the Clearpath Husky. It includes:

- Four mecanum-style wheels with friction and inertia properties
- A forward-facing camera sensor on a fixed joint
- A differential drive plugin compatible with Gazebo Sim's gz-sim-diff-drive-system

## Extending the System

- **Add a scenario** — create a new function in `utils/scenarios.py` following the `nominal()` or `challenging()` pattern, then call it in `world_generator.py`.
- **Change plant appearance** — modify the `Plant` dataclass fields or the color/size variance parameters passed to `add_natural_row()`.
- **Add obstacle types** — define a new `Box` instance with the desired position, dimensions, and color, then append it to `world.boxes`.
- **Swap the robot** — replace the template in `templates/robot.sdf` and update `utils/sdf/snippets.py` accordingly.

## License

This project is open source. See [LICENSE](LICENSE) for details.
