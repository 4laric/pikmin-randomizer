###############################################################################
#  Pikmin PC Port — CMake Build System
#  Stage 1: Compilation Skeleton
#
#  This CMakeLists.txt compiles the decompiled Pikmin source code natively
#  for Linux x86_64, replacing all GameCube Dolphin SDK calls with our stubs.
#
#  Usage:
#    mkdir build && cd build
#    cmake ..
#    make -j$(nproc)
###############################################################################
cmake_minimum_required(VERSION 3.16)
project(PikminPC VERSION 0.1.0 LANGUAGES C CXX)

# Native MinGW defines WIN32 too; the original game uses that spelling for
# its incompatible legacy renderer. Keep _WIN32 for the actual host APIs.
if(MINGW AND NOT CMAKE_CXX_FLAGS MATCHES "-UWIN32")
    add_compile_options(-UWIN32)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_C_STANDARD 11)

# ─── Build type ───
# An unset build type means no -O flag at all, which is -O0: the game then runs
# several times slower with nothing on screen to say why. This is a game, so a
# build that is merely usable is the wrong default; RelWithDebInfo keeps the
# symbols a crash report needs while still optimising.
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE "RelWithDebInfo" CACHE STRING
        "Build type: Debug, Release, RelWithDebInfo or MinSizeRel" FORCE)
    message(STATUS "CMAKE_BUILD_TYPE was empty; defaulting to RelWithDebInfo.")
