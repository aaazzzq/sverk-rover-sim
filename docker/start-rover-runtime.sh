#!/usr/bin/env bash
set -euo pipefail

SMALL_ROVER_WS="${SMALL_ROVER_WS:-/opt/small_rover_ws}"

set +u
source /opt/ros/humble/setup.bash
if [ -f /home/sverk/sverk_ws/install/setup.bash ]; then
    source /home/sverk/sverk_ws/install/setup.bash
fi
source "${SMALL_ROVER_WS}/setup.bash"
set -u

exec ros2 launch small_rover_sim small_rover.launch.py "$@"
