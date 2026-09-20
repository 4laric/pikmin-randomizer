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
    pc_port/pc_p2_sarai_capture_bridge.cpp
    pc_port/pc_p2_sarai_manager.cpp
    pc_port/pc_p2_generated_placement.cpp
    pc_port/pc_p2_campaign_goal_probe.cpp
    pc_port/pc_bbft.cpp
    # Challenge host-mode engine runtime bridge (#722, ported from #710
    # db245877; #186 review before shared-line landing): the per-tick runtime
    # bridge plus the landed host-state module, linked into pikmin_pc so the
    # engine drives syncTick from live facts during a challenge boot.
    # pc_bbft_test keeps linking: pc_bbft.cpp stays engine-free (null-by-default
    # hook) and neither TU is added to that small target.
    pc_port/pc_p2_challenge_runtime.cpp
    # Bomb birth hook call site (#732; #186 review before shared-line
    # landing): the #726/#616 manager + payload TUs plus the new
    # research-mirror call-site TU that strong-defines
    # pc_p2_bomb_birth_hook_notify in the production graph and routes the
    # retail Bomb-family IDs (36/93) to pc_p2_bomb_engine_birth_poll.
    # No GLOB covers pikmin2-research, so the call-site TU is listed
    # explicitly; neither TU is added to engine-free test targets.
    pc_port/pc_p2_bomb_mgr_birth.cpp
    pc_port/pc_p2_bomb_payload_actor.cpp
    pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp
    pc_port/pc_p2_challenge_mode.cpp
    # Overworld session save serializer (#736; #186 review before shared-line
    # landing): the save/load/verify module, linked into pikmin_pc so the
    # engine serializes the session on the pc_bbft session path. The pc_bbft
    # call site is weak-linked (null-by-default), so pc_bbft_test keeps
    # linking without this TU.
    pc_port/pc_p2_overworld_save.cpp
    # Challenge persistence recorder module (#725, membership for #713; #186
    # review before shared-line landing). Added here so the production
    # pikmin_pc target resolves the pc_bbft.cpp weak references and the engine
    # emits its 7 challenge-persistence probe markers; the #718 callsite fixture
    # links this same object rather than a fixture-local copy.
    pc_port/pc_p2_challenge_persistence.cpp
    pc_port/pc_p2_preview.cpp
    pc_port/pc_p2_captain.cpp
    pc_port/pc_p2_second_captain.cpp
    pc_port/pc_p2_economy.cpp
    pc_port/pc_p2_teki_lifetime.cpp
    pc_port/pc_p2_placement_probe.cpp
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
    pc_port/pc_p2_cave_generate.cpp
    pc_port/pc_p2_cave_generator.cpp
    pc_port/pc_p2_cave_rooms.cpp
    pc_port/pc_p2_cave_geometry.cpp
    pc_port/pc_p2_cave_items.cpp
    pc_port/pc_p2_cave_bud_actor.cpp
    pc_port/pc_p2_cave_carry.cpp
    pc_port/pc_p2_enemy.cpp
    pc_port/pc_p2_sheargrub.cpp
    pc_port/pc_p2_kochappy.cpp
    pc_port/pc_p2_dwarf_orange.cpp
    pc_port/pc_p2_bluechappy.cpp
    pc_port/pc_p2_kochappy_fsm.cpp
    pc_port/pc_p2_breadbug_visual.cpp
    pc_port/pc_p2_giant_breadbug_visual.cpp
    pc_port/pc_p2_bulblax_visual.cpp
    pc_port/pc_p2_queen.cpp
    pc_port/pc_p2_king.cpp
    pc_port/pc_p2_king_teki.cpp
    pc_port/pc_p2_queen_teki.cpp
    pc_port/pc_p2_breadbug_actor.cpp
    pc_port/pc_p2_breadbug_contest_host.cpp
    pc_port/pc_p2_giant_breadbug_actor.cpp
    pc_port/pc_p2_frog.cpp
    pc_port/pc_p2_kogane.cpp
    pc_port/pc_p2_mamuta.cpp
    pc_port/pc_p2_mamuta_rules.cpp
    pc_port/pc_p2_tank.cpp
    pc_port/pc_p2_hiba.cpp
    pc_port/pc_p2_flora_actor.cpp
    pc_port/pc_p2_receipt_host.cpp
    pc_port/pc_p2_delivery_host.cpp
    pc_port/pc_p2_pom.cpp
    pc_port/pc_p2_candypop.cpp
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
    pc_port/pc_p2_otakara.cpp
    pc_port/pc_p2_otakara_fx.cpp
    pc_port/pc_p2_elecbug.cpp
    pc_port/pc_p2_tamago.cpp
    pc_port/pc_p2_imomushi.cpp
    pc_port/pc_p2_hana.cpp
    pc_port/pc_p2_tadpole.cpp
    pc_port/pc_p2_mar.cpp
    pc_port/pc_p2_mar_receipt.cpp
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
pc_port/pc_p2_kabuto_host.cpp
pc_port/pc_p2_projectile_host.cpp
    pc_port/pc_p2_rock_hazard.cpp
    pc_port/pc_p2_rock_host.cpp
    pc_port/pc_p2_projectile_receiver.cpp
    pc_port/pc_p2_projectile_engine_receiver.cpp
    pc_port/pc_p2_groink.cpp
    pc_port/pc_p2_groink_arena.cpp
    pc_port/pc_p2_groink_attack.cpp
    pc_port/pc_p2_groink_map_trace.cpp
    pc_port/pc_p2_groink_target.cpp
    pc_port/pc_p2_groink_volley.cpp
    pc_port/pc_p2_groink_hit.cpp
    pc_port/pc_p2_groink_strike.cpp
    pc_port/pc_p2_groink_carcass.cpp
    pc_port/pc_p2_groink_teki.cpp
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
    pc_port/pc_p2_bombsarai_teki.cpp
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
    pc_port/pc_p2_bigtreasure_receiver.cpp
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
# Lane 29 replacement-main runtime fixture (#243). Built as an ordinary target so
# the lane wrapper (`build_lane.py l29 --target p2_kurage_runtime`) produces it
# under the normal build semaphore; it runs the same engine as pikmin_pc with the
# kurage scenario main (tools/p2_kurage_runtime.cpp) instead of pc_main.cpp.
set(P2_KURAGE_RUNTIME_SOURCES ${PC_PORT_SOURCES})
list(REMOVE_ITEM P2_KURAGE_RUNTIME_SOURCES pc_port/pc_main.cpp)
list(APPEND P2_KURAGE_RUNTIME_SOURCES tools/p2_kurage_runtime.cpp)
add_executable(p2_kurage_runtime ${P2_KURAGE_RUNTIME_SOURCES})
target_include_directories(p2_kurage_runtime PRIVATE tools)
target_compile_options(p2_kurage_runtime PRIVATE ${NATIVE_COMPILE_OPTIONS})
target_link_libraries(p2_kurage_runtime PRIVATE pikmin_legacy)
if(WIN32)
    add_library(bbft_transport STATIC pc_port/bbft/bbft_transport.c)
    target_link_libraries(pikmin_pc PRIVATE bbft_transport ws2_32)
    target_link_libraries(p2_kurage_runtime PRIVATE bbft_transport ws2_32)
    add_executable(pc_bbft_test pc_port/pc_bbft_test.cpp pc_port/pc_bbft.cpp pc_port/pc_randomizer.cpp pc_port/pc_p2_delivery_host.cpp)
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
set(PIKMIN_OPTIMIZED_TARGETS pikmin_pc pikmin_legacy p2_kurage_runtime)

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
    target_link_libraries(p2_kurage_runtime PRIVATE ${SDL2_LIBRARIES} opengl32)
