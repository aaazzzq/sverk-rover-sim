#!/usr/bin/env bash
set -euo pipefail

SMALL_ROVER_WS="${SMALL_ROVER_WS:-/opt/small_rover_ws}"

set +u
source /opt/ros/humble/setup.bash
source "${SMALL_ROVER_WS}/setup.bash"
set -u

exec ros2 launch small_rover_sim small_rover.launch.py "$@"
