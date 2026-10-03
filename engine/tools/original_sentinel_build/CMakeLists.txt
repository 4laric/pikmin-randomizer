cmake_minimum_required(VERSION 3.20)
project(OriginalSentinelProviderChecks LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
enable_testing()
get_filename_component(SENTINEL_SOURCE "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
# Private composition includes the real owner-pinned Honey factory. Production
# course admission remains separate until actual source77 native gameplay passes.
set(PIKMIN_ORIGINAL_SENTINEL ON CACHE BOOL "Link original plant source77 factory and attachment consumers")
add_subdirectory("${SENTINEL_SOURCE}/tools/original_resource_build" resources)
# Root owns this single pure control declaration; expose its executable at the
# private graph root for worker hashing without injecting a second test target.
set_target_properties(pc_p2_original_shijimi_group_test PROPERTIES
 RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
add_executable(p2_original_shijimi_honey_identity
 "${SENTINEL_SOURCE}/tools/test_p2_original_shijimi_honey.cpp"
 "${SENTINEL_SOURCE}/pc_port/pc_p2_original_shijimi_honey.cpp"
 "${SENTINEL_SOURCE}/pc_port/pc_p2_original_resource_contents.cpp")
target_include_directories(p2_original_shijimi_honey_identity PRIVATE "${SENTINEL_SOURCE}/pc_port")
target_compile_options(p2_original_shijimi_honey_identity PRIVATE -Wall -Wextra -Werror -UNDEBUG)
enable_testing()
add_test(NAME original_shijimi_honey_identity COMMAND p2_original_shijimi_honey_identity)
add_executable(p2_original_shijimi_state
 "${SENTINEL_SOURCE}/tools/test_p2_original_shijimi_state.cpp"
 "${SENTINEL_SOURCE}/pc_port/pc_p2_original_shijimi_state.cpp")
target_include_directories(p2_original_shijimi_state PRIVATE "${SENTINEL_SOURCE}/pc_port")
target_compile_options(p2_original_shijimi_state PRIVATE -Wall -Wextra -Werror -UNDEBUG)
add_test(NAME original_shijimi_state COMMAND p2_original_shijimi_state)

# Genuine private resources are supplied explicitly to this control executable.
# Do not register a fake-byte or resource-free appearance acceptance test.
add_executable(p2_shijimi_effect_control
 "${SENTINEL_SOURCE}/tools/test_p2_shijimi_effect.cpp"
 "${SENTINEL_SOURCE}/pc_port/pc_p2_shijimi_effect.cpp")
target_include_directories(p2_shijimi_effect_control PRIVATE "${SENTINEL_SOURCE}/pc_port")
target_compile_options(p2_shijimi_effect_control PRIVATE -Wall -Wextra -Werror -UNDEBUG)

# Released397 SDK is a separately pinned predecessor, not a new native Piki
# producer. These controls link its real registry with controlled observers.
add_executable(p2_shijimi_attachment_control
 "${SENTINEL_SOURCE}/tools/test_p2_shijimi_attachment.cpp"
 "${SENTINEL_SOURCE}/pc_port/pc_p2_shijimi_attachment.cpp"
 "${SENTINEL_SOURCE}/pc_port/pc_p2_original_piki_origin.cpp")
target_include_directories(p2_shijimi_attachment_control PRIVATE "${SENTINEL_SOURCE}/pc_port")
target_compile_options(p2_shijimi_attachment_control PRIVATE -Wall -Wextra -Werror -UNDEBUG)
add_test(NAME original_shijimi_attachment_refs COMMAND p2_shijimi_attachment_control)

add_executable(p2_original_honey_identity_policy
 "${SENTINEL_SOURCE}/pc_port/pc_p2_original_honey_identity_test.cpp"
 "${SENTINEL_SOURCE}/pc_port/pc_p2_original_resource_contents.cpp")
target_include_directories(p2_original_honey_identity_policy PRIVATE "${SENTINEL_SOURCE}/pc_port")
target_compile_options(p2_original_honey_identity_policy PRIVATE -Wall -Wextra -Werror -UNDEBUG)
add_test(NAME original_honey_identity_policy COMMAND p2_original_honey_identity_policy)

foreach(control pc_p2_original_foliage_test p2_original_piki_origin_test p2_original_honey_save_policy
 p2_original_contents_save_policy p2_original_resource_state_policy
 p2_original_resource_save_policy p2_original_egg_contents_policy)
 set_target_properties(${control} PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
endforeach()
