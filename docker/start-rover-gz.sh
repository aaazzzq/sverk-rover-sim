#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:99
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
case ":${GZ_SIM_RESOURCE_PATH:-}:" in
    *:/workspace/models:*) ;;
    *) export GZ_SIM_RESOURCE_PATH="/workspace/models${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}" ;;
esac
VNC_RESOLUTION="${VNC_RESOLUTION:-1920x1080x24}"
export XDG_RUNTIME_DIR=/tmp/runtime-root

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
mkdir -p /tmp/.X11-unix
chmod 1777 /tmp/.X11-unix
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

Xvfb "$DISPLAY" -screen 0 "$VNC_RESOLUTION" +extension GLX +render -noreset &
for _ in $(seq 1 50); do
    [ -S /tmp/.X11-unix/X99 ] && break
    sleep 0.2
done

fluxbox >/dev/null 2>&1 &
x11vnc -display "$DISPLAY" -forever -shared -nopw -quiet -bg
websockify --web=/opt/novnc 6080 localhost:5900 >/tmp/novnc.log 2>&1 &

echo "Open http://localhost:6081/vnc.html"
echo "Gazebo resource path: $GZ_SIM_RESOURCE_PATH"

gz sim -s -r /workspace/worlds/roller_test.sdf &
server_pid=$!
rover_runtime_pid=""

cleanup() {
    [ -z "$rover_runtime_pid" ] || kill "$rover_runtime_pid" 2>/dev/null || true
    kill "$server_pid" 2>/dev/null || true
    [ -z "$rover_runtime_pid" ] || wait "$rover_runtime_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 50); do
    gz service -l 2>/dev/null | grep -q '/world/small_rover_drive_test/control' && break
    sleep 0.2
done

/usr/local/bin/start-rover-runtime.sh \
    world_name:=small_rover_drive_test \
    spawn_rover:=false \
    use_sim_time:=true \
    >/tmp/small-rover-runtime.log 2>&1 &
rover_runtime_pid=$!

gz sim -g -v 4
