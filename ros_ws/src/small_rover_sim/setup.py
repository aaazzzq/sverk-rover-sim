from glob import glob
import os

from setuptools import find_packages, setup


setup(
    name="small_rover_sim",
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/small_rover_sim"]),
        ("share/small_rover_sim", ["package.xml"]),
        (
            os.path.join("share", "small_rover_sim", "launch"),
            glob(os.path.join("launch", "*.launch.py")),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="sverk",
    maintainer_email="devnull@example.invalid",
    description="Simulation-only ROS adapters and launch files for small_rover.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "cmd_vel_adapter = small_rover_sim.cmd_vel_adapter:main",
            "drone_marker_localization = small_rover_sim.drone_marker_localization:main",
        ],
    },
)
