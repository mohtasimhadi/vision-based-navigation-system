# Vision-Based Navigation System

A simulation environment and vision-based navigation stack for autonomous robot navigation through crop fields. Includes a procedural Gazebo world generator and a ROS 2 navigation package that steers the robot using camera input only — no prebuilt navigation stack.

## Overview

The project has two layers:

- **World generator** — produces Gazebo SDF world files with configurable crop rows, lighting, fog, and obstacles
- **Navigation stack** (`vision_nav`) — a ROS 2 package that uses edge-based vision to detect all boundaries (plants, obstacles, posts) and steer through the widest open gap

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
│   ├── wheel.sdf               # Robot wheel model
│   ├── grass_patch.sdf         # Ground vegetation patch
│   ├── gravel_stone.sdf        # Gravel debris model
│   ├── light_point.sdf         # Point light template
│   ├── light_spot.sdf          # Spot light template
│   └── light_spot_row.sdf      # Row of spot lights
├── utils/                      # World generator Python modules
│   ├── data_classes.py         # Plant, Box, and World dataclasses
│   ├── scenarios.py            # Scenario definitions (nominal, challenging)
│   ├── generators.py           # Row population and post placement
│   ├── assembler.py            # SDF template assembly engine
│   └── sdf/
│       └── snippets.py         # Per-component SDF string generators
├── vision_nav/                 # ROS 2 workspace + vision navigation package
│   ├── vision_nav/
│   │   ├── camera_viewer.py    # Camera feed subscriber + OpenCV display
│   │   ├── row_detector.py     # HSV segmentation + corridor detection
│   │   ├── vanishing_point.py  # Vanishing point heading estimation
│   │   ├── vision_pipeline.py  # Unified single-window pipeline
│   │   ├── visual_servo.py     # P-controller → /cmd_vel
│   │   ├── field_traverser.py  # Multi-row field traversal state machine
│   │   └── navigate_cli.py     # Interactive CLI to send row commands
│   ├── package.xml             # ROS 2 package manifest
│   ├── setup.py                # Python package setup
│   ├── setup.cfg               # ament_python develop config
│   └── launch/
│       └── camera_view.launch.py   # Bridge + viewer + traverser launch file
├── scripts/                    # Convenience launchers
│   ├── run_sim.sh              # Launch Gazebo
│   └── run_ros2.sh             # Build + launch ROS 2 nav stack
├── run_all.sh                  # Launch both sim and nav in separate terminals
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

## Running Tests

The test suite covers the world generator and vision pipeline pure functions without requiring a ROS 2 installation.

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=utils --cov=vision_nav
```

All tests mock ROS 2 internals via `conftest.py`, so they run on any machine with Python 3.10+.

## Generating the Worlds

```bash
python world_generator.py
```

Output:

```
[OK] worlds/crop_nominal.sdf     plants=68  boxes=5  fog=none
[OK] worlds/crop_challenging.sdf plants=57  boxes=2  fog=d0.055
```

You can also select the starting corridor:

```bash
python world_generator.py --row 0   # C2_left (default)
python world_generator.py --row 1   # C1_inner
python world_generator.py --row 2   # C3_right
```

Load into Gazebo:

```bash
gz sim worlds/crop_nominal.sdf
```

## Running the Navigation Stack

### Quick Start (Convenience Scripts)

From the project root, run both in separate terminals:

```bash
./run_all.sh [nominal|challenging] [0|1|2]
```

- Row `0` = C2_left  (default)
- Row `1` = C1_inner
- Row `2` = C3_right

Or run them individually:

```bash
# Terminal 1 — Gazebo
./scripts/run_sim.sh nominal 0

# Terminal 2 — ROS 2 nav stack
./scripts/run_ros2.sh 0
```

### Manual Start

**Terminal 1 — Gazebo:**

```bash
gz sim worlds/crop_nominal.sdf
```

**Terminal 2 — Build and launch the ROS 2 node:**

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select vision_nav --symlink-install
source install/setup.bash
ros2 launch vision_nav camera_view.launch.py
```

The launch file starts three things:
1. `ros_gz_bridge` — bidirectional bridge:
   - Gazebo `/camera` → ROS 2 `/camera/image_raw`
   - ROS 2 `/cmd_vel` → Gazebo `/cmd_vel`
