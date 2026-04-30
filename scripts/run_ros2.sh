#!/bin/bash
# Build (if needed) and launch the vision navigation stack.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WS_DIR="$PROJECT_ROOT/ros2_ws"

if [ ! -d "$WS_DIR" ]; then
    echo "[ERROR] ROS 2 workspace not found at $WS_DIR"
    exit 1
fi

# Source ROS 2
if [ -f "/opt/ros/jazzy/setup.bash" ]; then
    source /opt/ros/jazzy/setup.bash
else
    echo "[ERROR] ROS 2 Jazzy setup.bash not found at /opt/ros/jazzy/setup.bash"
    exit 1
fi

cd "$WS_DIR" || exit 1

# Build if install directory is missing or if source is newer
if [ ! -d "install" ] || [ "$(find src -newer install -print -quit 2>/dev/null)" ]; then
    echo "[ROS2] Building vision_nav package..."
    colcon build --packages-select vision_nav --symlink-install
    if [ $? -ne 0 ]; then
        echo "[ERROR] Build failed"
        exit 1
    fi
else
    echo "[ROS2] Build is up to date, skipping colcon build..."
fi

source "$WS_DIR/install/setup.bash"

echo "[ROS2] Launching vision_nav camera_view.launch.py..."
ros2 launch vision_nav camera_view.launch.py
