# The local SVERK SITL image already provides ROS 2 Humble, ros_gzharmonic,
# Gazebo Harmonic and noVNC. Reusing it avoids a fragile second set of APT
# downloads for the rover sandbox.
ARG BASE_IMAGE=sverk/ros2:sitl-novnc
FROM ${BASE_IMAGE}

USER root

ENV LIBGL_ALWAYS_SOFTWARE=1

COPY docker/start-rover-gz.sh /usr/local/bin/start-rover-gz.sh
COPY docker/start-rover-runtime.sh /usr/local/bin/start-rover-runtime.sh
RUN sed -i 's/\r$//' /usr/local/bin/start-rover-gz.sh && \
    sed -i 's/\r$//' /usr/local/bin/start-rover-runtime.sh && \
    chmod +x /usr/local/bin/start-rover-gz.sh /usr/local/bin/start-rover-runtime.sh

COPY models /tmp/sverk-rover-sim/models
COPY ros_ws /tmp/sverk-rover-sim/ros_ws
RUN bash -lc 'source /opt/ros/humble/setup.bash && \
    colcon --log-base /tmp/sverk-rover-log build \
      --base-paths /tmp/sverk-rover-sim/ros_ws/src \
      --build-base /tmp/sverk-rover-build \
      --install-base /opt/small_rover_ws \
      --merge-install' && \
    rm -rf /tmp/sverk-rover-sim /tmp/sverk-rover-build /tmp/sverk-rover-log

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/start-rover-gz.sh"]
