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
│           │   ├── camera_viewer.py    # Camera feed subscriber + OpenCV display
│           │   ├── row_detector.py     # HSV segmentation + corridor detection
│           │   ├── vanishing_point.py  # Vanishing point heading estimation
│           │   ├── vision_pipeline.py  # Unified single-window pipeline
│           │   └── visual_servo.py     # P-controller → /cmd_vel
│           ├── package.xml           # ROS 2 package manifest
│           ├── setup.py              # Python package setup
│           ├── setup.cfg             # ament_python develop config
│           └── launch/
│               └── camera_view.launch.py   # Bridge + viewer launch file
├── scripts/                    # Convenience launchers
│   ├── run_sim.sh              # Launch Gazebo
│   ├── run_ros2.sh             # Build + launch ROS 2 nav stack
│   └── run_all.sh              # Launch both in separate terminals
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

### Quick Start (Convenience Scripts)

From the project root, run both in separate terminals:

```bash
./scripts/run_all.sh [nominal|challenging]
```

Or run them individually:

```bash
# Terminal 1 — Gazebo
./scripts/run_sim.sh nominal

# Terminal 2 — ROS 2 nav stack
./scripts/run_ros2.sh
```

### Manual Start

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

The launch file starts three things:
1. `ros_gz_bridge` — bidirectional bridge:
   - Gazebo `/camera` → ROS 2 `/camera/image_raw`
   - ROS 2 `/cmd_vel` → Gazebo `/cmd_vel`
2. `vision_pipeline` — displays the live feed, green mask, row detection, Canny edges, and vanishing point in a single tiled OpenCV window, **and publishes heading errors**.
3. `visual_servo` — subscribes to the heading errors and publishes `Twist` messages to `/cmd_vel`, making the robot drive forward and steer autonomously.

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
| `visual_servo` | `visual_servo.py` | **Controller** — P-controller that converts heading error to `Twist` on `/cmd_vel` |

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
| `/cmd_vel` | `geometry_msgs/Twist` | `visual_servo` | Velocity commands for the differential drive |

### Tuning the Controller

The launch file exposes three parameters you can override on the command line:

```bash
ros2 launch vision_nav camera_view.launch.py Kp:=0.003 Kd:=0.002 linear_x:=0.2 use_vp:=false
```

| Parameter | Default | Effect |
|-----------|---------|--------|
| `Kp` | `0.005` | Proportional gain. Higher = sharper steering response. |
| `Kd` | `0.001` | Derivative gain. Dampens oscillation; increase if the robot weaves. |
| `linear_x` | `0.3` | Base forward speed in m/s. The controller scales this down automatically when uncertain. |
| `use_vp` | `true` | Use vanishing-point heading when confidence ≥ `min_confidence`. Falls back to histogram otherwise. |

**Auto speed modulation** (no extra params):
- Robot slows when `|heading_error|` is large.
- Robot slows when corridor width drops below ~120 px (narrowing path / obstacle ahead).
- Robot slows when VP confidence is zero (rows not clearly visible).

## Scenarios

### Nominal

| Parameter | Value |
|-----------|-------|
| Ambient light | 0.68 |
| Fog | None |
| Row spacing | 1.3 m between all rows (inner corridor = 1.3 m) |
| Plant rows | 4 (sinusoidal, curve_amp=0.10, y_jitter=0.06) |
| Plants | canopy_r_base=0.18 m, size_var=0.10 |
| Obstacles | 1 end-of-row post |

### Challenging

| Parameter | Value |
|-----------|-------|
| Ambient light | 0.28 |
| Fog density | 0.055 (range 1.5–14 m) |
| Row spacing | 1.3 m between all rows (inner corridor = 1.3 m) |
| Plant rows | 4 (sharper curves, increased jitter, missing plants) |
| Plants | canopy_r_base=0.20 m, size_var=0.20 |
| Obstacles | Crate (left side of corridor), debris (right side), end-of-row post |

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

## License

This project is open source. See [LICENSE](LICENSE) for details.