else()
    target_link_libraries(pikmin_pc PRIVATE m ${SDL2_LIBRARIES} OpenGL::GL X11)
    target_link_libraries(p2_kurage_runtime PRIVATE m ${SDL2_LIBRARIES} OpenGL::GL X11)
endif()
# Export symbol names so the diagnostic backtrace in pc_gfx.cpp prints function
# names rather than bare addresses. Costs nothing at runtime.
#
# GNU-ld only: MinGW rejects the flag outright, and the backtrace it serves is
# compiled out on Windows anyway (glibc's execinfo.h has no equivalent there).
if (NOT WIN32)
    target_link_options(pikmin_pc PRIVATE -rdynamic)
    target_link_options(p2_kurage_runtime PRIVATE -rdynamic)
else()
    # SDL2's CMake package links -mwindows, which hides the console and with it
    # every printf the port uses to report what it is doing. Keep a console on
    # the game so a failed launch says why instead of vanishing. The launcher
    # stays windowed: it talks through native dialogs.
    target_link_options(pikmin_pc PRIVATE -mconsole)
    target_link_options(p2_kurage_runtime PRIVATE -mconsole)
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

# P2 Challenge host-state unit test (#651), landed per #676. Guard include dir
# is an explicit, validated cache PATH (per the pinned #651/#186 review): it
# defaults to the root-relative scripts/ when present, and private builds pass
# -DP2_CHALLENGE_GUARD_INCLUDE_DIR=<canonical scripts dir>. No vendored copy.
set(P2_CHALLENGE_GUARD_INCLUDE_DIR "${CMAKE_SOURCE_DIR}/../scripts" CACHE PATH
    "Directory containing the canonical p2_fixture_captain_guard.h")
if(NOT EXISTS "${P2_CHALLENGE_GUARD_INCLUDE_DIR}/p2_fixture_captain_guard.h")
    message(FATAL_ERROR
        "p2_fixture_captain_guard.h not found in ${P2_CHALLENGE_GUARD_INCLUDE_DIR}; "
        "pass -DP2_CHALLENGE_GUARD_INCLUDE_DIR=<canonical scripts dir>")
endif()
add_executable(p2_challenge_mode_fixture
    tools/p2_challenge_mode_fixture.cpp
    pc_port/pc_p2_challenge_mode.cpp)
