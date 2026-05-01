#!/bin/bash
# Launch Gazebo and the ROS 2 navigation stack in separate terminals.
# Usage: ./run_all.sh [nominal|challenging]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

SCENARIO="${1:-nominal}"

echo "=== Row Navigator ==="
echo "Available starting rows:"
echo "  0 = C2_left  (x=-0.5, y=-1.0, facing +X)"
echo "  1 = C1_inner (x= 9.4, y= 0.0, facing -X)"
echo "  2 = C3_right (x=-0.5, y= 1.0, facing +X)"
echo ""
read -rp "Select starting row (0/1/2): " ROW
ROW="${ROW:-0}"

case "$ROW" in
    0|1|2) ;;
    *) echo "[ERROR] Invalid row '$ROW'. Using default 0."; ROW=0 ;;
esac

echo "[LAUNCH] Starting simulation + navigation stack ($SCENARIO scenario, row $ROW)..."

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

SIM_CMD="cd '$PROJECT_ROOT' && ./scripts/run_sim.sh $SCENARIO $ROW"
ROS_CMD="cd '$PROJECT_ROOT' && ./scripts/run_ros2.sh $ROW"

if run_in_terminal "Gazebo Sim" "$SIM_CMD"; then
    sleep 2
    if run_in_terminal "ROS 2 Nav" "$ROS_CMD"; then
        echo "[LAUNCH] Both terminals opened successfully."
        echo "[LAUNCH] Robot starts at row $ROW. Close either terminal to stop."
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
