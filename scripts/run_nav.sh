#!/bin/bash
# Interactive CLI to send row-navigation commands.
# Usage: ./scripts/run_nav.sh

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
    echo "[ERROR] ROS 2 Jazzy setup.bash not found"
    exit 1
fi

source "$WS_DIR/install/setup.bash"

echo "[NAV] Starting row navigator CLI..."
echo "[NAV] Publish Int32 messages to /target_row (0=C2_left, 1=C1_inner, 2=C3_right)"
echo ""
ros2 run vision_nav navigate_cli