target_include_directories(p2_challenge_mode_fixture PRIVATE
    pc_port
    ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
target_compile_options(p2_challenge_mode_fixture PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_challenge_mode_fixture COMMAND p2_challenge_mode_fixture)

# P2 challenge boot fixture with argv stage select (#672 / lane rd-p2-fixture-cmake #674).
# Registration-only: the tool TU rides along via include of the module TU, so
# only the tool source is listed. Guard header comes from the validated
# P2_CHALLENGE_GUARD_INCLUDE_DIR cache PATH above (no vendored copy).
add_executable(p2_challenge_boot_fixture
    tools/p2_challenge_boot_fixture.cpp)
target_include_directories(p2_challenge_boot_fixture PRIVATE
    pc_port
    ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
target_compile_options(p2_challenge_boot_fixture PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_challenge_boot_fixture COMMAND p2_challenge_boot_fixture)

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
add_executable(p2_mar_receipt_registration_test
    tools/p2_mar_receipt_registration_test.cpp
    pc_port/pc_p2_mar_receipt.cpp)
target_include_directories(p2_mar_receipt_registration_test PRIVATE pc_port)
target_compile_options(p2_mar_receipt_registration_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_mar_receipt_registration_test COMMAND p2_mar_receipt_registration_test)

# Visible Otakara discharge attacks (#170, rd-p2-otakara-fx). Engine-free
# mapping + slot-lifecycle test; the game TU compiles with the real
# effectMgr seam, the test with P2_OTAKARA_FX_NO_ENGINE stubs.
add_executable(p2_otakara_fx_test
    tools/test_p2_otakara_fx.cpp
    pc_port/pc_p2_otakara_fx.cpp)
target_include_directories(p2_otakara_fx_test PRIVATE pc_port)
target_compile_definitions(p2_otakara_fx_test PRIVATE P2_OTAKARA_FX_NO_ENGINE)
target_compile_options(p2_otakara_fx_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_otakara_fx_test COMMAND p2_otakara_fx_test)

# Lane 35 cave unit-pool partition + phased trunk growth (#474). Header-only
# engine-free policy; no shared generator source is claimed or ported here.
add_executable(p2_cave_growth_test
    tools/p2_cave_growth_test.cpp)
target_include_directories(p2_cave_growth_test PRIVATE pc_port)
target_compile_options(p2_cave_growth_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_cave_growth_test COMMAND p2_cave_growth_test)

# Lane 41 cave-generator port (#480). One-consumer gate over the header-only
# generator plus the engine-linked facade source (pc_p2_cave_generator.cpp).
add_executable(p2_cave_generator_test
    tools/p2_cave_generator_test.cpp
    pc_port/pc_p2_cave_generator.cpp)
target_include_directories(p2_cave_generator_test PRIVATE pc_port)
target_compile_options(p2_cave_generator_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_cave_generator_test COMMAND p2_cave_generator_test)

# Lane 44 proxy cave-room instantiation (#482). Header-only engine-free logic;
# the engine glue (pc_p2_cave_rooms.cpp) is linked into pikmin_pc separately.
add_executable(p2_cave_rooms_test
tools/p2_cave_rooms_test.cpp)
target_include_directories(p2_cave_rooms_test PRIVATE pc_port)
target_compile_options(p2_cave_rooms_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_cave_rooms_test COMMAND p2_cave_rooms_test)

# Lane 45 real cave-unit geometry + electric-gate actor (#483). Header-only
# engine-free plan logic; the engine glue (pc_p2_cave_geometry.cpp) is linked
# into pikmin_pc separately.
add_executable(p2_cave_geometry_test
    tools/p2_cave_geometry_test.cpp)
target_include_directories(p2_cave_geometry_test PRIVATE pc_port)
target_compile_options(p2_cave_geometry_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_cave_geometry_test COMMAND p2_cave_geometry_test)

# Lane 46 (#484): physical cave-item placement gate (header-only; the engine
# glue pc_p2_cave_items.cpp is linked into pikmin_pc separately).
add_executable(p2_cave_items_test
    tools/p2_cave_items_test.cpp)
target_include_directories(p2_cave_items_test PRIVATE pc_port)
target_compile_options(p2_cave_items_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_cave_items_test COMMAND p2_cave_items_test)

# Lane 48 (#486): seeded Candypop bud actor instantiation gate (header-only;
# the engine glue pc_p2_cave_bud_actor.cpp is linked into pikmin_pc separately).
add_executable(p2_cave_bud_test
    tools/p2_cave_bud_test.cpp)
target_include_directories(p2_cave_bud_test PRIVATE pc_port)
target_compile_options(p2_cave_bud_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_cave_bud_test COMMAND p2_cave_bud_test)
# Lane 50 (#488): carry-blocking gate (header-only engine-free plan/verdict; the
# engine glue pc_p2_cave_carry.cpp is linked into pikmin_pc separately).
add_executable(p2_cave_carry_test
    tools/p2_cave_carry_test.cpp)
target_include_directories(p2_cave_carry_test PRIVATE pc_port)
target_compile_options(p2_cave_carry_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_cave_carry_test COMMAND p2_cave_carry_test)

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

# rd-snakecrow-gate (#174): SnakeCrow/SnakeWhole emerged-vulnerability gate.
# Header-only engine-free predicate shared with pc_p2_snakejoint_invulnerable;
# the engine glue (pc_p2_snakejoint.cpp) is linked into pikmin_pc separately.
add_executable(p2_snakejoint_gate_test
    tools/test_p2_snakejoint_gate.cpp)
target_include_directories(p2_snakejoint_gate_test PRIVATE pc_port)
target_compile_options(p2_snakejoint_gate_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_snakejoint_gate_test COMMAND p2_snakejoint_gate_test)

# rd-onikurage-policy (#243): the shared OniKurage (Greater Spotted Jellyfloat)
# captain-capture/Drop sources shipped on the approved line without ctest
# registration. Register the existing engine-free suite so `ctest -R onikurage`
# exercises it; no policy code is (re)added here.
add_executable(p2_onikurage_fsm_test
    tools/p2_onikurage_fsm_test.cpp)
target_include_directories(p2_onikurage_fsm_test PRIVATE pc_port)
target_compile_options(p2_onikurage_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_onikurage_fsm_test COMMAND p2_onikurage_fsm_test)

add_executable(p2_onikurage_mouth_test
    tools/test_p2_onikurage_mouth.cpp
    pc_port/pc_p2_onikurage_mouth.cpp)
target_include_directories(p2_onikurage_mouth_test PRIVATE pc_port)
target_compile_options(p2_onikurage_mouth_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_onikurage_mouth_test COMMAND p2_onikurage_mouth_test)

add_executable(p2_onikurage_teki_policy_test
    tools/test_p2_onikurage_teki_policy.cpp)
target_include_directories(p2_onikurage_teki_policy_test PRIVATE pc_port)
target_compile_options(p2_onikurage_teki_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_onikurage_teki_policy_test COMMAND p2_onikurage_teki_policy_test)

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

# Animated capture-joint transform + payload follow gate (kamu_jnt1 stand-in).
add_executable(p2_bombsarai_joint_test
    tools/p2_bombsarai_joint_test.cpp
    pc_port/pc_p2_bombsarai_bomb.cpp)
target_include_directories(p2_bombsarai_joint_test PRIVATE pc_port)
target_compile_options(p2_bombsarai_joint_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bombsarai_joint_test COMMAND p2_bombsarai_joint_test)

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

add_executable(p2_fuefuki_owner_death_test tools/p2_fuefuki_owner_death_test.cpp)
target_include_directories(p2_fuefuki_owner_death_test PRIVATE pc_port)
target_compile_options(p2_fuefuki_owner_death_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_fuefuki_owner_death_test COMMAND p2_fuefuki_owner_death_test)

# Lane 28 Fuefuki natural-combat real-GL fixture (#245): compile-only isolated
# target. Its replacement-main executable is produced by
# scripts/build_pikmin2_fixture.py against a completed pikmin_pc build; this
# object target only proves the full-app fixture source still compiles against
# the engine headers (SDL2/GL/App/...) when the lane edits it.
add_library(p2_fuefuki_combat_runtime_compile OBJECT tools/p2_fuefuki_combat_runtime.cpp)
target_include_directories(p2_fuefuki_combat_runtime_compile PRIVATE pc_port ${SDL2_INCLUDE_DIRS})
target_compile_options(p2_fuefuki_combat_runtime_compile PRIVATE ${NATIVE_COMPILE_OPTIONS} -Wno-unused-parameter)

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

add_executable(p2_hana_events_test
    tools/test_p2_hana_events.cpp)
target_include_directories(p2_hana_events_test PRIVATE pc_port)
target_compile_options(p2_hana_events_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_hana_events_test COMMAND p2_hana_events_test)

add_executable(p2_catfish_events_test
    tools/test_p2_catfish_events.cpp)
target_include_directories(p2_catfish_events_test PRIVATE pc_port)
target_compile_options(p2_catfish_events_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_catfish_events_test COMMAND p2_catfish_events_test)

add_executable(p2_billboard_test
    tools/test_p2_billboard.cpp)
target_include_directories(p2_billboard_test PRIVATE pc_port)
target_compile_options(p2_billboard_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_billboard_test COMMAND p2_billboard_test)

add_executable(p2_specular_dir_test
    tools/test_p2_specular_dir.cpp)
target_include_directories(p2_specular_dir_test PRIVATE pc_port)
target_compile_options(p2_specular_dir_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_specular_dir_test COMMAND p2_specular_dir_test)

# rd-p2-material-tint (#207) per-species batch-2 tint probe. Engine-free: the
# tint table is inline in pc_port/pc_p2_batch2.h, so the test needs only its own
# source plus the pc_port include dir.
add_executable(p2_batch2_tint_test
    tools/test_p2_batch2_tint.cpp)
target_include_directories(p2_batch2_tint_test PRIVATE pc_port)
target_compile_options(p2_batch2_tint_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_batch2_tint_test COMMAND p2_batch2_tint_test)

# Lane 30 (#242) standalone policy tests. The drop/host-clock and Sarai
# captor/lifecycle/identity harnesses are dependency-free headers: a test source
# and the pc_port include dir are all they need. (demon_captor/demon_escape and
# sarai_fsm/sarai_policy are already registered by the policy foreach below.)
add_executable(p2_demon_drop_policy_test tools/p2_demon_drop_policy_test.cpp)
target_include_directories(p2_demon_drop_policy_test PRIVATE pc_port)
target_compile_options(p2_demon_drop_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_demon_drop_policy_test COMMAND p2_demon_drop_policy_test)

add_executable(p2_demon_host_clock_test tools/p2_demon_host_clock_test.cpp)
target_include_directories(p2_demon_host_clock_test PRIVATE pc_port)
target_compile_options(p2_demon_host_clock_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_demon_host_clock_test COMMAND p2_demon_host_clock_test)

add_executable(p2_sarai_captor_test tools/p2_sarai_captor_test.cpp)
target_include_directories(p2_sarai_captor_test PRIVATE pc_port)
target_compile_options(p2_sarai_captor_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_sarai_captor_test COMMAND p2_sarai_captor_test)

# Lane 30 (#457/#242) Sarai capture-lifecycle test. Engine-free: the shared
# escape window and the lane's capture/detach model are dependency-free headers.
add_executable(p2_sarai_captor_lifecycle_test tools/p2_sarai_captor_lifecycle_test.cpp)
target_include_directories(p2_sarai_captor_lifecycle_test PRIVATE pc_port)
target_compile_options(p2_sarai_captor_lifecycle_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_sarai_captor_lifecycle_test COMMAND p2_sarai_captor_lifecycle_test)

# rd-p2ap-sarai (#439) Sarai seed-bridge campaign test. Engine-free: stub
# engine headers shadow the real ones (BEFORE pc_port), so the real
# pc_p2_generated_placement.cpp compiles against doubles (same mechanics as
# p2_purple_flight_actual_test). The Sarai dynamic binder is doubled with its
# real claim contract; the real binder ships in pc_p2_sarai_manager.cpp.
add_executable(p2_sarai_seed_bridge_test tools/test_p2_sarai_campaign.cpp
    pc_port/pc_p2_generated_placement.cpp)
target_include_directories(p2_sarai_seed_bridge_test BEFORE PRIVATE tools/p2_sarai_campaign_stubs pc_port)
target_compile_options(p2_sarai_seed_bridge_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_sarai_seed_bridge_test COMMAND p2_sarai_seed_bridge_test)

# rd-p2-sarai-campaign (#457) Sarai campaign capture/teardown proof. Engine-free:
# the two stub dirs shadow the real Piki/Creature/CollPart/Interaction and
# Generator/teki headers (BEFORE pc_port), so the SHIPPED
# pc_p2_sarai_capture_bridge.cpp is compiled and driven directly against
# campaign-shaped hosts (pc_p2_campaign_policy.h vehicle + pc_p2_campaign_actor.h
# token). Asserts a capture and a teardown strand no Pikmin.
add_executable(p2_sarai_campaign_test tools/p2_sarai_campaign_test.cpp
    pc_port/pc_p2_sarai_capture_bridge.cpp)
target_include_directories(p2_sarai_campaign_test BEFORE PRIVATE
    tools/p2_sarai_capture_stubs tools/p2_sarai_campaign_stubs pc_port)
target_compile_options(p2_sarai_campaign_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_sarai_campaign_test COMMAND p2_sarai_campaign_test)

# rd-p2-sarai-campaign-behavior (#834) Sarai campaign targeting/reacquisition
# proof. Engine-free: header-only policy/capture/fsm suites plus the SHIPPED
# capture bridge against the same stub dirs as p2_sarai_campaign_test, and
# the roster header. Pins retail eligibility, nearest-first selection,
# bounded FSM reacquisition, receivers, teardown and the unchanged source-23
# binding; optional log mode classifies a campaign-behavior run
# (shared-review registration only).
add_executable(p2_sarai_campaign_behavior_test tools/p2_sarai_campaign_behavior_test.cpp
    pc_port/pc_p2_sarai_capture_bridge.cpp)
target_include_directories(p2_sarai_campaign_behavior_test BEFORE PRIVATE
    tools/p2_sarai_capture_stubs tools/p2_sarai_campaign_stubs pc_port)
target_compile_options(p2_sarai_campaign_behavior_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_sarai_campaign_behavior_test COMMAND p2_sarai_campaign_behavior_test)

# Lane 30 (#242) dedicated captor spawn-identity test. Engine-free: it asserts
# the identity/selection seam; the constant is static_asserted against
# TEKI_P2Demon in the engine build (pc_port/pc_p2_demon_host.cpp).
add_executable(p2_demon_identity_test tools/p2_demon_identity_test.cpp)
target_include_directories(p2_demon_identity_test PRIVATE pc_port)
target_compile_options(p2_demon_identity_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_demon_identity_test COMMAND p2_demon_identity_test)

# rd-captain-kurage (#130): port of the codex/p2-lane12-review captain/Kurage
# review fixes onto the line captain API. The adapter and policy harnesses are
# engine-free (header + doubles only). The Kurage receiver harness is a single
# TU: it drives the production receiver + captain glue against the stub engine
# doubles (tools/kurage_receiver_stubs/engine.h) with the real engine headers
# neutralized by include-guard defines inside the test source.
add_executable(p2_captain_adapter_test tools/test_p2_captain_adapter.cpp)
target_include_directories(p2_captain_adapter_test PRIVATE pc_port)
target_compile_options(p2_captain_adapter_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_captain_adapter_test COMMAND p2_captain_adapter_test)

add_executable(p2_captain_policy_test tools/test_p2_captain_policy.cpp)
target_include_directories(p2_captain_policy_test PRIVATE pc_port)
target_compile_options(p2_captain_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_captain_policy_test COMMAND p2_captain_policy_test)

add_executable(p2_kurage_receiver_test tools/test_p2_kurage_receiver.cpp)
target_include_directories(p2_kurage_receiver_test PRIVATE pc_port tools/kurage_receiver_stubs)
target_compile_options(p2_kurage_receiver_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kurage_receiver_test COMMAND p2_kurage_receiver_test)

# Lane 12 captain/Kurage real-GL diagnostic (codex/p2-lane12-review
# tools/p2_captain_kurage_runtime.cpp, adapted to the line epoch API).
# Compile-only isolated target, mirroring p2_fuefuki_combat_runtime_compile:
# the replacement-main executable is produced by scripts/build_pikmin2_fixture.py
# against a completed pikmin_pc build.
add_library(p2_captain_kurage_runtime_compile OBJECT tools/p2_captain_kurage_runtime.cpp)
target_include_directories(p2_captain_kurage_runtime_compile PRIVATE pc_port ${SDL2_INCLUDE_DIRS})
target_compile_options(p2_captain_kurage_runtime_compile PRIVATE ${NATIVE_COMPILE_OPTIONS} -Wno-unused-parameter)

# Engine-including admission test: it includes Navi/NaviState through
# pc_port/pc_p2_demon_admission.h and uses _putenv_s/_spawnl to prove both
# allowlist branches, so it is Windows-only like the launcher platform tests.
if(WIN32)
    add_executable(p2_demon_admission_test tools/p2_demon_admission_test.cpp)
    target_include_directories(p2_demon_admission_test PRIVATE pc_port include)
    target_compile_options(p2_demon_admission_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME p2_demon_admission_test COMMAND p2_demon_admission_test)
endif()

# rd-demon-chain-b: standalone policy tests from codex/p2-demon-drop-interruption
# commits 22..43. Dependency-free headers; test source + pc_port include dir
# are all they need. Verified -fsyntax-only clean against the line's headers.
add_executable(p2_demon_capture_test tools/p2_demon_capture_test.cpp)
target_include_directories(p2_demon_capture_test PRIVATE pc_port)
target_compile_options(p2_demon_capture_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_demon_capture_test COMMAND p2_demon_capture_test)

add_executable(p2_demon_attack_window_test tools/p2_demon_attack_window_test.cpp)
target_include_directories(p2_demon_attack_window_test PRIVATE pc_port)
target_compile_options(p2_demon_attack_window_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_demon_attack_window_test COMMAND p2_demon_attack_window_test)

add_executable(p2_demon_policy_scenario_test tools/p2_demon_policy_scenario_test.cpp)
target_include_directories(p2_demon_policy_scenario_test PRIVATE pc_port)
target_compile_options(p2_demon_policy_scenario_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_demon_policy_scenario_test COMMAND p2_demon_policy_scenario_test)

add_executable(p2_demon_attachment_test tools/p2_demon_attachment_test.cpp)
target_include_directories(p2_demon_attachment_test PRIVATE pc_port)
target_compile_options(p2_demon_attachment_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_demon_attachment_test COMMAND p2_demon_attachment_test)

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
# Include the P2 ordinary delivery ledger because pc_randomizer.cpp always links
# against its host entry points; this only changes probe linkage, not behavior.
add_executable(pc_randomizer_probe pc_port/pc_randomizer_probe.cpp pc_port/pc_randomizer.cpp pc_port/pc_p2_delivery_host.cpp)

# Only the isolated diagnostic build includes scripted stock/death fixtures.
option(PIKMIN_RANDOMIZER_TEST_HOOKS "Enable standalone scripted gameplay test fixtures" OFF)
if(PIKMIN_RANDOMIZER_TEST_HOOKS)
    set_property(SOURCE src/plugPikiKando/gameCoreSection.cpp APPEND PROPERTY
        COMPILE_DEFINITIONS PIKMIN_RANDOMIZER_TEST_HOOKS=1)
endif()

# Integration gates: keep assertions active for these engine-free contracts.
foreach(policy IN ITEMS species_schema hazard_reaction hazard_emitter elemental_attack cave_transfer bulbmin_cave_filter cave_item_gate_placement cave_bud_policy captain_roster squad_policy mamuta_policy)
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

# Lane 06: per-consumer ledger — two handles on distinct paths never interfere.
add_executable(p2_receipt_host_multi_test tools/p2_receipt_host_multi_test.cpp pc_port/pc_p2_receipt_host.cpp)
target_include_directories(p2_receipt_host_multi_test PRIVATE pc_port)
target_compile_options(p2_receipt_host_multi_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_receipt_host_multi_test COMMAND p2_receipt_host_multi_test)

# Lane 06: P2 ordinary delivery receiver (header-only over pc_p2_receipt.h).
add_executable(p2_delivery_receiver_test tools/p2_delivery_receiver_test.cpp)
target_include_directories(p2_delivery_receiver_test PRIVATE pc_port)
target_compile_options(p2_delivery_receiver_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_delivery_receiver_test COMMAND p2_delivery_receiver_test)
add_executable(p2_breadbug_contest_consumer_test tools/p2_breadbug_contest_consumer_test.cpp
    pc_port/pc_p2_breadbug_contest_host.cpp)
target_include_directories(p2_breadbug_contest_consumer_test PRIVATE pc_port)
target_compile_options(p2_breadbug_contest_consumer_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_breadbug_contest_consumer_test COMMAND p2_breadbug_contest_consumer_test)

# Lane 06: engine-free delivery host bridge (persistent ordinary receipt ledger).
add_executable(p2_delivery_host_test tools/p2_delivery_host_test.cpp pc_port/pc_p2_delivery_host.cpp)
target_include_directories(p2_delivery_host_test PRIVATE pc_port)
target_compile_options(p2_delivery_host_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_delivery_host_test COMMAND p2_delivery_host_test)

# rd-p2-elecbug-admit (#585): ElecBug28 corpse -> carried -> exactly one Onion
# receipt over the real delivery-host bridge (registration only).
add_executable(p2_elecbug_transport_test tools/p2_elecbug_transport_test.cpp pc_port/pc_p2_delivery_host.cpp)
target_include_directories(p2_elecbug_transport_test PRIVATE pc_port)
target_compile_options(p2_elecbug_transport_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_elecbug_transport_test COMMAND p2_elecbug_transport_test)

# rd-p2-kurage-transport (#768): Kurage57 corpse -> carried -> exactly one
# Onion receipt over the real delivery-host bridge (registration only).
add_executable(p2_kurage_transport_test tools/p2_kurage_transport_test.cpp pc_port/pc_p2_delivery_host.cpp)
target_include_directories(p2_kurage_transport_test PRIVATE pc_port)
target_compile_options(p2_kurage_transport_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kurage_transport_test COMMAND p2_kurage_transport_test)
# rd-p2-kurage-natural (#832): engine-free reachability audit for the
# private-adapter Kurage (source 57) natural-kill gate (registration only).
add_executable(p2_kurage_natural_test tools/p2_kurage_natural_test.cpp pc_port/pc_p2_kurage_natural.cpp)
target_include_directories(p2_kurage_natural_test PRIVATE pc_port)
target_compile_options(p2_kurage_natural_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kurage_natural_test COMMAND p2_kurage_natural_test)
# rd-p2-kurage-natural (#832): guarded replacement-main natural-engagement
# observation fixture. Compile-only here; the replacement-main executable is
# produced by scripts/build_pikmin2_fixture.py against a completed pikmin_pc build.
add_library(p2_kurage_natural_runtime_compile OBJECT tools/p2_kurage_natural_runtime.cpp)
target_include_directories(p2_kurage_natural_runtime_compile PRIVATE pc_port ${SDL2_INCLUDE_DIRS})
target_compile_options(p2_kurage_natural_runtime_compile PRIVATE ${NATIVE_COMPILE_OPTIONS} -Wno-unused-parameter)
# rd-p2-kogane-receipt (#571): Kogane9 corpse -> carried -> exactly one Onion
# receipt over the real delivery-host bridge (registration only).
add_executable(p2_kogane_receipt_test tools/p2_kogane_receipt_test.cpp pc_port/pc_p2_delivery_host.cpp)
target_include_directories(p2_kogane_receipt_test PRIVATE pc_port)
target_compile_options(p2_kogane_receipt_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kogane_receipt_test COMMAND p2_kogane_receipt_test)
# rd-p2-kogane-engagement (#835): finite flip/drop/escape engagement contract.
# Engine-free truth tables over the owned policy header (registration only).
add_executable(p2_kogane_engagement_test tools/p2_kogane_engagement_test.cpp)
target_include_directories(p2_kogane_engagement_test PRIVATE pc_port)
target_compile_options(p2_kogane_engagement_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kogane_engagement_test COMMAND p2_kogane_engagement_test)
# Guarded natural-throw replacement-main fixture. Compile-only here; the
# replacement-main executable is produced by scripts/build_pikmin2_fixture.py
# against a completed pikmin_pc build.
add_library(p2_kogane_engagement_runtime_compile OBJECT tools/p2_kogane_engagement_runtime.cpp)
target_include_directories(p2_kogane_engagement_runtime_compile PRIVATE pc_port ${SDL2_INCLUDE_DIRS})
target_compile_options(p2_kogane_engagement_runtime_compile PRIVATE ${NATIVE_COMPILE_OPTIONS} -Wno-unused-parameter)
# rd-p2-sokkuri-receipt (#578): Sokkuri79 corpse -> carried -> exactly one
# Onion receipt over the real delivery-host bridge (registration only).
add_executable(p2_sokkuri_receipt_test tools/p2_sokkuri_receipt_test.cpp pc_port/pc_p2_delivery_host.cpp)
target_include_directories(p2_sokkuri_receipt_test PRIVATE pc_port)
target_compile_options(p2_sokkuri_receipt_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_sokkuri_receipt_test COMMAND p2_sokkuri_receipt_test)
# rd-p2-sarai-combat-repair (#828): Sarai23 corpse -> carried -> exactly one
# Onion receipt over the real delivery-host bridge plus the weigh-down policy
# the repaired host now feeds with live anchor facts (registration only).
add_executable(p2_sarai_combat_repair_test tools/p2_sarai_combat_repair_test.cpp pc_port/pc_p2_delivery_host.cpp)
target_include_directories(p2_sarai_combat_repair_test PRIVATE pc_port)
target_compile_options(p2_sarai_combat_repair_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_sarai_combat_repair_test COMMAND p2_sarai_combat_repair_test)
# rd-p2-sarai-combat-repair (#828): guarded replacement-main combat-repair
# observation fixture with controller-driven throws. Compile-only here; the
# replacement-main executable is produced by scripts/build_pikmin2_fixture.py
# against a completed pikmin_pc build.
add_library(p2_sarai_combat_repair_runtime_compile OBJECT tools/p2_sarai_combat_repair_runtime.cpp)
target_include_directories(p2_sarai_combat_repair_runtime_compile PRIVATE pc_port ${SDL2_INCLUDE_DIRS})
target_compile_options(p2_sarai_combat_repair_runtime_compile PRIVATE ${NATIVE_COMPILE_OPTIONS} -Wno-unused-parameter)
# rd-p2-sarai-campaign-behavior (#834): guarded replacement-main
# campaign-behavior observation fixture (campaign-seam bind, protected
# captain observation, reset/teardown). Compile-only here; the
# replacement-main executable is produced by scripts/build_pikmin2_fixture.py
# against a completed pikmin_pc build (shared-review registration only).
add_library(p2_sarai_campaign_behavior_runtime_compile OBJECT tools/p2_sarai_campaign_behavior_runtime.cpp)
target_include_directories(p2_sarai_campaign_behavior_runtime_compile PRIVATE pc_port ${SDL2_INCLUDE_DIRS})
target_compile_options(p2_sarai_campaign_behavior_runtime_compile PRIVATE ${NATIVE_COMPILE_OPTIONS} -Wno-unused-parameter)
# rd-p2-sarai-combat-repair (#828, supervisor finding 2): manager/central-seam
# lifecycle over the real pc_p2_sarai_manager.cpp TU (engine headers shadowed
# by tools/p2_sarai_lifecycle_stubs; real host class, token logic, roster and
# delivery ledger) covering setup/rebind idempotency, dynamic refusal,
# forget, death retention, reset central-drop, rebind exactly-once and bridge
# routing (registration only).
add_executable(p2_sarai_lifecycle_test tools/p2_sarai_lifecycle_test.cpp
    pc_port/pc_p2_sarai_manager.cpp pc_port/pc_p2_delivery_host.cpp)
target_include_directories(p2_sarai_lifecycle_test BEFORE PRIVATE
    tools/p2_sarai_lifecycle_stubs pc_port)
target_compile_options(p2_sarai_lifecycle_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_sarai_lifecycle_test COMMAND p2_sarai_lifecycle_test)

# Lane 06: engine-free provider unit tests (header-only; previously present but unregistered).
add_executable(p2_receipt_test tools/p2_receipt_test.cpp)
target_include_directories(p2_receipt_test PRIVATE pc_port)
target_compile_options(p2_receipt_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_receipt_test COMMAND p2_receipt_test ${CMAKE_CURRENT_BINARY_DIR}/p2_receipt_test_tmp)

add_executable(p2_cargo_contest_test tools/p2_cargo_contest_test.cpp)
target_include_directories(p2_cargo_contest_test PRIVATE pc_port)
target_compile_options(p2_cargo_contest_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_cargo_contest_test COMMAND p2_cargo_contest_test)

add_executable(test_p2_cargo tools/test_p2_cargo.cpp)
target_include_directories(test_p2_cargo PRIVATE pc_port)
target_compile_options(test_p2_cargo PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME test_p2_cargo COMMAND test_p2_cargo)

foreach(policy IN ITEMS demon_captor demon_escape demon_pose sarai_fsm sarai_policy sarai_capture fuefuki_follow fuefuki_follow_binding)
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
# Lane 20 (#424) generated-session live-animator family host.
add_executable(p2_kabuto_host_test tools/p2_kabuto_host_test.cpp ${P2_KABUTO_TEST_DEPS} pc_port/pc_p2_kabuto_host.cpp)
target_include_directories(p2_kabuto_host_test PRIVATE pc_port)
target_compile_options(p2_kabuto_host_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kabuto_host_test COMMAND p2_kabuto_host_test)

foreach(policy IN ITEMS bigtreasure_ordinary bigtreasure_animclock bigtreasure_natural bigtreasure_elements)
    add_executable(p2_${policy}_test tools/p2_${policy}_test.cpp ${P2_BIGTREASURE_TEST_DEPS}
        pc_port/pc_p2_bigtreasure_ordinary.cpp pc_port/pc_p2_bigtreasure_animclock.cpp
        pc_port/pc_p2_bigtreasure_motion.cpp pc_port/pc_p2_bigtreasure_elements.cpp)
    target_include_directories(p2_${policy}_test PRIVATE pc_port)
    target_compile_options(p2_${policy}_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
    add_test(NAME p2_${policy}_test COMMAND p2_${policy}_test)
endforeach()

# Lane 32 (#246) elemental receiver decision (engine-free stimulus resolve).
add_executable(p2_bigtreasure_receiver_test tools/p2_bigtreasure_receiver_test.cpp
    pc_port/pc_p2_bigtreasure_receiver.cpp)
target_include_directories(p2_bigtreasure_receiver_test PRIVATE pc_port)
target_compile_options(p2_bigtreasure_receiver_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_bigtreasure_receiver_test COMMAND p2_bigtreasure_receiver_test)

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
# Parked Groink carcass-recovery and host-registration-guard policy tests.
add_executable(p2_groink_carcass_test tools/p2_groink_carcass_test.cpp pc_port/pc_p2_groink_carcass.cpp)
target_include_directories(p2_groink_carcass_test PRIVATE pc_port)
target_compile_options(p2_groink_carcass_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_carcass_test COMMAND p2_groink_carcass_test)
add_executable(p2_groink_lifetime_test tools/p2_groink_lifetime_test.cpp)
target_include_directories(p2_groink_lifetime_test PRIVATE pc_port)
target_compile_options(p2_groink_lifetime_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_lifetime_test COMMAND p2_groink_lifetime_test)
# Slice 2: carcass sidecar binding descriptor reader + config handoff.
add_executable(p2_groink_teki_test tools/p2_groink_teki_test.cpp pc_port/pc_p2_groink_carcass.cpp)
target_include_directories(p2_groink_teki_test PRIVATE pc_port)
target_compile_options(p2_groink_teki_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_teki_test COMMAND p2_groink_teki_test)
# Compile the engine-side sidecar under the CTest build as an object-only library:
# its link deps are the product engine (tekiMgr/gsys/BTekii/Pellet), which this
# standalone test does not link, but compiling it here catches sidecar source
# regressions that the product build alone would only surface later.
add_library(p2_groink_teki_sidecar OBJECT pc_port/pc_p2_groink_teki.cpp)
target_include_directories(p2_groink_teki_sidecar PRIVATE pc_port)
target_compile_options(p2_groink_teki_sidecar PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_dependencies(p2_groink_teki_test p2_groink_teki_sidecar)

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

# #440 campaign setup failsafe: in bridge mode a species setup that cannot stage
# its files logs P2_SETUP_SKIP and leaves the P1 stand-ins instead of aborting;
# fixture mode stays fail-closed. Engine-free guard test.
add_executable(p2_setup_failsafe_test tools/test_p2_setup_failsafe.cpp)
target_include_directories(p2_setup_failsafe_test PRIVATE pc_port)
target_compile_options(p2_setup_failsafe_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_setup_failsafe_test COMMAND p2_setup_failsafe_test)

# rd-p2-campaign-goal-lifecycle (#836; CMake registration shared review):
# read-only Onion GoalItem lifecycle probe linked into pikmin_pc so campaign
# fixtures resolve the census; engine-free format/parse/classify regression;
# guarded replacement-main campaign observer (compile-only here, executable
# via scripts/build_pikmin2_fixture.py against a completed pikmin_pc build).
add_executable(p2_campaign_goal_lifecycle_test tools/p2_campaign_goal_lifecycle_test.cpp)
target_include_directories(p2_campaign_goal_lifecycle_test PRIVATE pc_port)
target_compile_options(p2_campaign_goal_lifecycle_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_campaign_goal_lifecycle_test COMMAND p2_campaign_goal_lifecycle_test)
add_library(p2_campaign_goal_lifecycle_runtime_compile OBJECT tools/p2_campaign_goal_lifecycle_runtime.cpp)
target_include_directories(p2_campaign_goal_lifecycle_runtime_compile PRIVATE pc_port ${SDL2_INCLUDE_DIRS})
target_compile_options(p2_campaign_goal_lifecycle_runtime_compile PRIVATE ${NATIVE_COMPILE_OPTIONS} -Wno-unused-parameter)
