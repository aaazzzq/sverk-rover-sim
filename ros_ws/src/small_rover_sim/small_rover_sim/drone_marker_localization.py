"""Localize small_rover from the drone camera's moving ArUco-marker pose."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
import time
from typing import Deque, Optional

from aruco_det_loc.msg import MarkerArray
from geometry_msgs.msg import Pose, PoseWithCovarianceStamped, Transform, TransformStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from std_msgs.msg import Bool
from tf2_ros import Buffer, TransformBroadcaster, TransformException, TransformListener


Vector3 = tuple[float, float, float]
Quaternion = tuple[float, float, float, float]


@dataclass(frozen=True)
class RigidTransform:
    translation: Vector3
    rotation: Quaternion


@dataclass(frozen=True)
class DronePoseSample:
    stamp_ns: int
    frame_id: str
    transform: RigidTransform
    covariance: tuple[float, ...]


@dataclass(frozen=True)
class PendingMarkerObservation:
    stamp_ns: int
    camera_frame: str
    camera_to_marker: RigidTransform


def _stamp_ns(stamp) -> int:
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def _has_fresh_pnp_pose(pose: Pose) -> bool:
    quaternion = (
        pose.orientation.x,
        pose.orientation.y,
        pose.orientation.z,
        pose.orientation.w,
    )
    return all(math.isfinite(component) for component in quaternion) and (
        sum(component * component for component in quaternion) > 1e-12
    )


def _normalise_quaternion(q: Quaternion) -> Quaternion:
    norm = math.sqrt(sum(component * component for component in q))
    if norm < 1e-12:
        return (0.0, 0.0, 0.0, 1.0)
    return tuple(component / norm for component in q)  # type: ignore[return-value]


def _quaternion_multiply(first: Quaternion, second: Quaternion) -> Quaternion:
    x1, y1, z1, w1 = first
    x2, y2, z2, w2 = second
    return _normalise_quaternion(
        (
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        )
    )


def _quaternion_inverse(q: Quaternion) -> Quaternion:
    x, y, z, w = _normalise_quaternion(q)
    return (-x, -y, -z, w)


def _rotate(q: Quaternion, vector: Vector3) -> Vector3:
    x, y, z, w = _normalise_quaternion(q)
    vx, vy, vz = vector
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (
        vx + w * tx + y * tz - z * ty,
        vy + w * ty + z * tx - x * tz,
        vz + w * tz + x * ty - y * tx,
    )


def _compose(first: RigidTransform, second: RigidTransform) -> RigidTransform:
    offset = _rotate(first.rotation, second.translation)
    return RigidTransform(
        (
            first.translation[0] + offset[0],
            first.translation[1] + offset[1],
            first.translation[2] + offset[2],
        ),
        _quaternion_multiply(first.rotation, second.rotation),
    )


def _inverse(transform: RigidTransform) -> RigidTransform:
    rotation = _quaternion_inverse(transform.rotation)
    tx, ty, tz = _rotate(rotation, transform.translation)
    return RigidTransform((-tx, -ty, -tz), rotation)


def _from_pose(pose: Pose) -> RigidTransform:
    return RigidTransform(
        (pose.position.x, pose.position.y, pose.position.z),
        _normalise_quaternion(
            (pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w)
        ),
    )


def _from_transform(transform: Transform) -> RigidTransform:
    return RigidTransform(
        (transform.translation.x, transform.translation.y, transform.translation.z),
        _normalise_quaternion(
            (transform.rotation.x, transform.rotation.y, transform.rotation.z, transform.rotation.w)
        ),
    )


def _to_pose(transform: RigidTransform) -> Pose:
    pose = Pose()
    pose.position.x, pose.position.y, pose.position.z = transform.translation
    (
        pose.orientation.x,
        pose.orientation.y,
        pose.orientation.z,
        pose.orientation.w,
    ) = transform.rotation
    return pose


def _slerp(first: Quaternion, second: Quaternion, alpha: float) -> Quaternion:
    q1 = _normalise_quaternion(first)
    q2 = _normalise_quaternion(second)
    dot = sum(a * b for a, b in zip(q1, q2))
    if dot < 0.0:
        q2 = tuple(-component for component in q2)  # type: ignore[assignment]
        dot = -dot
    if dot > 0.9995:
        return _normalise_quaternion(
            tuple(a + alpha * (b - a) for a, b in zip(q1, q2))  # type: ignore[arg-type]
        )
    theta = math.acos(max(-1.0, min(1.0, dot)))
    sin_theta = math.sin(theta)
    first_weight = math.sin((1.0 - alpha) * theta) / sin_theta
    second_weight = math.sin(alpha * theta) / sin_theta
    return _normalise_quaternion(
        tuple(first_weight * a + second_weight * b for a, b in zip(q1, q2))  # type: ignore[arg-type]
    )


class DroneMarkerLocalization(Node):
    """Compose drone map pose, camera extrinsics and rover tag pose."""

    def __init__(self) -> None:
        super().__init__("small_rover_drone_marker_localization")

        self.declare_parameter("marker_id", 99)
        self.declare_parameter("marker_x", -0.043195)
        self.declare_parameter("marker_y", 0.0)
        self.declare_parameter("marker_z", 0.153)
        self.declare_parameter("marker_yaw", 0.0)
        self.declare_parameter("marker_coordinate_yaw_offset", -math.pi / 2.0)
        self.declare_parameter("drone_base_frame", "base_link")
        self.declare_parameter("camera_frame", "camera_optical_1")
        self.declare_parameter("vision_frame", "small_rover_vision")
        self.declare_parameter("markers_topic", "/aruco/det/markers")
        self.declare_parameter("drone_world_pose_topic", "/aruco/world_pose")
        self.declare_parameter("pose_buffer_s", 2.0)
        self.declare_parameter("observation_timeout_s", 0.5)
        self.declare_parameter("measurement_timeout_s", 0.5)
        self.declare_parameter("position_stddev_floor", 0.03)
        self.declare_parameter("position_stddev_per_meter", 0.02)
        self.declare_parameter("z_stddev_floor", 0.06)
        self.declare_parameter("angle_stddev", 0.15)

        self._marker_id = int(self.get_parameter("marker_id").value)
        self._marker_x = float(self.get_parameter("marker_x").value)
        self._marker_y = float(self.get_parameter("marker_y").value)
        self._marker_z = float(self.get_parameter("marker_z").value)
        self._marker_yaw = float(self.get_parameter("marker_yaw").value)
        self._marker_coordinate_yaw_offset = float(
            self.get_parameter("marker_coordinate_yaw_offset").value
        )
        self._drone_base_frame = str(self.get_parameter("drone_base_frame").value)
        self._default_camera_frame = str(self.get_parameter("camera_frame").value)
        self._vision_frame = str(self.get_parameter("vision_frame").value)
        self._observation_timeout_ns = int(
            float(self.get_parameter("observation_timeout_s").value) * 1_000_000_000
        )
        self._measurement_timeout_ns = int(
            float(self.get_parameter("measurement_timeout_s").value) * 1_000_000_000
        )
        self._pose_buffer_ns = int(
            float(self.get_parameter("pose_buffer_s").value) * 1_000_000_000
        )
        self._position_stddev_floor = float(
            self.get_parameter("position_stddev_floor").value
        )
        self._position_stddev_per_meter = float(
            self.get_parameter("position_stddev_per_meter").value
        )
        self._z_stddev_floor = float(self.get_parameter("z_stddev_floor").value)
        self._angle_stddev = float(self.get_parameter("angle_stddev").value)

        self._drone_poses: Deque[DronePoseSample] = deque()
        self._pending_observations: Deque[PendingMarkerObservation] = deque()
        self._camera_extrinsics: dict[str, RigidTransform] = {}
        self._last_measurement_ns: Optional[int] = None
        self._last_warning_at: dict[str, float] = {}

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._tf_broadcaster = TransformBroadcaster(self)

        self._pose_publisher = self.create_publisher(
            PoseWithCovarianceStamped, "vision/pose", 10
        )
        self._odometry_publisher = self.create_publisher(Odometry, "vision/odometry", 10)
        self._valid_publisher = self.create_publisher(Bool, "vision/valid", 1)
        self.create_subscription(
            MarkerArray,
            str(self.get_parameter("markers_topic").value),
            self._on_markers,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            PoseWithCovarianceStamped,
            str(self.get_parameter("drone_world_pose_topic").value),
            self._on_drone_pose,
            qos_profile_sensor_data,
        )
        self.create_timer(0.2, self._publish_validity)

        self.get_logger().info(
            "Waiting for moving ArUco marker %d on %s"
            % (self._marker_id, self.get_parameter("markers_topic").value)
        )

    def _warn_throttled(self, key: str, message: str) -> None:
        now = time.monotonic()
        if now - self._last_warning_at.get(key, float("-inf")) >= 5.0:
            self.get_logger().warning(message)
            self._last_warning_at[key] = now

    def _on_drone_pose(self, message: PoseWithCovarianceStamped) -> None:
        frame_id = message.header.frame_id.strip()
        if not frame_id:
            self._warn_throttled("world-frame", "Ignoring /aruco/world_pose without frame_id")
            return

        sample = DronePoseSample(
            stamp_ns=_stamp_ns(message.header.stamp),
            frame_id=frame_id,
            transform=_from_pose(message.pose.pose),
            covariance=tuple(message.pose.covariance),
        )
        if self._drone_poses:
            previous = self._drone_poses[-1]
            if previous.frame_id != sample.frame_id:
                self._drone_poses.clear()
                self._pending_observations.clear()
                self._warn_throttled(
                    "world-frame-change",
                    "The drone localization frame changed; cleared pending observations",
                )
            elif sample.stamp_ns == previous.stamp_ns:
                self._drone_poses[-1] = sample
                self._publish_ready_observations(sample.stamp_ns)
                return
            elif sample.stamp_ns < previous.stamp_ns:
                self._drone_poses.clear()
                self._pending_observations.clear()
                self._warn_throttled(
                    "world-time-reset",
                    "Drone localization time moved backwards; cleared pending observations",
                )

        self._drone_poses.append(sample)
        cutoff_ns = sample.stamp_ns - self._pose_buffer_ns
        while self._drone_poses and self._drone_poses[0].stamp_ns < cutoff_ns:
            self._drone_poses.popleft()
        self._publish_ready_observations(sample.stamp_ns)

    def _on_markers(self, message: MarkerArray) -> None:
        marker = next((item for item in message.markers if item.id == self._marker_id), None)
        if marker is None:
            return

        if not _has_fresh_pnp_pose(marker.pose):
            self.get_logger().debug(
                "Rover marker sample does not contain a fresh PnP pose"
            )
            return

        stamp_ns = _stamp_ns(message.header.stamp)
        if stamp_ns == 0:
            self._warn_throttled(
                "missing-pnp-stamp",
                "Ignoring rover marker pose without a message timestamp",
            )
            return
        camera_frame = message.header.frame_id.strip() or self._default_camera_frame
        self._pending_observations.append(
            PendingMarkerObservation(
                stamp_ns=stamp_ns,
                camera_frame=camera_frame,
                camera_to_marker=_from_pose(marker.pose),
            )
        )
        self._publish_ready_observations(stamp_ns)

    def _publish_ready_observations(self, reference_stamp_ns: int) -> None:
        pending: Deque[PendingMarkerObservation] = deque()
        for observation in self._pending_observations:
            pose_sample = self._drone_pose_at(observation.stamp_ns)
            if pose_sample is None:
                if reference_stamp_ns - observation.stamp_ns > self._observation_timeout_ns:
                    self._warn_throttled(
                        "drone-pose-timeout",
                        "Dropping rover marker pose without bracketing /aruco/world_pose samples",
                    )
                else:
                    pending.append(observation)
                continue

            base_to_camera = self._base_to_camera(observation.camera_frame)
            if base_to_camera is None:
                if reference_stamp_ns - observation.stamp_ns > self._observation_timeout_ns:
                    self._warn_throttled(
                        "camera-extrinsic-timeout",
                        "Dropping rover marker pose before its camera extrinsic became available",
                    )
                else:
                    pending.append(observation)
                continue

            map_to_rover = _compose(
                _compose(
                    _compose(pose_sample.transform, base_to_camera),
                    observation.camera_to_marker,
                ),
                _inverse(self._base_to_marker()),
            )
            self._publish_measurement(
                stamp=Time(nanoseconds=observation.stamp_ns).to_msg(),
                frame_id=pose_sample.frame_id,
                transform=map_to_rover,
                drone_covariance=pose_sample.covariance,
                camera_to_marker=observation.camera_to_marker,
            )
            self._last_measurement_ns = observation.stamp_ns
        self._pending_observations = pending

    def _base_to_marker(self) -> RigidTransform:
        # OpenCV's marker axes differ from the generated SDF link axes: marker
        # +X points toward rover -Y and marker +Y toward rover +X.
        yaw = self._marker_yaw + self._marker_coordinate_yaw_offset
        half_yaw = yaw * 0.5
        return RigidTransform(
            (self._marker_x, self._marker_y, self._marker_z),
            (0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw)),
        )

    def _base_to_camera(self, camera_frame: str) -> Optional[RigidTransform]:
        cached = self._camera_extrinsics.get(camera_frame)
        if cached is not None:
            return cached

        candidates = [camera_frame]
        if self._default_camera_frame not in candidates:
            candidates.append(self._default_camera_frame)

        transform = None
        errors = []
        resolved_frame = camera_frame
        for candidate in candidates:
            try:
                transform = self._tf_buffer.lookup_transform(
                    self._drone_base_frame,
                    candidate,
                    Time(),
                    timeout=Duration(seconds=0.05),
                )
                resolved_frame = candidate
                break
            except TransformException as error:
                errors.append("%s: %s" % (candidate, error))

        if transform is None:
            self._warn_throttled(
                "camera-extrinsic",
                "Waiting for camera extrinsic from %s: %s"
                % (self._drone_base_frame, "; ".join(errors)),
            )
            return None

        extrinsic = _from_transform(transform.transform)
        self._camera_extrinsics[camera_frame] = extrinsic
        self.get_logger().info(
            "Using camera extrinsic %s -> %s%s"
            % (
                self._drone_base_frame,
                resolved_frame,
                " for messages labelled %s" % camera_frame
                if resolved_frame != camera_frame
                else "",
            )
        )
        return extrinsic

    def _drone_pose_at(self, stamp_ns: int) -> Optional[DronePoseSample]:
        if not self._drone_poses:
            return None

        samples = list(self._drone_poses)
        if stamp_ns < samples[0].stamp_ns or stamp_ns > samples[-1].stamp_ns:
            return None
        if stamp_ns == samples[0].stamp_ns:
            return samples[0]

        for previous, following in zip(samples, samples[1:]):
            if stamp_ns == following.stamp_ns:
                return following
            if not previous.stamp_ns < stamp_ns < following.stamp_ns:
                continue
            if previous.frame_id != following.frame_id:
                return None
            interval_ns = following.stamp_ns - previous.stamp_ns
            alpha = (stamp_ns - previous.stamp_ns) / interval_ns
            translation = tuple(
                start + alpha * (end - start)
                for start, end in zip(
                    previous.transform.translation, following.transform.translation
                )
            )
            covariance = tuple(
                start + alpha * (end - start)
                for start, end in zip(previous.covariance, following.covariance)
            )
            return DronePoseSample(
                stamp_ns=stamp_ns,
                frame_id=previous.frame_id,
                transform=RigidTransform(
                    translation,  # type: ignore[arg-type]
                    _slerp(previous.transform.rotation, following.transform.rotation, alpha),
                ),
                covariance=covariance,
            )
        return None

    def _publish_measurement(
        self,
        stamp,
        frame_id: str,
        transform: RigidTransform,
        drone_covariance: tuple[float, ...],
        camera_to_marker: RigidTransform,
    ) -> None:
        pose = _to_pose(transform)
        covariance = self._covariance(drone_covariance, camera_to_marker)

        pose_message = PoseWithCovarianceStamped()
        pose_message.header.stamp = stamp
        pose_message.header.frame_id = frame_id
        pose_message.pose.pose = pose
        pose_message.pose.covariance = covariance
        self._pose_publisher.publish(pose_message)

        odometry = Odometry()
        odometry.header = pose_message.header
        odometry.child_frame_id = self._vision_frame
        odometry.pose = pose_message.pose
        odometry.twist.covariance[0] = -1.0
        self._odometry_publisher.publish(odometry)

        vision_tf = TransformStamped()
        vision_tf.header = pose_message.header
        vision_tf.child_frame_id = self._vision_frame
        vision_tf.transform.translation.x = transform.translation[0]
        vision_tf.transform.translation.y = transform.translation[1]
        vision_tf.transform.translation.z = transform.translation[2]
        vision_tf.transform.rotation = pose.orientation
        self._tf_broadcaster.sendTransform(vision_tf)

    def _covariance(
        self, drone_covariance: tuple[float, ...], camera_to_marker: RigidTransform
    ) -> list[float]:
        distance = math.sqrt(sum(value * value for value in camera_to_marker.translation))
        position_stddev = self._position_stddev_floor + (
            self._position_stddev_per_meter * distance
        )
        variances = [0.0] * 36
        drone_x = max(0.0, drone_covariance[0]) if len(drone_covariance) == 36 else 0.0
        drone_y = max(0.0, drone_covariance[7]) if len(drone_covariance) == 36 else 0.0
        drone_z = max(0.0, drone_covariance[14]) if len(drone_covariance) == 36 else 0.0
        drone_roll = max(0.0, drone_covariance[21]) if len(drone_covariance) == 36 else 0.0
        drone_pitch = max(0.0, drone_covariance[28]) if len(drone_covariance) == 36 else 0.0
        drone_yaw = max(0.0, drone_covariance[35]) if len(drone_covariance) == 36 else 0.0
        variances[0] = drone_x + position_stddev * position_stddev
        variances[7] = drone_y + position_stddev * position_stddev
        variances[14] = drone_z + self._z_stddev_floor * self._z_stddev_floor
        variances[21] = drone_roll + self._angle_stddev * self._angle_stddev
        variances[28] = drone_pitch + self._angle_stddev * self._angle_stddev
        variances[35] = drone_yaw + self._angle_stddev * self._angle_stddev
        return variances

    def _publish_validity(self) -> None:
        now_ns = self.get_clock().now().nanoseconds
        valid = (
            self._last_measurement_ns is not None
            and 0 <= now_ns - self._last_measurement_ns <= self._measurement_timeout_ns
        )
        self._valid_publisher.publish(Bool(data=valid))


def main() -> None:
    rclpy.init()
    node = DroneMarkerLocalization()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
