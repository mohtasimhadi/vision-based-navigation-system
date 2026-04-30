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
| `vision_pipeline` | `vision_pipeline.py` | **Unified node** — runs segmentation + row detection + vanishing point, tiles outputs into one window, and publishes heading errors |
| `visual_servo` | `visual_servo.py` | **Controller** — P-controller that converts heading error to `Twist` on `/cmd_vel` |

### Heading Error

Two complementary heading estimates are produced:

**1. Corridor histogram (`row_detector`)**
```
heading_error = corridor_centre_x - image_centre_x   (pixels)
```
- Derived from the bottom 2/3 of the frame by finding the low-green corridor between crop rows.
- Fast but can be noisy when plants are missing or the robot is angled.
- Negative = corridor is left of centre, positive = right.

**2. Vanishing point (`vanishing_point`)**
```
heading_error = vanishing_point_x - image_centre_x   (pixels)
```
- Derived from the intersection of extrapolated left-row and right-row lines.
- Geometrically stable; only moves when the robot's heading relative to the rows actually changes.
- A confidence score (0–N) indicates how many line endpoints were detected on the weaker side.

The two signals can be fused in the controller stage for robust steering.

### Published Topics

| Topic | Type | Source | Description |
|-------|------|--------|-------------|
| `/vision/heading_error` | `std_msgs/Float64` | `vision_pipeline` | Corridor histogram heading error (px) |
| `/vision/vp_heading_error` | `std_msgs/Float64` | `vision_pipeline` | Vanishing point heading error (px) |
| `/vision/vp_confidence` | `std_msgs/Int32` | `vision_pipeline` | Line-detection confidence (pts) |
| `/cmd_vel` | `geometry_msgs/Twist` | `visual_servo` | Velocity commands for the differential drive |

### Tuning the Controller

The launch file exposes three parameters you can override on the command line:

```bash
ros2 launch vision_nav camera_view.launch.py Kp:=0.003 linear_x:=0.2 use_vp:=false
```

| Parameter | Default | Effect |
|-----------|---------|--------|
| `Kp` | `0.005` | Proportional gain. Higher = sharper steering response. |
| `linear_x` | `0.3` | Forward speed in m/s. Start low while tuning. |
| `use_vp` | `true` | Use vanishing-point heading when confidence ≥ `min_confidence`. Falls back to histogram otherwise. |

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
