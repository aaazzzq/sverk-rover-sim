"""Attach the small rover runtime to an existing Gazebo world."""

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, SetEnvironmentVariable
from launch.substitutions import (
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from small_rover_sim.marker_model import create_marker_model


def _as_bool(value):
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _spawn_rover(context):
    if not _as_bool(LaunchConfiguration("spawn_rover").perform(context)):
        return []

    entity_name = LaunchConfiguration("entity_name").perform(context)
    model_file = (
        get_package_share_directory("small_rover_description")
        + "/models/small_rover/model.sdf"
    )
    if _as_bool(LaunchConfiguration("marker_enabled").perform(context)):
        model_file = create_marker_model(
            source_path=model_file,
            entity_name=entity_name,
            marker_size=float(LaunchConfiguration("marker_size").perform(context)),
            vocabulary=LaunchConfiguration("marker_vocabulary").perform(context),
            marker_id=int(LaunchConfiguration("marker_id").perform(context)),
            marker_x=float(LaunchConfiguration("marker_x").perform(context)),
            marker_y=float(LaunchConfiguration("marker_y").perform(context)),
            marker_z=float(LaunchConfiguration("marker_z").perform(context)),
            marker_yaw=float(LaunchConfiguration("marker_yaw").perform(context)),
        )

    return [
        Node(
            package="ros_gz_sim",
            executable="create",
            name="spawn_small_rover",
            output="screen",
            arguments=[
                "-world",
                LaunchConfiguration("world_name"),
                "-name",
                entity_name,
                "-file",
                model_file,
                "-x",
                LaunchConfiguration("x"),
                "-y",
                LaunchConfiguration("y"),
                "-z",
                LaunchConfiguration("z"),
                "-Y",
                LaunchConfiguration("yaw"),
            ],
        )
    ]


def generate_launch_description() -> LaunchDescription:
    namespace = LaunchConfiguration("namespace")
    model_path = PathJoinSubstitution(
        [FindPackageShare("small_rover_description"), "models"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world_name", description="Name of the running Gazebo world."
            ),
            DeclareLaunchArgument(
                "entity_name",
                default_value="small_rover",
                description="Gazebo entity name.",
            ),
            DeclareLaunchArgument(
                "namespace",
                default_value="small_rover",
                description="ROS namespace for rover topics and nodes.",
            ),
            DeclareLaunchArgument(
                "spawn_rover",
                default_value="true",
                description="Spawn the model before starting its ROS runtime.",
            ),
            DeclareLaunchArgument("x", default_value="0.0", description="Spawn X in m."),
            DeclareLaunchArgument("y", default_value="0.0", description="Spawn Y in m."),
            DeclareLaunchArgument(
                "z", default_value="0.013", description="Spawn Z in m."
            ),
            DeclareLaunchArgument(
                "yaw", default_value="0.0", description="Spawn yaw in rad."
            ),
            DeclareLaunchArgument(
                "marker_enabled",
                default_value=EnvironmentVariable(
                    "ROVER_MARKER_ENABLED", default_value="true"
                ),
                description="Attach an upward-facing ArUco marker to the rover.",
            ),
            DeclareLaunchArgument(
                "marker_size",
                default_value=EnvironmentVariable(
                    "ROVER_MARKER_SIZE", default_value="0.08"
                ),
                description="ArUco code side length in metres, excluding its white margin.",
            ),
            DeclareLaunchArgument(
                "marker_vocabulary",
                default_value=EnvironmentVariable(
                    "ROVER_MARKER_VOCABULARY", default_value="DICT_4X4_1000"
                ),
                description="OpenCV predefined ArUco vocabulary name.",
            ),
            DeclareLaunchArgument(
                "marker_id",
                default_value=EnvironmentVariable(
                    "ROVER_MARKER_ID", default_value="99"
                ),
                description="Marker ID within marker_vocabulary.",
            ),
            DeclareLaunchArgument(
                "marker_x",
                default_value=EnvironmentVariable(
                    "ROVER_MARKER_X", default_value="-0.043195"
                ),
                description="Marker centre X relative to base_link in metres.",
            ),
            DeclareLaunchArgument(
                "marker_y",
                default_value=EnvironmentVariable(
                    "ROVER_MARKER_Y", default_value="0.0"
                ),
                description="Marker centre Y relative to base_link in metres.",
            ),
            DeclareLaunchArgument(
                "marker_z",
                default_value=EnvironmentVariable(
                    "ROVER_MARKER_Z", default_value="0.153"
                ),
                description="Marker centre Z relative to base_link in metres.",
            ),
            DeclareLaunchArgument(
                "marker_yaw",
                default_value=EnvironmentVariable(
                    "ROVER_MARKER_YAW", default_value="0.0"
                ),
                description="Marker yaw relative to base_link in radians.",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use the Gazebo simulation clock.",
            ),
            DeclareLaunchArgument(
                "command_timeout_s",
                default_value="0.25",
                description="Stop after this interval without a velocity command.",
            ),
            SetEnvironmentVariable(
                "GZ_SIM_RESOURCE_PATH",
                [
                    model_path,
                    ":",
                    EnvironmentVariable("GZ_SIM_RESOURCE_PATH", default_value=""),
                ],
            ),
            OpaqueFunction(function=_spawn_rover),
            Node(
                package="ros_gz_bridge",
                executable="parameter_bridge",
                name="small_rover_bridge",
                namespace=namespace,
                output="screen",
                arguments=[
                    "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
                    "/small_rover/gz_cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
                    "/small_rover/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
                    "/small_rover/lidar/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
                ],
                remappings=[
                    ("/small_rover/gz_cmd_vel", "internal/gz_cmd_vel"),
                    ("/small_rover/odometry", "internal/gz_odometry"),
                    ("/small_rover/lidar/scan", "lidar/scan"),
                ],
            ),
            Node(
                package="small_rover_sim",
                executable="cmd_vel_adapter",
                name="cmd_vel_adapter",
                namespace=namespace,
                output="screen",
                parameters=[
                    {
                        "command_timeout_s": LaunchConfiguration("command_timeout_s"),
                        "use_sim_time": LaunchConfiguration("use_sim_time"),
                    }
                ],
            ),
        ]
    )
