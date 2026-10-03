# Include at the end of CMakeLists.txt in a private qualification checkout.
# Consumer integration owns maintained dispatch/registration independently.
target_sources(pikmin_pc PRIVATE
    pc_port/pc_p2_original_bulblax_snagret.cpp
    pc_port/pc_p2_original_bulblax_snagret_native.cpp)
add_executable(pc_p2_original_bulblax_snagret_test
    tools/test_p2_original_bulblax_snagret.cpp
    pc_port/pc_p2_original_bulblax_snagret.cpp
    pc_port/pc_p2_original_spawn_plan.cpp
    pc_port/pc_p2_original_drop.cpp
    pc_port/pc_p2_original_catalog.cpp)
target_include_directories(pc_p2_original_bulblax_snagret_test PRIVATE pc_port)
target_compile_options(pc_p2_original_bulblax_snagret_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME pc_p2_original_bulblax_snagret_test COMMAND pc_p2_original_bulblax_snagret_test)

pikmin_add_ci_fixture(original_snagret tools/p2_original_snagret_runtime.cpp)

add_executable(pc_p2_original_snagret_captain_guard_test tools/test_p2_original_snagret_captain_guard.cpp)
target_compile_options(pc_p2_original_snagret_captain_guard_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME pc_p2_original_snagret_captain_guard_test COMMAND pc_p2_original_snagret_captain_guard_test)