2. `vision_pipeline` — displays the live feed, edge mask, row detection, Canny edges, and vanishing point in a single tiled OpenCV window, **and publishes heading errors + edge peak positions**.
3. `field_traverser` — state machine that follows each corridor to the end, turns onto the headland, transverses to the next row, aligns, and repeats until all 3 corridors are traversed.

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

### Nodes

| Node | File | What it does |
|------|------|--------------|
| `camera_viewer` | `camera_viewer.py` | Subscribes to `/camera/image_raw`, displays raw feed with frame info overlay |
| `row_detector` | `row_detector.py` | Converts each frame to HSV, masks crop green pixels, finds the low-green corridor, computes heading error in pixels |
| `vanishing_point` | `vanishing_point.py` | Detects row edges, fits left/right lines, computes vanishing point for stable heading estimation |
| `vision_pipeline` | `vision_pipeline.py` | **Unified node** — detects ALL edges (plants, obstacles, posts), finds the widest open valley between edge peaks, and publishes heading errors |
| `visual_servo` | `visual_servo.py` | **Controller** — P-controller that converts heading error to `Twist` on `/cmd_vel` (standalone) |
| `field_traverser` | `field_traverser.py` | **Field traverser** — state machine that drives down all 3 corridors sequentially |
| `navigate_cli` | `navigate_cli.py` | **CLI tool** — interactive terminal prompt to publish `/target_row` commands to the field traverser |

### Heading Error

**Edge-based corridor detection (`vision_pipeline`)**
```
heading_error = valley_centre_x - image_centre_x   (pixels)
```
- Computes a Canny edge map of the bottom 2/3 of the frame (detects plants, obstacles, posts, soil boundaries — any edge).
- Builds a per-column edge-density histogram and smooths it.
- Finds peaks = boundaries, then returns the **centre of the widest valley between two adjacent peaks**.
- This naturally avoids obstacles: an obstacle creates an extra peak, splitting the corridor into two valleys; the robot steers toward the wider (safer) opening.

**Vanishing point (`vanishing_point`)**
```
heading_error = vanishing_point_x - image_centre_x   (pixels)
```
- Derived from the intersection of extrapolated left-row and right-row lines detected by Hough transform on the edge map.
- Geometrically stable; only moves when the robot's heading relative to the rows actually changes.
- A confidence score (0–N) indicates how many line endpoints were detected on the weaker side.

The controller fuses both signals: vanishing point when confident, otherwise the edge-based valley centre.

### Published Topics

| Topic | Type | Source | Description |
|-------|------|--------|-------------|
| `/vision/heading_error` | `std_msgs/Float64` | `vision_pipeline` | Valley-centre heading error (px) |
| `/vision/vp_heading_error` | `std_msgs/Float64` | `vision_pipeline` | Vanishing point heading error (px) |
| `/vision/vp_confidence` | `std_msgs/Int32` | `vision_pipeline` | Line-detection confidence (pts) |
| `/vision/corridor_width` | `std_msgs/Float64` | `vision_pipeline` | Width of the widest edge valley (px) |
| `/vision/left_peak` | `std_msgs/Float64` | `vision_pipeline` | X-position of left edge peak (px) |
| `/vision/right_peak` | `std_msgs/Float64` | `vision_pipeline` | X-position of right edge peak (px) |
| `/cmd_vel` | `geometry_msgs/Twist` | `field_traverser` | Velocity commands for the differential drive |
| `/target_row` | `std_msgs/Int32` | `navigate_cli` | Manual row-selection command |

### Tuning the Controller

The launch file exposes parameters you can override on the command line:

```bash
ros2 launch vision_nav camera_view.launch.py Kp:=0.003 Kd:=0.002 linear_x:=0.2 use_vp:=false corridor_idx:=1
```

| Parameter | Default | Effect |
|-----------|---------|--------|
| `Kp` | `0.005` | Proportional gain. Higher = sharper steering response. |
| `Kd` | `0.001` | Derivative gain. Dampens oscillation; increase if the robot weaves. |
| `linear_x` | `0.2` | Base forward speed in m/s. The controller scales this down automatically when uncertain. |
| `use_vp` | `true` | Use vanishing-point heading when confidence ≥ `min_confidence`. Falls back to histogram otherwise. |
| `corridor_idx` | `0` | Which row to start from: `0`=C2_left, `1`=C1_inner, `2`=C3_right. |