endif()
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    message(WARNING
        "Building Debug: no optimisation. Expect a fraction of the normal frame "
        "rate. For play or for any performance measurement, configure with "
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo.")
endif()

# ─── Compiler Flags ───
# Force-include our PC types header BEFORE anything else.
# This overrides MetroWerks and MSVC macros, fixes type sizes, etc.
set(PC_PORT_DIR "${CMAKE_SOURCE_DIR}/pc_port")

# Legacy code (decompiled GameCube sources) needs permissive compilation.
# Modern GCC would reject many Metrowerks-era constructs.
set(LEGACY_COMPILE_OPTIONS
    -include "${PC_PORT_DIR}/pc_types.h"
    -fpermissive
    -Wno-narrowing
    -Wno-multichar
    -Wno-write-strings
    -Wno-sign-compare
    -Wno-unused-variable
    -Wno-unused-but-set-variable
    -Wno-parentheses
    -Wno-delete-non-virtual-dtor
    -Wno-reorder
    -Wno-switch
    -Wno-format
    -Wno-attributes
    -Wno-comment
)

# Native code (pc_port, tests, launcher) should compile with strict warnings.
# We keep -fpermissive because native code includes legacy Dolphin headers.
set(NATIVE_COMPILE_OPTIONS
    -include "${PC_PORT_DIR}/pc_types.h"
    -fpermissive
    -Wall
    -Wextra
    -Wno-changes-meaning
    -Wno-narrowing
    -Wno-multichar
    -Wno-write-strings
    -Wno-sign-compare
    -Wno-unused-variable
    -Wno-unused-but-set-variable
    -Wno-parentheses
    -Wno-delete-non-virtual-dtor
    -Wno-reorder
    -Wno-attributes
    -Wno-comment
    -Werror=return-type
    -Werror=switch
)

# Off by default: the native mixer is the configuration known to work. Turn on
# with -DPIKMIN_NATIVE_JAUDIO=ON to drive audio from the original engine.
option(PIKMIN_NATIVE_JAUDIO "Drive audio with the original src/jaudio engine" OFF)

# Testing shortcuts (F5 stocks Pikmin, F6 skips an hour) and the menu row that
# switches them on. Off by default so a release carries no trace of them; turn
# on with -DPIKMIN_DEBUG_KEYS=ON while working on the Mods settings.
option(PIKMIN_DEBUG_KEYS "Build the F5/F6 testing shortcuts" OFF)

# ─── Which release of the game this binary is built for ───
#
# The port compiles the game's own code, and that code is conditional on the
# release in 404 places across 83 files, so this is a build-time choice and not
# a setting. The disc is only ever used for assets.
set(PIKMIN_GAME_VERSION "VERSION_GPIE01_01" CACHE STRING
    "Game release to build: VERSION_GPIE01_01 (USA Rev 1), VERSION_GPIE01_00, \
VERSION_GPIP01_00 (PAL), VERSION_GPIJ01_01, VERSION_GPIJ01_02")

add_compile_definitions(
    PIKI_PC_PORT=1
    ${PIKMIN_GAME_VERSION}
    DTK_CONFIG_NONMATCHING=1
    # The Linux renderer translates the game's native GX command stream to
    # OpenGL.  Selecting the old Win32/OpenGL code path here mixes two
    # incompatible texture/rendering backends and leaves GXTexObj uninitialised.
    PIKI_USE_DGX=1
    # Selects which engine drives audio. 0 keeps the native PC mixer in
    # pc_port/audio; 1 compiles the original engine in src/jaudio and renders
    # its DSPchannel_ voice parameter blocks through pc_dsp_host. The two
    # cannot coexist -- see the guards in dolphin_stubs/audio_stubs.cpp.
    PIKI_USE_JAUDIO=$<BOOL:${PIKMIN_NATIVE_JAUDIO}>
    PIKI_DEBUG_KEYS=$<BOOL:${PIKMIN_DEBUG_KEYS}>
    # Some SDL2 builds (including current Arch configurations) remap main to
    # SDL_main unless the application explicitly owns its entry point.
    SDL_MAIN_HANDLED=1
    # In-game settings menu (F1). Remove this to disable the overlay entirely.
    PIKI_PC_SETTINGS_MENU=1
)

# ─── Include paths ───
include_directories(
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/include/Dolphin
    ${CMAKE_SOURCE_DIR}/include/Dolphin/OS
    ${CMAKE_SOURCE_DIR}/include/Dolphin/GX
    ${PC_PORT_DIR}
    ${PC_PORT_DIR}/gl
)

###############################################################################
#  Source file lists
#  We compile only the game logic modules, NOT the original Dolphin SDK
#  implementations (those are replaced by our stubs).
###############################################################################

# ─── External Dependencies (SDL2 & OpenGL) ───
find_package(SDL2 QUIET)
if (NOT SDL2_FOUND)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(SDL2 REQUIRED sdl2)
endif()

# SDL2main supplies a WinMain that forwards to SDL_main. This project declares
# SDL_MAIN_HANDLED and defines its own main, so linking it leaves SDL_main
# undefined in every executable. Drop it wherever the SDL2 package offers it.
if (SDL2_LIBRARIES)
    list(FILTER SDL2_LIBRARIES EXCLUDE REGEX "SDL2main")
endif()

if (NOT WIN32)
    find_package(OpenGL REQUIRED)
endif()

set(PC_PORT_SOURCES
    pc_port/pc_p2_material_scope.cpp
    pc_port/pc_p2_material_binding.cpp
    pc_port/pc_p2_color_binding.cpp
    pc_port/pc_p2_specular_layer.cpp
    pc_port/pc_p2_demon_drop_state.cpp
    pc_port/pc_p2_demon_escape_state.cpp
    pc_port/pc_p2_demon_bridge.cpp
    pc_port/pc_p2_demon_host.cpp
    pc_port/pc_p2_sarai_host.cpp
    pc_port/pc_bbft.cpp
    pc_port/pc_p2_preview.cpp
    pc_port/pc_p2_captain.cpp
    pc_port/pc_p2_second_captain.cpp
    pc_port/pc_p2_economy.cpp
    pc_port/pc_p2_teki_lifetime.cpp
    pc_port/pc_p2_input_script.cpp
    pc_port/pc_p2_purple.cpp
    pc_port/pc_p2_purple_motion.cpp
    pc_port/pc_p2_purple_impact.cpp
    pc_port/pc_p2_purple_direct.cpp
    pc_port/pc_p2_purple_flight.cpp
    pc_port/pc_p2_purple_feedback.cpp
    pc_port/pc_p2_kochappy_stun.cpp
    pc_port/pc_p2_species.cpp
    pc_port/pc_p2_bulbmin.cpp
    pc_port/pc_p2_white.cpp
    pc_port/pc_p2_white_poison.cpp
    pc_port/pc_p2_cave.cpp
    pc_port/pc_p2_enemy.cpp
    pc_port/pc_p2_sheargrub.cpp
    pc_port/pc_p2_kochappy.cpp
    pc_port/pc_p2_dwarf_orange.cpp
    pc_port/pc_p2_kochappy_fsm.cpp
    pc_port/pc_p2_breadbug_visual.cpp
    pc_port/pc_p2_giant_breadbug_visual.cpp
    pc_port/pc_p2_bulblax_visual.cpp
    pc_port/pc_p2_queen.cpp
    pc_port/pc_p2_king.cpp
    pc_port/pc_p2_breadbug_actor.cpp
    pc_port/pc_p2_giant_breadbug_actor.cpp
    pc_port/pc_p2_frog.cpp
    pc_port/pc_p2_kogane.cpp
    pc_port/pc_p2_mamuta.cpp
    pc_port/pc_p2_mamuta_rules.cpp
    pc_port/pc_p2_tank.cpp
    pc_port/pc_p2_hiba.cpp
    pc_port/pc_p2_flora_actor.cpp
    pc_port/pc_p2_receipt_host.cpp
    pc_port/pc_p2_pom.cpp
    pc_port/pc_p2_plant.cpp
    pc_port/pc_p2_waterwraith_visual.cpp
    pc_port/pc_p2_waterwraith_host.cpp
    pc_port/pc_p2_waterwraith_register.cpp
    pc_port/pc_p2_waterwraith_encounter.cpp
    pc_port/pc_p2_dweevil.cpp
    pc_port/pc_p2_bombotakara.cpp
    pc_port/pc_p2_qurione.cpp
    pc_port/pc_p2_shijimi.cpp
    pc_port/pc_p2_kurage_receiver.cpp
    pc_port/pc_p2_sokkuri.cpp
    pc_port/pc_p2_armor.cpp
    pc_port/pc_p2_elecbug.cpp
    pc_port/pc_p2_tamago.cpp
    pc_port/pc_p2_imomushi.cpp
    pc_port/pc_p2_hana.cpp
    pc_port/pc_p2_tadpole.cpp
    pc_port/pc_p2_mar.cpp
    pc_port/pc_p2_catfish.cpp
    pc_port/pc_p2_hanachirashi.cpp
    pc_port/pc_p2_dangomushi.cpp
    pc_port/pc_p2_snakejoint.cpp
    pc_port/pc_p2_jigumo.cpp
    pc_port/pc_p2_umimushi.cpp
    pc_port/pc_p2_batch2.cpp
    pc_port/pc_p2_batch3.cpp
    pc_port/pc_p2_snagret_fsm.cpp
    pc_port/pc_p2_dangomushi_hazard.cpp
    pc_port/pc_p2_long_legs_fsm.cpp
    pc_port/pc_p2_long_legs.cpp
    pc_port/pc_p2_cannon_stone.cpp
    pc_port/pc_p2_egg_hazard.cpp
pc_port/pc_p2_kabuto_cannon.cpp
pc_port/pc_p2_kabuto_events.cpp
pc_port/pc_p2_kabuto_muzzle.cpp
pc_port/pc_p2_kabuto_binding.cpp
pc_port/pc_p2_projectile_host.cpp
    pc_port/pc_p2_rock_hazard.cpp
    pc_port/pc_p2_projectile_receiver.cpp
    pc_port/pc_p2_groink.cpp
    pc_port/pc_p2_groink_arena.cpp
    pc_port/pc_p2_groink_attack.cpp
    pc_port/pc_p2_groink_map_trace.cpp
    pc_port/pc_p2_groink_target.cpp
    pc_port/pc_p2_groink_volley.cpp
    pc_port/pc_p2_groink_hit.cpp
    pc_port/pc_p2_groink_strike.cpp
    pc_port/pc_p2_projectiles.cpp
    pc_port/pc_p2_hardlanes.cpp
    pc_port/pc_p2_fuefuki_visual.cpp
    pc_port/pc_p2_fuefuki_motion.cpp
    pc_port/pc_p2_bombsarai_arena.cpp
    pc_port/pc_p2_bombsarai_blast.cpp
    pc_port/pc_p2_bombsarai_bomb.cpp
    pc_port/pc_p2_bombsarai_fsm.cpp
    pc_port/pc_p2_bombsarai_hover.cpp
    pc_port/pc_p2_bombsarai_map_trace.cpp
    pc_port/pc_p2_bombsarai_terrain.cpp
    pc_port/pc_p2_bigtreasure.cpp
    pc_port/pc_p2_bigtreasure_attacks.cpp
    pc_port/pc_p2_bigtreasure_fsm.cpp
    pc_port/pc_p2_bigtreasure_host.cpp
    pc_port/pc_p2_bigtreasure_fsmhost.cpp
    pc_port/pc_p2_bigtreasure_map_trace.cpp
    pc_port/pc_p2_bigtreasure_motion.cpp
    pc_port/pc_p2_bigtreasure_visual.cpp
    pc_port/pc_p2_bigtreasure_save.cpp
    pc_port/pc_p2_bigtreasure_ordinary.cpp
    pc_port/pc_p2_bigtreasure_animclock.cpp
    pc_port/pc_p2_bigtreasure_elements.cpp
    pc_port/pc_randomizer.cpp
    pc_port/pc_p2_waterwraith.cpp
    pc_port/pc_p2_waterwraith_actor.cpp
    pc_port/pc_p2_kurage.cpp
    pc_port/pc_p2_kurage_arena.cpp
    pc_port/pc_p2_kurage_visual.cpp
    pc_port/pc_p2_kurage_teki.cpp
    pc_port/pc_p2_onikurage_mouth.cpp
    pc_port/pc_p2_onikurage_teki.cpp
    pc_port/pc_main.cpp
    pc_port/pc_window.cpp
    pc_port/pc_pad_axis.cpp
    pc_port/pc_menu_repeat.cpp
    pc_port/pc_photo_mode.cpp
    pc_port/pc_permadeath.cpp
    pc_port/pc_gpu_preference.cpp
    pc_port/gl/pc_gfx.cpp
    pc_port/gl/pc_tev_shader.cpp
    pc_port/gl/pc_postprocess.cpp
    pc_port/timing/pc_frame_scheduler.cpp
    pc_port/timing/pc_render_phase.cpp
    pc_port/timing/pc_visual_snapshot.cpp
    pc_port/timing/pc_camera_snapshot.cpp
    pc_port/timing/pc_visual_runtime.cpp
    pc_port/timing/pc_render_packet.cpp
    pc_port/timing/pc_tick_profiler.cpp
    pc_port/audio/pc_audio.cpp
    pc_port/audio/pc_envelope.cpp
    pc_port/audio/pc_jam.cpp
    pc_port/audio/pc_instrument_bank.cpp
    pc_port/audio/pc_wave_bank.cpp
    pc_port/audio/pc_sequence_archive.cpp
    pc_port/audio/pc_aram.cpp
    pc_port/audio/pc_dsp_host.cpp
    pc_port/settings/pc_settings.cpp
    pc_port/settings/pc_settings_p2d.cpp
    src/jaudio/pikiseq.c
    pc_port/dolphin_stubs/os_stubs.cpp
    pc_port/dolphin_stubs/gx_stubs.cpp
    pc_port/dolphin_stubs/dvd_stubs.cpp
    pc_port/dolphin_stubs/pad_stubs.cpp
    pc_port/dolphin_stubs/vi_stubs.cpp
    pc_port/dolphin_stubs/card_stubs.cpp
    pc_port/dolphin_stubs/audio_stubs.cpp
    pc_port/dolphin_stubs/jaudio_hw_stubs.cpp
    pc_port/dolphin_stubs/misc_stubs.cpp
)

include_directories(
    ${SDL2_INCLUDE_DIRS}
    ${OPENGL_INCLUDE_DIR}
)

# ─── System Common (platform-independent game engine) ───
file(GLOB SYSCOMMON_SOURCES "src/sysCommon/*.cpp")

# ─── System Dolphin (GameCube-specific system layer — we compile it but stubs handle the calls) ───
set(SYSDOLPHIN_SOURCES
    src/sysDolphin/controllerMgr.cpp
    src/sysDolphin/dgxGraphics.cpp
    src/sysDolphin/gameApp.cpp
    src/sysDolphin/sysNew.cpp
    src/sysDolphin/system.cpp
    src/sysDolphin/texture.cpp
)

# JAudio uses NextOS's host boundary, never the GameCube DSP boot/mailboxes.
set(JAUDIO_TARGET_SOURCES "")
if(PIKMIN_NATIVE_JAUDIO)
    set(JAUDIO_TARGET_SOURCES
        src/jaudio/aramcall.c
        src/jaudio/audiomesg.c
        src/jaudio/bankdrv.c
        src/jaudio/bankloader.c
        src/jaudio/bankread.c
        src/jaudio/centcalc.c
        src/jaudio/cmdqueue.c
        src/jaudio/cmdstack.c
        src/jaudio/connect.c
        src/jaudio/driverinterface.c
        src/jaudio/dspdriver.c
        src/jaudio/dspinterface.c
        src/jaudio/dummyprobe.c
        src/jaudio/dummyrom.c
        src/jaudio/dvdthread.c
        src/jaudio/fat.c
        src/jaudio/file_seq.c
        src/jaudio/filter3d.c
        src/jaudio/fxinterface.c
        src/jaudio/heapctrl.c
        src/jaudio/interface.c
        src/jaudio/interleave.c
        # H4M video. The decoder is complete -- no TRAP_UNIMPLEMENTED anywhere
        # in hvqm4dec.c -- and hvqm_play.c's three are all in jaudio's own
        # decode thread, which this game never uses: movSample.cpp drives
        # Jac_HVQM_Update from a thread of its own, and that function is whole.
        src/hvqm4dec/hvqm4dec.c
        src/jaudio/hvqm_play.c
        src/jaudio/app_inter.c
        src/jaudio/ja_calc.c
        src/jaudio/jammain_2.c
        src/jaudio/jamosc.c
        src/jaudio/memory.c
        src/jaudio/midplay.c
        src/jaudio/noteon.c
        src/jaudio/oneshot.c
        src/jaudio/piki_bgm.c
        src/jaudio/piki_player.c
        src/jaudio/piki_scene.c
        src/jaudio/pikidemo.c
        src/jaudio/pikiinter.c
        src/jaudio/pikiseq.c
        src/jaudio/playercall.c
        src/jaudio/random.c
        src/jaudio/rate.c
        src/jaudio/sample.c
        src/jaudio/seqsetup.c
        src/jaudio/stackchecker.c
        src/jaudio/streamctrl.c
        src/jaudio/syncstream.c
        src/jaudio/tables.c
        src/jaudio/verysimple.c
        src/jaudio/virload.c
        src/jaudio/waveread.c
    )
    set_source_files_properties(${JAUDIO_TARGET_SOURCES} PROPERTIES LANGUAGE CXX)
    list(REMOVE_ITEM PC_PORT_SOURCES src/jaudio/pikiseq.c
        pc_port/audio/pc_dsp_host.cpp pc_port/dolphin_stubs/jaudio_hw_stubs.cpp)
    list(APPEND PC_PORT_SOURCES pc_port/audio/jaudio_integration_test.cpp)
    list(APPEND JAUDIO_TARGET_SOURCES pc_port/audio/jaudio_host.cpp
        pc_port/audio/jaudio_bank_host.cpp pc_port/audio/jaudio_sink.cpp)
    message(STATUS "Audio: JAudio + NextOS software DSP (SDL2)")
else()
    message(STATUS "Audio: legacy native PC mixer (pc_port/audio)")
endif()

# ─── Game plugin modules (the actual game code) ───
file(GLOB PLUGPIKI_KANDO_SOURCES   "src/plugPikiKando/*.cpp")
file(GLOB PLUGPIKI_NAKATA_SOURCES  "src/plugPikiNakata/*.cpp")
file(GLOB PLUGPIKI_NISHIMURA_SOURCES "src/plugPikiNishimura/*.cpp")
file(GLOB PLUGPIKI_COLIN_SOURCES   "src/plugPikiColin/*.cpp")
file(GLOB PLUGPIKI_OGAWA_SOURCES   "src/plugPikiOgawa/*.cpp")
file(GLOB PLUGPIKI_YAMASHITA_SOURCES "src/plugPikiYamashita/*.cpp")

###############################################################################
#  Files we EXCLUDE from compilation
#  These are GameCube hardware drivers that our stubs replace entirely.
###############################################################################
# We do NOT compile:
#   src/os/          — Dolphin OS implementation (replaced by os_stubs)
#   src/gx/          — GX hardware driver (replaced by gx_stubs)
#   src/dvd/         — DVD hardware driver (replaced by dvd_stubs)
#   src/pad/         — PAD hardware driver (replaced by pad_stubs)
#   src/vi/          — VI hardware driver (replaced by vi_stubs)
#   src/card/        — Memory card driver (replaced by card_stubs)
#   src/dsp/         — DSP driver (replaced by audio_stubs)
#   src/ai/          — Audio interface (replaced by audio_stubs)
#   src/ar/          — ARAM driver (replaced by os_stubs)
#   src/si/          — Serial interface (replaced by misc_stubs)
#   src/exi/         — Expansion interface (replaced by misc_stubs)
#   src/jaudio/      — JAudio library (replaced by audio_stubs)
#   src/mtx/         — Matrix math (replaced by misc_stubs)
#   src/mtxD/        — Matrix math (replaced by misc_stubs)
#   src/base/        — PPCArch (replaced by misc_stubs)
#   src/db/          — Debug (replaced by misc_stubs)
#   src/hio/         — Host I/O (replaced by misc_stubs)
#   src/hvqm4dec/    — Video decoder (built with PIKMIN_NATIVE_JAUDIO)
#   src/MSL_C/       — MetroWerks Standard Library (use system libc)
#   src/Runtime/     — CodeWarrior Runtime (use system runtime)
#   src/TRK_MINNOW_DOLPHIN/ — Debugger (not needed)
#   src/OdemuExi2/   — Dev kit hardware (not needed)
#   src/amcExi2/     — Dev kit hardware (not needed)
#   src/amcnotstub/  — Dev kit hardware (not needed)
#   src/amcstubs/    — Dev kit hardware (not needed)
#   src/odemustubs/  — Dev kit hardware (not needed)
#   src/odenotstub/  — Dev kit hardware (not needed)
#   src/sysCore/     — Windows DLL code (uses Win32 APIs, will adapt later)
#   src/sysBootup.cpp — Original entry point (replaced by pc_main.cpp)

###############################################################################
#  Build the executable
###############################################################################
# Create a static library for legacy (decompiled) sources with permissive flags.
# This isolates the legacy compilation from the strict native compilation.
add_library(pikmin_legacy STATIC
    ${SYSCOMMON_SOURCES}
    ${SYSDOLPHIN_SOURCES}
    ${PLUGPIKI_KANDO_SOURCES}
    ${PLUGPIKI_NAKATA_SOURCES}
    ${PLUGPIKI_NISHIMURA_SOURCES}
    ${PLUGPIKI_COLIN_SOURCES}
    ${PLUGPIKI_OGAWA_SOURCES}
    ${PLUGPIKI_YAMASHITA_SOURCES}
    # Empty unless PIKMIN_NATIVE_JAUDIO is on. The engine belongs here rather
    # than in pikmin_pc because it is decompiled code and needs the permissive
    # legacy flags, not the strict ones the port's own sources build with.
    ${JAUDIO_TARGET_SOURCES}
)
target_compile_options(pikmin_legacy PRIVATE ${LEGACY_COMPILE_OPTIONS})

# Native executable with strict flags
add_executable(pikmin_pc
    ${PC_PORT_SOURCES}
)
target_compile_options(pikmin_pc PRIVATE ${NATIVE_COMPILE_OPTIONS})
target_link_libraries(pikmin_pc PRIVATE pikmin_legacy)
if(WIN32)
    add_library(bbft_transport STATIC pc_port/bbft/bbft_transport.c)
    target_link_libraries(pikmin_pc PRIVATE bbft_transport ws2_32)
    add_executable(pc_bbft_test pc_port/pc_bbft_test.cpp pc_port/pc_bbft.cpp pc_port/pc_randomizer.cpp)
    add_test(NAME pc_bbft_test COMMAND pc_bbft_test)
    add_test(NAME pc_bbft_background_test COMMAND pc_bbft_test --background)
    add_executable(jaudio_bbft_test pc_port/audio/jaudio_bbft_test.cpp pc_port/audio/jaudio_sink.cpp)
    target_include_directories(jaudio_bbft_test PRIVATE pc_port ${SDL2_INCLUDE_DIRS})
    target_link_libraries(jaudio_bbft_test PRIVATE ${SDL2_LIBRARIES})
    add_test(NAME jaudio_bbft_test COMMAND jaudio_bbft_test)
endif()

# GX display lists, game logic and the software audio mixer execute on the host
# CPU. Keep optimization level, machine-specific ISA and link-time optimization
# independent so release archives can remain portable.
#
# Both targets must receive all three. The bulk of the per-frame CPU work is in
# pikmin_legacy, not in pikmin_pc: renderall(), the scene traversal, the matrix
# and collision maths and every GX call the translator consumes are decompiled
# sources. When these options were attached to pikmin_pc alone -- which they
# were from the moment the legacy sources were split out into their own library
# -- the game code silently lost -march=native and LTO, and the library
# boundary also stopped the translator from inlining into it. That is a
# performance regression with no visible symptom other than the frame time.
set(PIKMIN_OPTIMIZED_TARGETS pikmin_pc pikmin_legacy)

foreach(target IN LISTS PIKMIN_OPTIMIZED_TARGETS)
    target_compile_options(${target} PRIVATE
        $<$<AND:$<CONFIG:Release>,$<COMPILE_LANG_AND_ID:C,GNU,Clang>>:-O3>
        $<$<AND:$<CONFIG:Release>,$<COMPILE_LANG_AND_ID:CXX,GNU,Clang>>:-O3>
        $<$<AND:$<CONFIG:RelWithDebInfo>,$<COMPILE_LANG_AND_ID:C,GNU,Clang>>:-O3>
        $<$<AND:$<CONFIG:RelWithDebInfo>,$<COMPILE_LANG_AND_ID:CXX,GNU,Clang>>:-O3>)
endforeach()

option(PIKMIN_NATIVE_OPTIMIZE "Use this build machine's CPU instruction set" ON)
if(PIKMIN_NATIVE_OPTIMIZE AND CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    foreach(target IN LISTS PIKMIN_OPTIMIZED_TARGETS)
        target_compile_options(${target} PRIVATE -march=native)
    endforeach()
endif()

option(PIKMIN_ENABLE_IPO "Enable portable interprocedural/link-time optimization" ON)
if(PIKMIN_ENABLE_IPO)
    include(CheckIPOSupported)
    check_ipo_supported(RESULT PIKMIN_IPO_SUPPORTED OUTPUT PIKMIN_IPO_ERROR)
    if(PIKMIN_IPO_SUPPORTED)
        foreach(target IN LISTS PIKMIN_OPTIMIZED_TARGETS)
            set_property(TARGET ${target} PROPERTY INTERPROCEDURAL_OPTIMIZATION TRUE)
        endforeach()
    else()
        message(WARNING "IPO/LTO unavailable: ${PIKMIN_IPO_ERROR}")
    endif()
endif()

# Link against math, SDL2, and OpenGL libraries
if (WIN32)
    # MinGW ya trae las funciones matemáticas en su runtime: no existe libm
    # suelta, y OpenGL lo expone opengl32.
    #
    # SDL2main NO se enlaza: aporta un WinMain que llama a SDL_main, y este
    # proyecto declara SDL_MAIN_HANDLED y define su propio main. Enlazarlo deja
    # SDL_main sin definir en todos los ejecutables.
    target_link_libraries(pikmin_pc PRIVATE ${SDL2_LIBRARIES} opengl32)
else()
    target_link_libraries(pikmin_pc PRIVATE m ${SDL2_LIBRARIES} OpenGL::GL X11)
endif()
# Export symbol names so the diagnostic backtrace in pc_gfx.cpp prints function
# names rather than bare addresses. Costs nothing at runtime.
#
# GNU-ld only: MinGW rejects the flag outright, and the backtrace it serves is
# compiled out on Windows anyway (glibc's execinfo.h has no equivalent there).
if (NOT WIN32)
    target_link_options(pikmin_pc PRIVATE -rdynamic)
else()
    # SDL2's CMake package links -mwindows, which hides the console and with it
    # every printf the port uses to report what it is doing. Keep a console on
    # the game so a failed launch says why instead of vanishing. The launcher
    # stays windowed: it talks through native dialogs.
    target_link_options(pikmin_pc PRIVATE -mconsole)
endif()

# Set output name
set_target_properties(pikmin_pc PROPERTIES
    OUTPUT_NAME "nectar"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)
if(NOT WIN32)
add_custom_command(TARGET pikmin_pc POST_BUILD
    COMMAND /bin/chmod 775 "$<TARGET_FILE:pikmin_pc>"
    COMMENT "Ensuring the native Pikmin executable is runnable")
endif()

# Standalone first-run launcher. It accepts an original, uncompressed
# GameCube ISO/GCM supplied by the user, extracts its FST into the per-user
# data directory and then starts the game from there. Keeping the extractor in
# a small library also lets CI test the legal install path without game assets.
add_library(pikmin_disc_image STATIC
    pc_port/launcher/gamecube_image.cpp
    pc_port/launcher/sha256.cpp)
target_include_directories(pikmin_disc_image PUBLIC
    ${CMAKE_SOURCE_DIR}/pc_port/launcher)
target_compile_options(pikmin_disc_image PRIVATE ${NATIVE_COMPILE_OPTIONS})

# La capa de plataforma aísla lo único del launcher que depende del sistema:
# rutas del ejecutable, diálogos y arranque del juego.
if (WIN32)
    set(LAUNCHER_PLATFORM_SOURCE pc_port/launcher/launcher_platform_win32.cpp)
else()
    set(LAUNCHER_PLATFORM_SOURCE pc_port/launcher/launcher_platform_posix.cpp)
endif()

find_package(Threads REQUIRED)
add_executable(pikmin_launcher
    pc_port/launcher/launcher_main.cpp
    pc_port/launcher/installer_ui.cpp
    ${LAUNCHER_PLATFORM_SOURCE})
target_include_directories(pikmin_launcher PRIVATE ${SDL2_INCLUDE_DIRS})
target_link_libraries(pikmin_launcher PRIVATE pikmin_disc_image ${SDL2_LIBRARIES} Threads::Threads)
if (WIN32)
    # Diálogo de archivo clásico, selector de carpeta del shell y COM.
    target_link_libraries(pikmin_launcher PRIVATE comdlg32 ole32 shell32 uuid)
endif()
target_compile_options(pikmin_launcher PRIVATE ${NATIVE_COMPILE_OPTIONS})
set_target_properties(pikmin_launcher PROPERTIES
    OUTPUT_NAME "nectar-launcher"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

add_executable(gamecube_image_test
    pc_port/launcher/gamecube_image_test.cpp)
target_link_libraries(gamecube_image_test PRIVATE pikmin_disc_image)
target_compile_options(gamecube_image_test PRIVATE ${NATIVE_COMPILE_OPTIONS})

add_executable(sha256_test
    pc_port/launcher/sha256_test.cpp)
target_link_libraries(sha256_test PRIVATE pikmin_disc_image)
target_compile_options(sha256_test PRIVATE ${NATIVE_COMPILE_OPTIONS})

add_executable(installer_ui_test
    pc_port/launcher/installer_ui_test.cpp
    pc_port/launcher/installer_ui.cpp)
target_include_directories(installer_ui_test PRIVATE
    ${CMAKE_SOURCE_DIR}/pc_port/launcher
    ${SDL2_INCLUDE_DIRS})
target_link_libraries(installer_ui_test PRIVATE ${SDL2_LIBRARIES})
target_compile_options(installer_ui_test PRIVATE ${NATIVE_COMPILE_OPTIONS})


enable_testing()
add_test(NAME gamecube_image_test COMMAND gamecube_image_test)
add_test(NAME sha256_test COMMAND sha256_test)
add_test(NAME installer_ui_test COMMAND installer_ui_test)

add_executable(asset_finalize_test pc_port/launcher/asset_finalize_test.cpp)
target_link_libraries(asset_finalize_test PRIVATE Threads::Threads)
target_compile_options(asset_finalize_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME asset_finalize_test COMMAND asset_finalize_test)

add_executable(prepared_image_test pc_port/launcher/prepared_image_test.cpp ${LAUNCHER_PLATFORM_SOURCE})
target_compile_options(prepared_image_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
if (WIN32)
    target_link_libraries(prepared_image_test PRIVATE comdlg32 ole32 shell32 uuid)
endif()
add_test(NAME prepared_image_test COMMAND prepared_image_test)

add_executable(pc_generator_cache_validation_test
    pc_port/save/pc_generator_cache_validation_test.cpp)
target_include_directories(pc_generator_cache_validation_test PRIVATE pc_port/save)
target_compile_options(pc_generator_cache_validation_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_generator_cache_validation_test COMMAND pc_generator_cache_validation_test)

# Both executables must remain side by side: the launcher resolves the game
# binary relative to itself, so this also works in relocatable archives.
install(TARGETS pikmin_pc pikmin_launcher
    RUNTIME DESTINATION bin)

# Envelope smoke test executable (not linked into main game)
add_executable(pc_envelope_test pc_port/audio/pc_envelope_test.cpp pc_port/audio/pc_envelope.cpp)
target_link_libraries(pc_envelope_test PRIVATE m)
target_compile_options(pc_envelope_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_envelope_test COMMAND pc_envelope_test)

# Host-backed ARAM test (not linked into main game)
add_executable(pc_aram_test pc_port/audio/pc_aram_test.cpp pc_port/audio/pc_aram.cpp)
target_compile_options(pc_aram_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_aram_test COMMAND pc_aram_test)

# Pad axis conversion (no controller needed)
add_executable(pc_pad_axis_test pc_port/pc_pad_axis_test.cpp pc_port/pc_pad_axis.cpp)
target_include_directories(pc_pad_axis_test PRIVATE ${SDL2_INCLUDE_DIRS} pc_port)
target_compile_options(pc_pad_axis_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_pad_axis_test COMMAND pc_pad_axis_test)

# Permadeath save block (no game needed)
add_executable(pc_permadeath_test pc_port/pc_permadeath_test.cpp pc_port/pc_permadeath.cpp src/sysCommon/stream.cpp src/sysCommon/string.cpp)
target_include_directories(pc_permadeath_test PRIVATE pc_port include)
target_compile_options(pc_permadeath_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_permadeath_test COMMAND pc_permadeath_test)

# Photo mode camera convention (no stage needed)
add_executable(pc_photo_mode_test pc_port/pc_photo_mode_test.cpp pc_port/pc_photo_mode.cpp)
target_include_directories(pc_photo_mode_test PRIVATE ${SDL2_INCLUDE_DIRS} pc_port)
target_link_libraries(pc_photo_mode_test PRIVATE ${SDL2_LIBRARIES})
target_compile_options(pc_photo_mode_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_photo_mode_test COMMAND pc_photo_mode_test)

# Which GPU to ask for on a switchable-graphics laptop (no GPU needed)
add_executable(pc_gpu_preference_test pc_port/pc_gpu_preference_test.cpp pc_port/pc_gpu_preference.cpp)
target_include_directories(pc_gpu_preference_test PRIVATE pc_port)
target_compile_options(pc_gpu_preference_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_gpu_preference_test COMMAND pc_gpu_preference_test)

# Menu input repeat (no controller needed)
add_executable(pc_menu_repeat_test pc_port/pc_menu_repeat_test.cpp pc_port/pc_menu_repeat.cpp)
target_include_directories(pc_menu_repeat_test PRIVATE pc_port)
target_compile_options(pc_menu_repeat_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_menu_repeat_test COMMAND pc_menu_repeat_test)

# Host software DSP test (not linked into main game)
add_executable(pc_dsp_host_test
    pc_port/audio/pc_dsp_host_test.cpp
    pc_port/audio/pc_dsp_host.cpp
    pc_port/audio/pc_aram.cpp)
target_compile_options(pc_dsp_host_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_dsp_host_test COMMAND pc_dsp_host_test)

add_executable(pc_jam_test
    pc_port/audio/pc_jam_test.cpp
    pc_port/audio/pc_jam.cpp
    pc_port/audio/pc_instrument_bank.cpp
    pc_port/audio/pc_sequence_archive.cpp
    pc_port/audio/pc_wave_bank.cpp
    src/jaudio/pikiseq.c)
target_compile_options(pc_jam_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
if(EXISTS "${CMAKE_SOURCE_DIR}/assets/dataDir/SndData/Banks/pikibank.bx")
    add_test(NAME pc_jam_test COMMAND pc_jam_test)
    set_tests_properties(pc_jam_test PROPERTIES WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}")
endif()

add_executable(pc_audio_mixer_test
    pc_port/audio/pc_audio_mixer_test.cpp
    pc_port/audio/pc_audio.cpp
    pc_port/audio/pc_envelope.cpp
    pc_port/audio/pc_jam.cpp
    pc_port/audio/pc_instrument_bank.cpp
    pc_port/audio/pc_sequence_archive.cpp
    pc_port/audio/pc_wave_bank.cpp
    src/jaudio/pikiseq.c)
target_link_libraries(pc_audio_mixer_test PRIVATE m ${SDL2_LIBRARIES})
target_compile_options(pc_audio_mixer_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
if(EXISTS "${CMAKE_SOURCE_DIR}/assets/dataDir/SndData/Banks/pikibank.bx")
    add_test(NAME pc_audio_mixer_test COMMAND pc_audio_mixer_test)
    set_tests_properties(pc_audio_mixer_test PROPERTIES WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}")
endif()

add_executable(pc_frame_scheduler_test
    pc_port/timing/pc_frame_scheduler_test.cpp
    pc_port/timing/pc_frame_scheduler.cpp)
target_compile_options(pc_frame_scheduler_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_frame_scheduler_test COMMAND pc_frame_scheduler_test)

add_executable(p2_dangomushi_hazard_test
    tools/p2_dangomushi_hazard_test.cpp
    pc_port/pc_p2_dangomushi_hazard.cpp)
target_include_directories(p2_dangomushi_hazard_test PRIVATE pc_port)
target_compile_options(p2_dangomushi_hazard_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_dangomushi_hazard_test COMMAND p2_dangomushi_hazard_test)

add_executable(p2_long_legs_fsm_test
    tools/p2_long_legs_fsm_test.cpp
    pc_port/pc_p2_long_legs_fsm.cpp)
target_include_directories(p2_long_legs_fsm_test PRIVATE pc_port)
target_compile_options(p2_long_legs_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_long_legs_fsm_test COMMAND p2_long_legs_fsm_test)

add_executable(p2_snagret_fsm_test
    tools/p2_snagret_fsm_test.cpp
    pc_port/pc_p2_snagret_fsm.cpp)
target_include_directories(p2_snagret_fsm_test PRIVATE pc_port)
target_compile_options(p2_snagret_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_snagret_fsm_test COMMAND p2_snagret_fsm_test)

# Lane 27 BombSarai (Careening Dirigibug) engine-free source-policy gates. The
# sources shipped on the approved line without ctest registration.
add_executable(p2_bombsarai_fsm_test
    tools/p2_bombsarai_fsm_test.cpp
    pc_port/pc_p2_bombsarai_fsm.cpp)
target_include_directories(p2_bombsarai_fsm_test PRIVATE pc_port)
target_compile_options(p2_bombsarai_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bombsarai_fsm_test COMMAND p2_bombsarai_fsm_test)

add_executable(p2_bombsarai_bomb_test
    tools/p2_bombsarai_bomb_test.cpp
    pc_port/pc_p2_bombsarai_bomb.cpp)
target_include_directories(p2_bombsarai_bomb_test PRIVATE pc_port)
target_compile_options(p2_bombsarai_bomb_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bombsarai_bomb_test COMMAND p2_bombsarai_bomb_test)

add_executable(p2_bombsarai_blast_test
    tools/p2_bombsarai_blast_test.cpp
    pc_port/pc_p2_bombsarai_blast.cpp)
target_include_directories(p2_bombsarai_blast_test PRIVATE pc_port)
target_compile_options(p2_bombsarai_blast_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bombsarai_blast_test COMMAND p2_bombsarai_blast_test)

add_executable(p2_bombsarai_clock_test
    tools/p2_bombsarai_clock_test.cpp)
target_include_directories(p2_bombsarai_clock_test PRIVATE pc_port)
target_compile_options(p2_bombsarai_clock_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bombsarai_clock_test COMMAND p2_bombsarai_clock_test)

add_executable(p2_bombsarai_hover_test
    tools/p2_bombsarai_hover_test.cpp
    pc_port/pc_p2_bombsarai_hover.cpp)
target_include_directories(p2_bombsarai_hover_test PRIVATE pc_port)
target_compile_options(p2_bombsarai_hover_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bombsarai_hover_test COMMAND p2_bombsarai_hover_test)

add_executable(p2_bombsarai_terrain_test
    tools/p2_bombsarai_terrain_test.cpp
    pc_port/pc_p2_bombsarai_terrain.cpp
    pc_port/pc_p2_bombsarai_bomb.cpp)
target_include_directories(p2_bombsarai_terrain_test PRIVATE pc_port)
target_compile_options(p2_bombsarai_terrain_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bombsarai_terrain_test COMMAND p2_bombsarai_terrain_test)

add_executable(p2_bombsarai_induction_test
    tools/p2_bombsarai_induction_test.cpp
    pc_port/pc_p2_bombsarai_bomb.cpp)
target_include_directories(p2_bombsarai_induction_test PRIVATE pc_port)
target_compile_options(p2_bombsarai_induction_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bombsarai_induction_test COMMAND p2_bombsarai_induction_test)

# Lane 27 Fuefuki hard-lane header-only policy gates (unwired on the approved line).
add_executable(p2_fuefuki_binding_test tools/p2_fuefuki_binding_test.cpp)
target_include_directories(p2_fuefuki_binding_test PRIVATE pc_port)
target_compile_options(p2_fuefuki_binding_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_fuefuki_binding_test COMMAND p2_fuefuki_binding_test)

add_executable(p2_fuefuki_fsm_test tools/p2_fuefuki_fsm_test.cpp)
target_include_directories(p2_fuefuki_fsm_test PRIVATE pc_port)
target_compile_options(p2_fuefuki_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_fuefuki_fsm_test COMMAND p2_fuefuki_fsm_test)

add_executable(p2_fuefuki_interference_policy_test tools/p2_fuefuki_interference_policy_test.cpp)
target_include_directories(p2_fuefuki_interference_policy_test PRIVATE pc_port)
target_compile_options(p2_fuefuki_interference_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_fuefuki_interference_policy_test COMMAND p2_fuefuki_interference_policy_test)

add_executable(p2_fuefuki_suspend_fallback_test tools/p2_fuefuki_suspend_fallback_test.cpp)
target_include_directories(p2_fuefuki_suspend_fallback_test PRIVATE pc_port)
target_compile_options(p2_fuefuki_suspend_fallback_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_fuefuki_suspend_fallback_test COMMAND p2_fuefuki_suspend_fallback_test)

# Lane 27 BigTreasure policy gates (unwired on the approved line).
add_executable(p2_bigtreasure_test
    tools/p2_bigtreasure_test.cpp
    pc_port/pc_p2_bigtreasure.cpp)
target_include_directories(p2_bigtreasure_test PRIVATE pc_port)
target_compile_options(p2_bigtreasure_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bigtreasure_test COMMAND p2_bigtreasure_test)

add_executable(p2_bigtreasure_fsm_test
    tools/p2_bigtreasure_fsm_test.cpp
    pc_port/pc_p2_bigtreasure_fsm.cpp)
target_include_directories(p2_bigtreasure_fsm_test PRIVATE pc_port)
target_compile_options(p2_bigtreasure_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bigtreasure_fsm_test COMMAND p2_bigtreasure_fsm_test)

add_executable(p2_bigtreasure_attacks_test
    tools/p2_bigtreasure_attacks_test.cpp
    pc_port/pc_p2_bigtreasure_attacks.cpp
    pc_port/pc_p2_bigtreasure.cpp)
target_include_directories(p2_bigtreasure_attacks_test PRIVATE pc_port)
target_compile_options(p2_bigtreasure_attacks_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bigtreasure_attacks_test COMMAND p2_bigtreasure_attacks_test)

set(P2_BIGTREASURE_TEST_DEPS
    pc_port/pc_p2_bigtreasure.cpp
    pc_port/pc_p2_bigtreasure_fsm.cpp
    pc_port/pc_p2_bigtreasure_attacks.cpp
    pc_port/pc_p2_bigtreasure_host.cpp
    pc_port/pc_p2_bigtreasure_fsmhost.cpp
    pc_port/pc_p2_bigtreasure_motion.cpp)

add_executable(p2_bigtreasure_fsmhost_test
    tools/p2_bigtreasure_fsmhost_test.cpp
    ${P2_BIGTREASURE_TEST_DEPS})
target_include_directories(p2_bigtreasure_fsmhost_test PRIVATE pc_port)
target_compile_options(p2_bigtreasure_fsmhost_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bigtreasure_fsmhost_test COMMAND p2_bigtreasure_fsmhost_test)

add_executable(p2_bigtreasure_host_test
    tools/p2_bigtreasure_host_test.cpp
    ${P2_BIGTREASURE_TEST_DEPS})
target_include_directories(p2_bigtreasure_host_test PRIVATE pc_port)
target_compile_options(p2_bigtreasure_host_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bigtreasure_host_test COMMAND p2_bigtreasure_host_test)

add_executable(p2_bigtreasure_motion_test
    tools/p2_bigtreasure_motion_test.cpp
    ${P2_BIGTREASURE_TEST_DEPS})
target_include_directories(p2_bigtreasure_motion_test PRIVATE pc_port)
target_compile_options(p2_bigtreasure_motion_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bigtreasure_motion_test COMMAND p2_bigtreasure_motion_test)
# Lane 31 (#443 / #175) engine-free Waterwraith/Tyre tests. -UNDEBUG keeps the
# assert-based fixtures active in the Release native gate.
add_executable(p2_waterwraith_policy_test
    tools/p2_waterwraith_test.cpp
    pc_port/pc_p2_waterwraith.cpp)
target_include_directories(p2_waterwraith_policy_test PRIVATE pc_port)
target_compile_options(p2_waterwraith_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_waterwraith_policy_test COMMAND p2_waterwraith_policy_test)

add_executable(p2_waterwraith_actor_test
    tools/p2_waterwraith_actor_test.cpp
    pc_port/pc_p2_waterwraith_actor.cpp
    pc_port/pc_p2_waterwraith.cpp)
target_include_directories(p2_waterwraith_actor_test PRIVATE pc_port)
target_compile_options(p2_waterwraith_actor_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_waterwraith_actor_test COMMAND p2_waterwraith_actor_test)

add_executable(p2_waterwraith_attack_policy_test
    tools/p2_waterwraith_attack_policy_test.cpp)
target_include_directories(p2_waterwraith_attack_policy_test PRIVATE pc_port)
target_compile_options(p2_waterwraith_attack_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_waterwraith_attack_policy_test COMMAND p2_waterwraith_attack_policy_test)
add_executable(p2_armor_events_test
    tools/test_p2_armor_events.cpp)
target_include_directories(p2_armor_events_test PRIVATE pc_port)
target_compile_options(p2_armor_events_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_armor_events_test COMMAND p2_armor_events_test)

add_executable(p2_billboard_test
    tools/test_p2_billboard.cpp)
target_include_directories(p2_billboard_test PRIVATE pc_port)
target_compile_options(p2_billboard_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_billboard_test COMMAND p2_billboard_test)

add_executable(p2_sarai_captor_test tools/p2_sarai_captor_test.cpp)
target_include_directories(p2_sarai_captor_test PRIVATE pc_port)
target_compile_options(p2_sarai_captor_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_sarai_captor_test COMMAND p2_sarai_captor_test)

# Lane 30 (#242) dedicated captor spawn-identity test. Engine-free: it asserts
# the identity/selection seam; the constant is static_asserted against
# TEKI_P2Demon in the engine build (pc_port/pc_p2_demon_host.cpp).
add_executable(p2_demon_identity_test tools/p2_demon_identity_test.cpp)
target_include_directories(p2_demon_identity_test PRIVATE pc_port)
target_compile_options(p2_demon_identity_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_demon_identity_test COMMAND p2_demon_identity_test)



add_executable(pc_render_phase_test
    pc_port/timing/pc_render_phase_test.cpp
    pc_port/timing/pc_render_phase.cpp)
target_compile_options(pc_render_phase_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_render_phase_test COMMAND pc_render_phase_test)

add_executable(pc_visual_snapshot_test
    pc_port/timing/pc_visual_snapshot_test.cpp
    pc_port/timing/pc_visual_snapshot.cpp)
target_compile_options(pc_visual_snapshot_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_visual_snapshot_test COMMAND pc_visual_snapshot_test)

add_executable(pc_camera_snapshot_test
    pc_port/timing/pc_camera_snapshot_test.cpp
    pc_port/timing/pc_camera_snapshot.cpp)
target_compile_options(pc_camera_snapshot_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_camera_snapshot_test COMMAND pc_camera_snapshot_test)

add_executable(pc_visual_runtime_test
    pc_port/timing/pc_visual_runtime_test.cpp
    pc_port/timing/pc_visual_runtime.cpp
    pc_port/timing/pc_render_phase.cpp
    pc_port/timing/pc_visual_snapshot.cpp)
target_compile_options(pc_visual_runtime_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_visual_runtime_test COMMAND pc_visual_runtime_test)

add_executable(pc_tev_shader_test
    pc_port/gl/pc_tev_shader_test.cpp
    pc_port/gl/pc_tev_shader.cpp
)
target_include_directories(pc_tev_shader_test PRIVATE pc_port/gl)
target_compile_options(pc_tev_shader_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_tev_shader_test COMMAND pc_tev_shader_test)

# Post-process shader generation (no GL context needed)
add_executable(pc_postprocess_test
    pc_port/gl/pc_postprocess_test.cpp
    pc_port/gl/pc_postprocess.cpp
)
target_include_directories(pc_postprocess_test PRIVATE pc_port/gl)
target_compile_options(pc_postprocess_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_postprocess_test COMMAND pc_postprocess_test)

add_executable(pc_render_packet_test
    pc_port/timing/pc_render_packet_test.cpp
    pc_port/timing/pc_render_packet.cpp)
target_compile_options(pc_render_packet_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_render_packet_test COMMAND pc_render_packet_test)

add_executable(pc_tick_profiler_test
    pc_port/timing/pc_tick_profiler_test.cpp
    pc_port/timing/pc_tick_profiler.cpp)
target_include_directories(pc_tick_profiler_test PRIVATE pc_port/timing)
target_compile_options(pc_tick_profiler_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_tick_profiler_test COMMAND pc_tick_profiler_test)

message(STATUS "")
message(STATUS "╔══════════════════════════════════════════╗")
message(STATUS "║   Pikmin PC Port - Build Configuration   ║")
message(STATUS "╠══════════════════════════════════════════╣")
message(STATUS "║   Version:  USA Rev 1 (GPIE01_01)       ║")
message(STATUS "║   Graphics: Native GX → OpenGL          ║")
message(STATUS "║   Audio:    SDL mixer/STX; JAudio WIP   ║")
message(STATUS "║   Input:    Native SDL keyboard/gamepad ║")
message(STATUS "╚══════════════════════════════════════════╝")
message(STATUS "")

if(PIKMIN_NATIVE_JAUDIO)
    add_test(NAME pc_jaudio_integration_test COMMAND pikmin_pc --audio-self-test)
    set_tests_properties(pc_jaudio_integration_test PROPERTIES
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}" TIMEOUT 30
        SKIP_RETURN_CODE 77 LABELS "game-assets")
endif()

# Standalone adapter harness; exercises real file I/O without game assets.
add_executable(pc_randomizer_probe pc_port/pc_randomizer_probe.cpp pc_port/pc_randomizer.cpp)

# Only the isolated diagnostic build includes scripted stock/death fixtures.
option(PIKMIN_RANDOMIZER_TEST_HOOKS "Enable standalone scripted gameplay test fixtures" OFF)
if(PIKMIN_RANDOMIZER_TEST_HOOKS)
    set_property(SOURCE src/plugPikiKando/gameCoreSection.cpp APPEND PROPERTY
        COMPILE_DEFINITIONS PIKMIN_RANDOMIZER_TEST_HOOKS=1)
endif()

# Integration gates: keep assertions active for these engine-free contracts.
foreach(policy IN ITEMS species_schema hazard_reaction hazard_emitter cave_transfer captain_roster squad_policy)
    add_executable(p2_${policy}_test tools/test_p2_${policy}.cpp)
    target_include_directories(p2_${policy}_test PRIVATE pc_port)
    target_compile_options(p2_${policy}_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
    add_test(NAME p2_${policy}_test COMMAND p2_${policy}_test)
endforeach()
add_executable(p2_groink_strike_test tools/p2_groink_strike_test.cpp
    pc_port/pc_p2_groink_strike.cpp pc_port/pc_p2_groink_hit.cpp pc_port/pc_p2_projectile_receiver.cpp)
target_include_directories(p2_groink_strike_test PRIVATE pc_port)
target_compile_options(p2_groink_strike_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_strike_test COMMAND p2_groink_strike_test)
add_executable(p2_bigtreasure_save_test tools/p2_bigtreasure_save_test.cpp pc_port/pc_p2_bigtreasure_save.cpp ${P2_BIGTREASURE_TEST_DEPS})
target_include_directories(p2_bigtreasure_save_test PRIVATE pc_port)
target_compile_options(p2_bigtreasure_save_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_bigtreasure_save_test COMMAND p2_bigtreasure_save_test)

add_executable(p2_receipt_host_test tools/p2_receipt_host_test.cpp pc_port/pc_p2_receipt_host.cpp)
target_include_directories(p2_receipt_host_test PRIVATE pc_port)
target_compile_options(p2_receipt_host_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_receipt_host_test COMMAND p2_receipt_host_test)

foreach(policy IN ITEMS demon_captor demon_escape demon_pose sarai_fsm sarai_policy fuefuki_follow fuefuki_follow_binding)
    add_executable(p2_${policy}_test tools/p2_${policy}_test.cpp)
    target_include_directories(p2_${policy}_test PRIVATE pc_port)
    target_compile_options(p2_${policy}_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
    add_test(NAME p2_${policy}_test COMMAND p2_${policy}_test)
endforeach()
add_executable(p2_fuefuki_motion_test tools/p2_fuefuki_motion_test.cpp pc_port/pc_p2_fuefuki_motion.cpp)
target_include_directories(p2_fuefuki_motion_test PRIVATE pc_port)
target_compile_options(p2_fuefuki_motion_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_fuefuki_motion_test COMMAND p2_fuefuki_motion_test)
set(P2_KABUTO_TEST_DEPS pc_port/pc_p2_kabuto_binding.cpp pc_port/pc_p2_kabuto_events.cpp pc_port/pc_p2_kabuto_muzzle.cpp pc_port/pc_p2_kabuto_cannon.cpp pc_port/pc_p2_cannon_stone.cpp)
foreach(policy IN ITEMS kabuto_muzzle kabuto_chain kabuto_binding)
    add_executable(p2_${policy}_test tools/p2_${policy}_test.cpp ${P2_KABUTO_TEST_DEPS})
    target_include_directories(p2_${policy}_test PRIVATE pc_port)
    target_compile_options(p2_${policy}_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
    add_test(NAME p2_${policy}_test COMMAND p2_${policy}_test)
endforeach()

foreach(policy IN ITEMS bigtreasure_ordinary bigtreasure_animclock bigtreasure_natural bigtreasure_elements)
    add_executable(p2_${policy}_test tools/p2_${policy}_test.cpp ${P2_BIGTREASURE_TEST_DEPS}
        pc_port/pc_p2_bigtreasure_ordinary.cpp pc_port/pc_p2_bigtreasure_animclock.cpp
        pc_port/pc_p2_bigtreasure_motion.cpp pc_port/pc_p2_bigtreasure_elements.cpp)
    target_include_directories(p2_${policy}_test PRIVATE pc_port)
    target_compile_options(p2_${policy}_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
    add_test(NAME p2_${policy}_test COMMAND p2_${policy}_test)
endforeach()

# Groink submitted policy dependencies; arena remains opt-in.
add_executable(p2_groink_test tools/p2_groink_test.cpp pc_port/pc_p2_groink.cpp)
target_include_directories(p2_groink_test PRIVATE pc_port)
target_compile_options(p2_groink_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_test COMMAND p2_groink_test)
add_executable(p2_groink_attack_test tools/p2_groink_attack_test.cpp pc_port/pc_p2_groink_attack.cpp pc_port/pc_p2_groink.cpp)
target_include_directories(p2_groink_attack_test PRIVATE pc_port)
target_compile_options(p2_groink_attack_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_attack_test COMMAND p2_groink_attack_test)
add_executable(p2_groink_clock_test tools/p2_groink_clock_test.cpp )
target_include_directories(p2_groink_clock_test PRIVATE pc_port)
target_compile_options(p2_groink_clock_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_clock_test COMMAND p2_groink_clock_test)
add_executable(p2_groink_events_test tools/p2_groink_events_test.cpp pc_port/pc_p2_groink_attack.cpp pc_port/pc_p2_groink.cpp)
target_include_directories(p2_groink_events_test PRIVATE pc_port)
target_compile_options(p2_groink_events_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_events_test COMMAND p2_groink_events_test)
add_executable(p2_groink_target_test tools/p2_groink_target_test.cpp pc_port/pc_p2_groink_target.cpp)
target_include_directories(p2_groink_target_test PRIVATE pc_port)
target_compile_options(p2_groink_target_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_target_test COMMAND p2_groink_target_test)
add_executable(p2_groink_volley_test tools/p2_groink_volley_test.cpp pc_port/pc_p2_groink_volley.cpp pc_port/pc_p2_groink.cpp)
target_include_directories(p2_groink_volley_test PRIVATE pc_port)
target_compile_options(p2_groink_volley_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_volley_test COMMAND p2_groink_volley_test)
add_executable(p2_groink_hit_test tools/p2_groink_hit_test.cpp pc_port/pc_p2_groink_hit.cpp)
target_include_directories(p2_groink_hit_test PRIVATE pc_port)
target_compile_options(p2_groink_hit_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_hit_test COMMAND p2_groink_hit_test)

# Opt-in Purple and White policy regressions.
add_executable(p2_purple_direct_policy_test tools/p2_purple_direct_policy_test.cpp)
target_include_directories(p2_purple_direct_policy_test PRIVATE pc_port)
target_compile_options(p2_purple_direct_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_purple_direct_policy_test COMMAND p2_purple_direct_policy_test)
add_executable(p2_purple_impact_policy_test tools/p2_purple_impact_policy_test.cpp)
target_include_directories(p2_purple_impact_policy_test PRIVATE pc_port)
target_compile_options(p2_purple_impact_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_purple_impact_policy_test COMMAND p2_purple_impact_policy_test)
add_executable(p2_white_poison_policy_test tools/test_p2_white_poison_policy.cpp)
target_include_directories(p2_white_poison_policy_test PRIVATE pc_port)
target_compile_options(p2_white_poison_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_white_poison_policy_test COMMAND p2_white_poison_policy_test)

add_executable(p2_purple_flight_actual_test tools/test_p2_purple_flight_actual.cpp pc_port/pc_p2_purple_flight.cpp)
target_include_directories(p2_purple_flight_actual_test BEFORE PRIVATE tools/p2_purple_flight_stubs pc_port)
target_compile_options(p2_purple_flight_actual_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_purple_flight_actual_test COMMAND p2_purple_flight_actual_test)
