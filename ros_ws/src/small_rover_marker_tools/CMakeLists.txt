cmake_minimum_required(VERSION 3.8)
project(small_rover_marker_tools)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(OpenCV REQUIRED)

add_executable(aruco_marker_bits src/aruco_marker_bits.cpp)
target_link_libraries(aruco_marker_bits ${OpenCV_LIBS} opencv_aruco)

install(TARGETS aruco_marker_bits
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
