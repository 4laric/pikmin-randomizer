cmake_minimum_required(VERSION 3.20)
project(OriginalResourceProviderChecks LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
get_filename_component(RESOURCE_SOURCE "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
# Additive private producer harness. Shared production CMake/dispatch remain
# with the startup owner. Explicitly links the real native adapter into engine.
add_subdirectory("${RESOURCE_SOURCE}" engine)
add_executable(p2_original_gas_policy
 "${RESOURCE_SOURCE}/tools/p2_original_gas_test.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_gas.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_spawn_plan.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_group.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_actor.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_catalog.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_lifecycle.cpp")
add_executable(p2_original_wisp_policy
 "${RESOURCE_SOURCE}/tools/pc_p2_original_wisp_test.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_wisp.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_spawn_plan.cpp")
add_executable(p2_original_egg_contents_policy
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_resource_contents_test.cpp")
add_executable(p2_original_egg_policy
 "${RESOURCE_SOURCE}/tools/p2_original_egg_test.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_egg.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_spawn_plan.cpp")
add_executable(p2_original_gas_links_policy
 "${RESOURCE_SOURCE}/tools/p2_original_gas_links_test.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_gas_links.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_gas.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_spawn_plan.cpp")
add_executable(p2_original_gas_save_policy
 "${RESOURCE_SOURCE}/tools/p2_original_gas_save_test.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_gas_save.cpp")
add_executable(p2_original_resource_state_policy
 "${RESOURCE_SOURCE}/tools/p2_original_resource_state_test.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_resource_state.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_resource_contents.cpp")
add_executable(p2_original_resource_save_policy
 "${RESOURCE_SOURCE}/tools/p2_original_resource_save_test.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_resource_save.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_resource_state.cpp"
 "${RESOURCE_SOURCE}/pc_port/pc_p2_original_resource_contents.cpp")
add_executable(p2_original_wisp_clock_policy "${RESOURCE_SOURCE}/tools/p2_original_wisp_clock_test.cpp")
add_executable(p2_original_egg_snapshot_policy "${RESOURCE_SOURCE}/tools/p2_original_egg_snapshot_test.cpp" "${RESOURCE_SOURCE}/pc_port/pc_p2_original_egg_snapshot.cpp")
add_executable(p2_original_wisp_snapshot_policy "${RESOURCE_SOURCE}/tools/p2_original_wisp_snapshot_test.cpp")
add_executable(p2_original_honey_policy "${RESOURCE_SOURCE}/pc_port/pc_p2_original_honey_policy_test.cpp")
add_executable(p2_original_honey_bank_policy "${RESOURCE_SOURCE}/pc_port/pc_p2_original_honey_bank_validation_test.cpp")
add_executable(p2_original_contents_save_policy "${RESOURCE_SOURCE}/tools/p2_original_contents_save_test.cpp" "${RESOURCE_SOURCE}/pc_port/pc_p2_original_contents_save.cpp" "${RESOURCE_SOURCE}/pc_port/pc_p2_original_resource_contents.cpp")
add_executable(p2_original_egg_save_policy "${RESOURCE_SOURCE}/tools/p2_original_egg_save_test.cpp" "${RESOURCE_SOURCE}/pc_port/pc_p2_original_egg_save.cpp" "${RESOURCE_SOURCE}/pc_port/pc_p2_original_egg_snapshot.cpp" "${RESOURCE_SOURCE}/pc_port/pc_p2_original_resource_contents.cpp")
add_executable(p2_original_wisp_save_policy "${RESOURCE_SOURCE}/tools/p2_original_wisp_save_test.cpp" "${RESOURCE_SOURCE}/pc_port/pc_p2_original_wisp_save.cpp")
add_executable(p2_original_honey_save_policy "${RESOURCE_SOURCE}/pc_port/pc_p2_original_honey_save_test.cpp" "${RESOURCE_SOURCE}/pc_port/pc_p2_original_honey_save.cpp" "${RESOURCE_SOURCE}/pc_port/pc_p2_original_resource_contents.cpp")
foreach(target p2_original_gas_policy p2_original_wisp_policy p2_original_egg_contents_policy p2_original_egg_policy p2_original_gas_links_policy p2_original_gas_save_policy p2_original_resource_state_policy p2_original_resource_save_policy p2_original_wisp_clock_policy p2_original_egg_snapshot_policy p2_original_wisp_snapshot_policy p2_original_honey_policy p2_original_honey_bank_policy p2_original_contents_save_policy p2_original_egg_save_policy p2_original_wisp_save_policy p2_original_honey_save_policy)
 target_include_directories(${target} PRIVATE "${RESOURCE_SOURCE}/pc_port")
 target_compile_options(${target} PRIVATE -Wall -Wextra -Werror -UNDEBUG)
endforeach()
enable_testing()
add_test(NAME original_gas_policy COMMAND p2_original_gas_policy)
add_test(NAME original_wisp_policy COMMAND p2_original_wisp_policy)
add_test(NAME original_egg_contents_policy COMMAND p2_original_egg_contents_policy)
add_test(NAME original_egg_policy COMMAND p2_original_egg_policy)
add_test(NAME original_gas_links_policy COMMAND p2_original_gas_links_policy)
add_test(NAME original_gas_save_policy COMMAND p2_original_gas_save_policy)
add_test(NAME original_resource_state_policy COMMAND p2_original_resource_state_policy)
add_test(NAME original_resource_save_policy COMMAND p2_original_resource_save_policy)
add_test(NAME original_wisp_clock_policy COMMAND p2_original_wisp_clock_policy)
add_test(NAME original_egg_snapshot_policy COMMAND p2_original_egg_snapshot_policy)
add_test(NAME original_wisp_snapshot_policy COMMAND p2_original_wisp_snapshot_policy)
add_test(NAME original_honey_policy COMMAND p2_original_honey_policy)
add_test(NAME original_honey_bank_policy COMMAND p2_original_honey_bank_policy)
add_test(NAME original_contents_save_policy COMMAND p2_original_contents_save_policy)
add_test(NAME original_egg_save_policy COMMAND p2_original_egg_save_policy)
add_test(NAME original_wisp_save_policy COMMAND p2_original_wisp_save_policy)
add_test(NAME original_honey_save_policy COMMAND p2_original_honey_save_policy)
