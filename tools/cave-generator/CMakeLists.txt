cmake_minimum_required(VERSION 3.16)
project(CaveGenerator LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
get_filename_component(SDK_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
add_executable(cave_generator
  "${SDK_ROOT}/engine/tools/p2_cave_generator_test.cpp"
  "${SDK_ROOT}/engine/pc_port/pc_p2_cave_generator.cpp")
target_include_directories(cave_generator PRIVATE "${SDK_ROOT}/engine/pc_port")
