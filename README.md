# Vision-Based Navigation System

A simulation environment and vision-based navigation stack for autonomous robot navigation through crop fields. Includes a procedural Gazebo world generator and a ROS 2 navigation package that steers the robot using camera input only — no prebuilt navigation stack.

## Overview

The project has two layers:

- **World generator** — produces Gazebo SDF world files with configurable crop rows, lighting, fog, and obstacles
- **Navigation stack** (`vision_nav`) — a ROS 2 package that processes the robot's camera feed to estimate heading and control motion

Two simulation scenarios are provided:

- **Nominal** — ideal lighting, clear visibility, uniform plant rows
- **Challenging** — reduced ambient light, fog, sparse plants, and added obstacles

Both place a Husky-style robot at the start of a crop field, ready to load into Gazebo Sim.

## Project Structure

```
vision-based-navigation-system/
├── world_generator.py          # Entry point — generates SDF world files
├── templates/                  # SDF templates for world components
│   ├── world.sdf               # Base world (lighting, physics, fog)
│   ├── plant.sdf               # Crop plant model (stem + canopy sphere)
│   ├── robot.sdf               # Husky robot with camera and drive plugin
│   ├── box.sdf                 # Generic obstacle/post model
│   └── wheel.sdf               # Robot wheel model
├── utils/                      # World generator Python modules
│   ├── data_classes.py         # Plant, Box, and World dataclasses
│   ├── scenarios.py            # Scenario definitions (nominal, challenging)
│   ├── generators.py           # Row population and post placement
│   ├── assembler.py            # SDF template assembly engine
│   └── sdf/
│       └── snippets.py         # Per-component SDF string generators
├── ros2_ws/                    # ROS 2 workspace
│   └── src/
│       └── vision_nav/         # Vision navigation package
│           ├── vision_nav/
│           │   └── camera_viewer.py    # Camera feed subscriber + OpenCV display
│           └── launch/
│               └── camera_view.launch.py   # Bridge + viewer launch file
└── worlds/                     # Generated SDF output (gitignored)
```

## Requirements

### World Generator

- Python 3.10+
- NumPy

```bash
pip install numpy
```

### Navigation Stack

- ROS 2 Jazzy
- Gazebo (Harmonic or later)
- `ros_gz_bridge`, `cv_bridge`, `python3-opencv`

```bash
sudo apt install ros-jazzy-ros-gz-bridge ros-jazzy-cv-bridge python3-opencv
```

## Generating the Worlds

```bash
python world_generator.py
```

Output:

```
[OK] worlds/crop_nominal.sdf     plants=68  boxes=1  fog=none
[OK] worlds/crop_challenging.sdf plants=62  boxes=3  fog=d0.055
```

Load into Gazebo:

```bash
gz sim worlds/crop_nominal.sdf
```

## Running the Navigation Stack

**Terminal 1 — Gazebo:**

```bash
gz sim worlds/crop_nominal.sdf
```

**Terminal 2 — Build and launch the ROS 2 node:**

```bash
cd ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select vision_nav
source install/setup.bash
ros2 launch vision_nav camera_view.launch.py
```

The launch file starts a `ros_gz_bridge` node that bridges the Gazebo camera topic to ROS 2, then starts the `camera_viewer` node which displays the live feed in an OpenCV window.

## Navigation Architecture

```
[Gazebo Camera]
      |
      v
[Perception]       RGB segmentation · feature tracking · optical flow
      |
      v
[Estimation]       Row centerline · heading error · traversability map
      |
      v
[Control]          Visual servoing → /cmd_vel
```

The navigation stack is custom — it does not use `move_base` or `nav2`. Only ROS 2 topics and `ros_gz_bridge` are used for transport.

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

## Robot Model

Four-wheeled differential-drive platform modeled after the Clearpath Husky:

- Differential drive plugin on `/cmd_vel`
- Forward-facing camera (640×480, 30 fps, 60° FOV) mounted at 0.45 m forward, 20° downward pitch
- Camera publishes on Gazebo topic `/camera`, bridged to `/camera/image_raw` in ROS 2

## How the World Generator Works

1. **Scenario definition** (`utils/scenarios.py`) — configures lighting, fog, and plant row parameters
2. **Row generation** (`utils/generators.py`) — places plants with seed-controlled randomization, sinusoidal curves, and per-plant size/color variance
3. **SDF assembly** (`utils/assembler.py`) — fills `world.sdf` with rendered plant, box, and robot snippets
4. **Output** (`world_generator.py`) — writes assembled SDF to disk

## License

This project is open source. See [LICENSE](LICENSE) for details.