**Field traversal pattern**
```
FOLLOW C2_left forward → TURN_PRE 90° left → TRANSVERSE 1.3 m → TURN_POST 90° right → ALIGN →
FOLLOW C1_inner forward → TURN_PRE 90° left → TRANSVERSE 1.3 m → TURN_POST 90° right → ALIGN →
FOLLOW C3_right forward → DONE
```
- Robot starts at the **leftmost corridor** (y = -0.675) and works rightward across the field.
- End-of-row is detected visually (rows disappear from view) with a distance backup.
- Transverse uses dead-reckoning from `/cmd_vel` integration.
- TURN_PRE / TURN_POST are timed 90° turns onto/off the headland.
- ALIGN fine-tunes until the new corridor is solidly ahead.

## Scenarios

### Nominal

| Parameter | Value |
|-----------|-------|
| Ambient light | 0.68 |
| Fog | None |
| Corridor widths | C2_left 1.15 m · C1_inner 1.00 m · C3_right 1.00 m |
| Plant rows | 4 (sinusoidal, curve_amp=0.08–0.10, y_jitter=0.05–0.06) |
| Plants | Graduated: 0.13 → 0.15 → 0.17 → 0.19 m, size_var=0.10 |
| Obstacles | 1 end-of-row post |
| Start position | Robot begins at **C2_left** (y = -0.675) |

### Challenging

| Parameter | Value |
|-----------|-------|
| Ambient light | 0.28 |
| Fog density | 0.055 (range 1.5–14 m) |
| Corridor widths | C2_left 1.15 m · C1_inner 1.00 m · C3_right 1.00 m |
| Plant rows | 4 (sharper curves, missing plants, y_jitter=0.06–0.08) |
| Plants | Uniform 0.15 m, size_var=0.12 |
| Ground | Loose gravel (C1_inner) + grass patches (C3_right) |
| Obstacles | End-of-row post only (no crate/debris) |
| Start position | Robot begins at **C2_left** (y = -0.675) |

## Robot Model

Four-wheeled differential-drive platform modeled after the Clearpath Husky:

- Differential drive plugin listening on Gazebo topic `/cmd_vel` (bridged from ROS 2)
- Wheel joints use `expressed_in="__model__"` axis so all four wheels rotate around the global Y axle correctly
- Forward-facing camera (640×480, 30 fps, 60° FOV) mounted at 0.45 m forward, 20° downward pitch
- Camera publishes on Gazebo topic `/camera`, bridged to `/camera/image_raw` in ROS 2

## Development Roadmap (Baby Steps)

| Step | Component | Status | What it teaches |
|------|-----------|--------|-----------------|
| 1 | Camera bridge + OpenCV viewer | ✅ Done | ROS 2 ↔ Gazebo image pipeline (`ros_gz_bridge`, `cv_bridge`) |
| 2 | HSV color segmentation | ✅ Done | Color spaces, masking, morphological operations |
| 3 | Vanishing point estimation | ✅ Done | Edge detection, Hough transform, line clustering, intersection geometry |
| 4 | Visual servoing controller | ✅ Done | Closed-loop control: heading error → P/PD controller → `/cmd_vel` |
| 5 | KLT feature tracking | 🔜 Future | Sparse optical flow, Lucas-Kanade |
| 6 | Dense optical flow | 🔜 Future | Farneback motion field, divergence analysis |
| 7 | Flow + segmentation fusion | 🔜 Future | Sensor fusion at the perception level |
| 8 | Traversability grid | 🔜 Future | Homography, top-down projection |
| 9 | Custom planner | 🔜 Future | Planning vs reactive control |

## How the World Generator Works

1. **Scenario definition** (`utils/scenarios.py`) — configures lighting, fog, and plant row parameters
2. **Row generation** (`utils/generators.py`) — places plants with seed-controlled randomization, sinusoidal curves, and per-plant size/color variance
3. **SDF assembly** (`utils/assembler.py`) — fills `world.sdf` with rendered plant, box, and robot snippets
4. **Output** (`world_generator.py`) — writes assembled SDF to disk
