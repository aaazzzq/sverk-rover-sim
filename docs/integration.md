# SITL integration contract

The integrated simulator uses one Gazebo server and two ROS 2 containers.

## Gazebo ownership

The drone SITL container owns Gazebo and the graphical session. The rover
container is headless and attaches through Gazebo Transport. It must not start
another server or expose another noVNC port.

Both containers need:

- The same Docker network
- The same `ROS_DOMAIN_ID`
- `ROS_LOCALHOST_ONLY=0`
- The same `GZ_PARTITION`
- Compatible Fast DDS discovery settings

The Gazebo server image must contain the installed
`small_rover_description` package because mesh and model URIs are resolved by
the server.

## Container installation

An integration image can fetch a pinned repository revision and run:

```bash
bash scripts/build-workspace.sh /opt/small_rover_ws
```

Pin a complete commit SHA. The rover Compose overlay should select this image;
the base SITL image should continue to build without rover dependencies.

## Startup

The drone service starts the selected world. The rover service then runs:

```bash
/usr/local/bin/start-rover-runtime.sh \
  world_name:=<world> \
  entity_name:=small_rover \
  namespace:=small_rover \
  x:=<meters> y:=<meters> z:=0.013 yaw:=<radians> \
  marker_enabled:=true \
  marker_size:=0.08 \
  marker_vocabulary:=DICT_4X4_1000 \
  marker_id:=99
```

`ros_gz_sim create` waits for the world's create service. A restarted service
must not intentionally spawn a second entity with the same name.

The marker is generated as SDF geometry before spawning, so the rover and
Gazebo server containers do not need to share a generated texture. The marker
arguments also accept `ROVER_MARKER_*` environment variables. Keep the
vocabulary and ID synchronized with the drone detector and register the
marker as a moving target rather than adding it to the static world map.

## Shared worlds

Scenario worlds should contain terrain, obstacles, markers and lighting, but
not the drone or rover. Each robot service owns its model and spawn pose.

For ArUco navigation, marker geometry in the world must match the marker map
used by the drone localization launch.

## Frames and topics

The initial interface supports one rover:

- ROS namespace: `/small_rover`
- Gazebo entity: `small_rover`
- Odometry frame: `odom`
- Body frame: `base_link`

A shared coordinator should establish the transform between the scenario
`map` frame and rover odometry. Wheel odometry alone will drift.

## Drone-marker localization

`small_rover_sim` starts `drone_marker_localization` by default. It listens to
the drone's `/aruco/det/markers` and `/aruco/world_pose`, matches the rover
marker ID, and accepts only fresh nonzero marker poses. Their timestamp is the
`MarkerArray` header. It waits for bracketing drone poses and interpolates them
at that timestamp before publishing `/small_rover/vision/pose`,
`/small_rover/vision/odometry`, `/small_rover/vision/valid`, and the debug TF
`<world_pose frame> -> small_rover_vision` (normally
`map -> small_rover_vision`).

The node keeps Gazebo's `base_link` untouched. It uses the marker mounting
values from `ROVER_MARKER_*`, so the generated model and transform stay
synchronized. The SITL rover overlay enables non-map PnP and passes the same
marker ID and size to the drone detector.
