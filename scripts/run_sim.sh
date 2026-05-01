#!/bin/bash
# Launch Gazebo with the crop field world.
# Usage: ./scripts/run_sim.sh [nominal|challenging] [row]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SCENARIO="${1:-nominal}"
ROW="${2:-0}"
WORLD_FILE="$PROJECT_ROOT/worlds/crop_${SCENARIO}.sdf"

echo "[SIM] Generating world for scenario=$SCENARIO, row=$ROW..."
cd "$PROJECT_ROOT" || exit 1
python3 world_generator.py --row "$ROW"

if [ ! -f "$WORLD_FILE" ]; then
    echo "[ERROR] World file not found: $WORLD_FILE"
    echo "Usage: $0 [nominal|challenging] [row]"
    exit 1
fi

echo "[SIM] Launching Gazebo with $SCENARIO scenario, row $ROW..."
gz sim "$WORLD_FILE"
