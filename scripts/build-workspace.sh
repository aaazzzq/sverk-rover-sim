#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
install_base="${1:-${repo_root}/install}"
build_base="${BUILD_BASE:-${repo_root}/build}"
log_base="${LOG_BASE:-${repo_root}/log}"

set +u
source "${ROS_SETUP:-/opt/ros/humble/setup.bash}"
set -u

colcon --log-base "${log_base}" build \
    --base-paths "${repo_root}/ros_ws/src" \
    --build-base "${build_base}" \
    --install-base "${install_base}" \
    --merge-install
