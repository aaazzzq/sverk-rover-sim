# sverk-rover-sim

Gazebo Harmonic and ROS 2 simulation package for the `small_rover` mecanum
platform.

## Included

- Dynamic rover model with four driven wheel hubs and 32 passive rollers
- RPLIDAR C1 model with a 360-sample GPU lidar
- Gazebo `MecanumDrive` controller
- ROS 2 bridge and command watchdog
- Standalone Gazebo/noVNC sandbox
- Launch file for attaching the rover to an existing Gazebo world

The model uses REP-103 axes: `+X` forward, `+Y` left and `+Z` up.

## Repository layout

```text
models/                         Gazebo models and meshes
ros_ws/src/
  small_rover_description/      Installs and exports Gazebo assets
  small_rover_sim/              ROS bridge, adapter and launch file
worlds/roller_test.sdf           Standalone development world
docker/                          Sandbox and headless runtime entrypoints
scripts/                         Model generation and build helpers
```

`worlds/roller_test.sdf` is only a model-development sandbox. Shared
drone-rover scenario worlds belong to the simulator's shared world assets and
should spawn the rover at runtime.

## Standalone sandbox

The sandbox requires the local `sverk/ros2:sitl-novnc` image, which provides
ROS 2 Humble, Gazebo Harmonic and noVNC.

```powershell
.\scripts\run-wheel-sandbox.ps1
```

Open `http://localhost:6081/vnc.html`.

Drive the rover from another terminal:

```powershell
docker exec -it small_rover_gz bash
source /opt/ros/humble/setup.bash
source /opt/small_rover_ws/setup.bash
ros2 topic pub --rate 10 /small_rover/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.10}}"
```

Use `linear.y` to strafe and `angular.z` to rotate. Stop the publisher with
`Ctrl+C`; the watchdog sends zero velocity after `0.25 s`.

Stop the sandbox:

```powershell
.\scripts\stop-wheel-sandbox.ps1
```

Models and worlds are mounted from the repository. Rebuild the sandbox after
changing ROS packages or Docker files.

## Install

Build a self-contained ROS installation:

```bash
bash scripts/build-workspace.sh /opt/small_rover_ws
source /opt/small_rover_ws/setup.bash
```

The installed `small_rover_description` package exports its model directory
through `GZ_SIM_RESOURCE_PATH`.

## Existing Gazebo world

With a Gazebo server already running:

```bash
source /opt/ros/humble/setup.bash
source /opt/small_rover_ws/setup.bash
ros2 launch small_rover_sim small_rover.launch.py \
  world_name:=obrik_rover_arena \
  x:=1.0 y:=0.0 z:=0.013 yaw:=0.0 \
  marker_enabled:=true \
  marker_size:=0.08 \
  marker_vocabulary:=DICT_4X4_1000 \
  marker_id:=99
```

The launch file does not start Gazebo. It:

1. Spawns `small_rover` into the named world.
2. Bridges command, odometry, lidar and simulation clock topics.
3. Starts the command watchdog adapter.

Use `spawn_rover:=false` when the world already contains the model. The
headless container entrypoint accepts the same launch arguments:

```bash
/usr/local/bin/start-rover-runtime.sh \
  world_name:=obrik_rover_arena \
  x:=1.0 y:=0.0 z:=0.013
```

## Rover ArUco marker

The launch file can attach an upward-facing `aruco_marker_link` to
`base_link`. It is enabled by default.

| Launch argument | Environment variable | Default |
|---|---|---|
| `marker_enabled` | `ROVER_MARKER_ENABLED` | `true` |
| `marker_size` | `ROVER_MARKER_SIZE` | `0.08` m |
| `marker_vocabulary` | `ROVER_MARKER_VOCABULARY` | `DICT_4X4_1000` |
| `marker_id` | `ROVER_MARKER_ID` | `99` |
| `marker_x`, `marker_y`, `marker_z` | `ROVER_MARKER_X`, `ROVER_MARKER_Y`, `ROVER_MARKER_Z` | `-0.043195`, `0.0`, `0.153` m |
| `marker_yaw` | `ROVER_MARKER_YAW` | `0.0` rad |

`marker_size` is the side length of the encoded black square; the generated
white margin is additional. The vocabulary and ID must match the drone ArUco
detector. Its top edge points toward rover `+X`.

## ROS interface

| Topic | Type | Direction |
|---|---|---|
| `/small_rover/cmd_vel` | `geometry_msgs/msg/Twist` | ROS to rover |
| `/small_rover/odometry` | `nav_msgs/msg/Odometry` | Rover to ROS |
| `/small_rover/lidar/scan` | `sensor_msgs/msg/LaserScan` | Rover to ROS |
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo to ROS |

The default namespace is `/small_rover` and can be changed with
`namespace:=<name>`. Gazebo transport topics remain private behind the adapter.

## Model notes

The first-pass total mass is `1 kg`. Roller collisions use fitted cylinders
instead of concave visual meshes for stable contact simulation. Wheel
odometry, mass, inertia, friction, motor limits and suspension behavior still
require calibration against the physical rover.

Regenerate `models/small_rover/model.sdf` after changing wheel or roller
constants:

```powershell
.\scripts\generate-small-rover-model.ps1
```
