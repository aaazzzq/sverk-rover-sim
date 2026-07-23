"""Attach the small rover runtime to an existing Gazebo world."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import (
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    world_name = LaunchConfiguration("world_name")
    entity_name = LaunchConfiguration("entity_name")
    namespace = LaunchConfiguration("namespace")
    model_file = PathJoinSubstitution(
        [FindPackageShare("small_rover_description"), "models", "small_rover", "model.sdf"]
    )
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
            Node(
                package="ros_gz_sim",
                executable="create",
                name="spawn_small_rover",
                output="screen",
                condition=IfCondition(LaunchConfiguration("spawn_rover")),
                arguments=[
                    "-world",
                    world_name,
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
            ),
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
