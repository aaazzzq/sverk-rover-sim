#include <opencv2/aruco.hpp>

#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace
{

const std::unordered_map<std::string, cv::aruco::PREDEFINED_DICTIONARY_NAME> kDictionaries{
  {"DICT_4X4_50", cv::aruco::DICT_4X4_50},
  {"DICT_4X4_100", cv::aruco::DICT_4X4_100},
  {"DICT_4X4_250", cv::aruco::DICT_4X4_250},
  {"DICT_4X4_1000", cv::aruco::DICT_4X4_1000},
  {"DICT_5X5_50", cv::aruco::DICT_5X5_50},
  {"DICT_5X5_100", cv::aruco::DICT_5X5_100},
  {"DICT_5X5_250", cv::aruco::DICT_5X5_250},
  {"DICT_5X5_1000", cv::aruco::DICT_5X5_1000},
  {"DICT_6X6_50", cv::aruco::DICT_6X6_50},
  {"DICT_6X6_100", cv::aruco::DICT_6X6_100},
  {"DICT_6X6_250", cv::aruco::DICT_6X6_250},
  {"DICT_6X6_1000", cv::aruco::DICT_6X6_1000},
  {"DICT_7X7_50", cv::aruco::DICT_7X7_50},
  {"DICT_7X7_100", cv::aruco::DICT_7X7_100},
  {"DICT_7X7_250", cv::aruco::DICT_7X7_250},
  {"DICT_7X7_1000", cv::aruco::DICT_7X7_1000},
  {"DICT_ARUCO_ORIGINAL", cv::aruco::DICT_ARUCO_ORIGINAL},
  {"DICT_APRILTAG_16h5", cv::aruco::DICT_APRILTAG_16h5},
  {"DICT_APRILTAG_25h9", cv::aruco::DICT_APRILTAG_25h9},
  {"DICT_APRILTAG_36h10", cv::aruco::DICT_APRILTAG_36h10},
  {"DICT_APRILTAG_36h11", cv::aruco::DICT_APRILTAG_36h11},
};

}  // namespace

int main(int argc, char ** argv)
{
  if (argc != 3) {
    std::cerr << "Usage: aruco_marker_bits <vocabulary> <marker_id>\n";
    return 2;
  }

  try {
    const std::string vocabulary{argv[1]};
    const auto vocabulary_it = kDictionaries.find(vocabulary);
    if (vocabulary_it == kDictionaries.end()) {
      throw std::invalid_argument("unsupported ArUco vocabulary: " + vocabulary);
    }

    const int marker_id = std::stoi(argv[2]);
    const auto dictionary = cv::aruco::getPredefinedDictionary(vocabulary_it->second);
    if (marker_id < 0 || marker_id >= dictionary->bytesList.rows) {
      throw std::out_of_range(
              "marker ID " + std::to_string(marker_id) + " is outside " + vocabulary +
              " (valid range: 0.." + std::to_string(dictionary->bytesList.rows - 1) + ")");
    }

    const int module_count = dictionary->markerSize + 2;
    cv::Mat marker;
    cv::aruco::drawMarker(dictionary, marker_id, module_count, marker, 1);

    for (int row = 0; row < marker.rows; ++row) {
      for (int col = 0; col < marker.cols; ++col) {
        std::cout << (marker.at<unsigned char>(row, col) > 127 ? '1' : '0');
      }
      std::cout << '\n';
    }
  } catch (const std::exception & error) {
    std::cerr << error.what() << '\n';
    return 1;
  }

  return 0;
}
