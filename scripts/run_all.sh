#!/bin/bash
# Launch Gazebo and the ROS 2 navigation stack in separate terminals.
# Usage: ./scripts/run_all.sh [nominal|challenging]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SCENARIO="${1:-nominal}"

echo "[LAUNCH] Starting simulation + navigation stack ($SCENARIO scenario)..."

# Try to detect a terminal emulator
run_in_terminal() {
    local TITLE="$1"
    local CMD="$2"

    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="$TITLE" -- bash -c "$CMD; exec bash"
    elif command -v konsole &> /dev/null; then
        konsole --new-tab --title="$TITLE" -e bash -c "$CMD; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -T "$TITLE" -e bash -c "$CMD; exec bash"
    elif command -v terminator &> /dev/null; then
        terminator -T "$TITLE" -e "bash -c '$CMD; exec bash'"
    else
        return 1
    fi
    return 0
}

SIM_CMD="cd '$PROJECT_ROOT' && ./scripts/run_sim.sh $SCENARIO"
ROS_CMD="cd '$PROJECT_ROOT' && ./scripts/run_ros2.sh"

if run_in_terminal "Gazebo Sim" "$SIM_CMD"; then
    sleep 2
    if run_in_terminal "ROS 2 Nav" "$ROS_CMD"; then
        echo "[LAUNCH] Both terminals opened successfully."
        echo "[LAUNCH] Close either terminal to stop that component."
    else
        echo "[ERROR] Could not open a terminal for ROS 2."
        echo "[INFO] Run manually in a second terminal:"
        echo "       $ROS_CMD"
    fi
else
    echo "[ERROR] No supported terminal emulator found (tried: gnome-terminal, konsole, xterm, terminator)."
    echo ""
    echo "[INFO] Please run the two commands manually in separate terminals:"
    echo ""
    echo "  Terminal 1:"
    echo "    $SIM_CMD"
    echo ""
    echo "  Terminal 2:"
    echo "    $ROS_CMD"
    echo ""
fi
