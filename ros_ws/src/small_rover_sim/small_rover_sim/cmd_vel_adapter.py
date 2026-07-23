"""Bridge public small_rover ROS commands to Gazebo with a command watchdog."""

from __future__ import annotations

import time

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node


class CmdVelAdapter(Node):
    """Publish safe Gazebo commands and relay wheel odometry in REP-103 axes."""

    def __init__(self) -> None:
        super().__init__("small_rover_cmd_vel_adapter")
        self.declare_parameter("command_timeout_s", 0.25)
        self._timeout = float(self.get_parameter("command_timeout_s").value)
        self._last_command = Twist()
        self._last_command_at: float | None = None

        self._gz_command_publisher = self.create_publisher(
            Twist, "internal/gz_cmd_vel", 10
        )
        self._odom_publisher = self.create_publisher(
            Odometry, "odometry", 10
        )
        self.create_subscription(Twist, "cmd_vel", self._on_command, 10)
        self.create_subscription(
            Odometry, "internal/gz_odometry", self._on_gz_odometry, 10
        )
        self.create_timer(0.05, self._publish_command)

    def _on_command(self, message: Twist) -> None:
        self._last_command = message
        self._last_command_at = time.monotonic()

    def _publish_command(self) -> None:
        command = Twist()
        if self._last_command_at is None:
            self._gz_command_publisher.publish(command)
            return

        if time.monotonic() - self._last_command_at > self._timeout:
            self._gz_command_publisher.publish(command)
            return

        # The generated rover model uses REP-103: +X forward and +Y left.
        # Gazebo's wheel-velocity convention is reversed only longitudinally.
        command.linear.x = -self._last_command.linear.x
        command.linear.y = self._last_command.linear.y
        command.angular.z = self._last_command.angular.z
        self._gz_command_publisher.publish(command)

    def _on_gz_odometry(self, message: Odometry) -> None:
        odometry = Odometry()
        odometry.header = message.header
        odometry.child_frame_id = message.child_frame_id
        odometry.pose = message.pose
        odometry.twist = message.twist
        odometry.pose.pose.position.x = -message.pose.pose.position.x
        odometry.twist.twist.linear.x = -message.twist.twist.linear.x
        self._odom_publisher.publish(odometry)


def main() -> None:
    rclpy.init()
    node = CmdVelAdapter()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
