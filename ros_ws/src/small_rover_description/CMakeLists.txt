cmake_minimum_required(VERSION 3.8)
project(small_rover_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../../models"
  DESTINATION "share/${PROJECT_NAME}"
)

ament_environment_hooks(
  "${CMAKE_CURRENT_SOURCE_DIR}/env-hooks/small_rover_description.dsv.in"
)

ament_package()
