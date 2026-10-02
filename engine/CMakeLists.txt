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
if (WIN32)
    enable_language(RC) # icono .rc de los ejecutables (windres de MinGW)
endif()

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
set(PC_PORT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/pc_port")

# Legacy code (decompiled GameCube sources) needs permissive compilation.
# Modern GCC would reject many Metrowerks-era constructs.
#
# -fsigned-char: plain char is signed on x86-64 but UNSIGNED on ARM64 (and on
# the original PowerPC). The desktop port has only ever run with signed char,
# and the decompilation has latent bugs in both directions (Font::charToIndex,
# see AI_HANDOFF.md). Pinning the sign here makes every platform and compiler
# behave like the tested desktop build, instead of inheriting the ABI.
# Clang (el compilador del NDK) convierte en error dos cosas que GCC deja
# pasar con -fpermissive: el especificador `register` y tomar la dirección de
# un temporal (stack_new). Ambas se relajan sólo en Clang.
set(CLANG_LEGACY_RELAXATIONS
    $<$<CXX_COMPILER_ID:Clang>:-Wno-register>
    $<$<CXX_COMPILER_ID:Clang>:-Wno-address-of-temporary>
    $<$<CXX_COMPILER_ID:Clang>:-Wno-unknown-warning-option>
)
set(LEGACY_COMPILE_OPTIONS
    -include "${PC_PORT_DIR}/pc_types.h"
    -fsigned-char
    -fpermissive
    ${CLANG_LEGACY_RELAXATIONS}
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
    -fsigned-char
    -fpermissive
    ${CLANG_LEGACY_RELAXATIONS}
    -Wall
    -Wextra
    $<$<CXX_COMPILER_ID:GNU>:-Wno-changes-meaning>
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

# ─── Render backend ───
# GLES 3.0 for Android and as an optional desktop path. When ON, shaders emit
# #version 300 es and the GL context requests ES via SDL. When OFF (default for
# desktop), the classic OpenGL 3.3 compatibility path is used.
if(ANDROID)
    set(PIKMIN_GLES_DEFAULT ON)
else()
    set(PIKMIN_GLES_DEFAULT OFF)
endif()
option(PIKMIN_GLES "Build with OpenGL ES 3.0 renderer" ${PIKMIN_GLES_DEFAULT})

# Controles táctiles (pc_port/touch): de serie en Android; en escritorio se
# pueden activar para probarlos con ratón (SDL_HINT_MOUSE_TOUCH_EVENTS=1).
option(PIKMIN_TOUCH "Build the touch control layer" ${PIKMIN_GLES_DEFAULT})

# ─── Qué partes del árbol se construyen ───
# El launcher es un programa de escritorio (diálogos nativos, dolphin-tool): en
# Android no se compila; se rehace como interfaz Android en la fase 7 del plan
# de docs/ANDROID_PLAN.md. Los tests se ejecutan en la máquina que compila,
# así que tampoco tienen sentido al cruzar hacia un dispositivo.
if(ANDROID)
    set(PIKMIN_DESKTOP_DEFAULT OFF)
else()
    set(PIKMIN_DESKTOP_DEFAULT ON)
endif()
option(PIKMIN_BUILD_LAUNCHER "Build the standalone first-run launcher" ${PIKMIN_DESKTOP_DEFAULT})
option(PIKMIN_BUILD_TESTS "Build the host-run test executables" ${PIKMIN_DESKTOP_DEFAULT})

if(PIKMIN_BUILD_TESTS)
    enable_testing()
endif()

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
    PIKI_USE_GLES=$<BOOL:${PIKMIN_GLES}>
    PIKI_PC_TOUCH=$<BOOL:${PIKMIN_TOUCH}>
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
    # SDL_main unless the application explicitly owns its entry point. En
    # Android es al revés: SDLActivity busca el símbolo SDL_main en la
    # biblioteca, así que ahí se deja que SDL_main.h renombre main.
    $<$<NOT:$<BOOL:${ANDROID}>>:SDL_MAIN_HANDLED=1>
    # In-game settings menu (F1). Remove this to disable the overlay entirely.
    PIKI_PC_SETTINGS_MENU=1
)

# ─── Include paths ───
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/include/Dolphin
    ${CMAKE_CURRENT_SOURCE_DIR}/include/Dolphin/OS
    ${CMAKE_CURRENT_SOURCE_DIR}/include/Dolphin/GX
    ${PC_PORT_DIR}
    ${PC_PORT_DIR}/gl
)

###############################################################################
#  Source file lists
#  We compile only the game logic modules, NOT the original Dolphin SDK
#  implementations (those are replaced by our stubs).
###############################################################################

# ─── External Dependencies (SDL2 & OpenGL) ───
# En Android SDL2 se compila en el mismo árbol: el proyecto Gradle
# (android/app/jni/CMakeLists.txt) añade las fuentes de SDL2 antes que este
# fichero y deja el target `SDL2` definido, con sus cabeceras como interfaz.
if (ANDROID)
    if (NOT TARGET SDL2)
        message(FATAL_ERROR "Android: SDL2 must be added as a target before this project (see android/app/jni/CMakeLists.txt)")
    endif()
    set(SDL2_LIBRARIES SDL2)
    # El port incluye <SDL2/SDL.h> (la disposición de los paquetes de
    # escritorio); el árbol de fuentes de SDL2 tiene SDL.h suelto. Un enlace
    # simbólico en el directorio de build reproduce esa disposición, y sirve
    # también a pikmin_legacy, que ve las cabeceras sin enlazar SDL2.
    get_target_property(_sdl2_src SDL2 SOURCE_DIR)
    file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/sdl2-include")
    file(CREATE_LINK "${_sdl2_src}/include" "${CMAKE_CURRENT_BINARY_DIR}/sdl2-include/SDL2" SYMBOLIC)
    set(SDL2_INCLUDE_DIRS "${CMAKE_CURRENT_BINARY_DIR}/sdl2-include" "${_sdl2_src}/include")
elseif(WIN32 AND DEFINED SDL2_MINGW_ROOT)
    # The explicit MinGW SDK also supplies the packaged DLL. Do not allow
    # stale SDL2_DIR/cache, system packages or pkg-config to select another SDK.
    foreach(_sdl2_required include/SDL2/SDL.h lib/libSDL2.dll.a bin/SDL2.dll)
        if(NOT EXISTS "${SDL2_MINGW_ROOT}/${_sdl2_required}" OR
           IS_DIRECTORY "${SDL2_MINGW_ROOT}/${_sdl2_required}")
            message(FATAL_ERROR "Incomplete SDL2 MinGW SDK: ${SDL2_MINGW_ROOT}/${_sdl2_required}")
        endif()
    endforeach()
    set(SDL2_INCLUDE_DIRS "${SDL2_MINGW_ROOT}/include" "${SDL2_MINGW_ROOT}/include/SDL2")
    set(SDL2_LIBRARIES "${SDL2_MINGW_ROOT}/lib/libSDL2.dll.a")
    set(SDL2_FOUND TRUE)
else()
    find_package(SDL2 QUIET)
    if (NOT SDL2_FOUND)
        find_package(PkgConfig REQUIRED)
        pkg_check_modules(SDL2 REQUIRED sdl2)
    endif()
endif()

# SDL2main supplies a WinMain that forwards to SDL_main. This project declares
# SDL_MAIN_HANDLED and defines its own main, so linking it leaves SDL_main
# undefined in every executable. Drop it wherever the SDL2 package offers it.
if (SDL2_LIBRARIES)
    list(FILTER SDL2_LIBRARIES EXCLUDE REGEX "SDL2main")
endif()

# OpenGL de escritorio no existe en Android: allí el contexto es GLES/EGL y lo
# aporta el NDK (fase 3 del plan de Android).
if (NOT WIN32 AND NOT ANDROID)
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
    pc_port/pc_p2_sarai_demon.cpp
    pc_port/pc_p2_sarai_capture_bridge.cpp
    pc_port/pc_p2_sarai_manager.cpp
    pc_port/pc_p2_generated_placement.cpp
    pc_port/pc_p2_campaign_goal_probe.cpp
    pc_port/pc_bbft.cpp
    pc_port/pc_p2_surface_topology.cpp
    pc_port/pc_p2_surface_water.cpp
    # Deterministic netplay fixed-step mode, M1 (issue #878). Engine-free TUs;
    # they join pikmin_pc and the engine-free pc_bbft_test / pc_sim_rng_test.
    pc_port/netplay/pc_netplay_det.cpp
    pc_port/netplay/pc_netplay_policy.cpp
    pc_port/netplay/pc_netplay_present.cpp
    pc_port/netplay/pc_sim_rng.cpp
    # Netplay M5c lane A (issue #887): the lead (instant) camera. Engine TU in
    # both builds; inert until a lockstep session arms it (netplay builds).
    pc_port/netplay/pc_netplay_camlead.cpp
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
    # Challenge stage-table extension fallthrough (#730; #186 decision
    # output/workflow/integration-recovery/species-owner/stagetable730-186-decision.md):
    # the additive LeafChappy/02tile table joins pikmin_pc so the pc_bbft.cpp
    # weak fallthrough resolves on an engine miss. pc_bbft_test keeps linking
    # without this TU.
    pc_port/pc_p2_challenge_stages_ext.cpp
    pc_port/pc_p2_preview.cpp
    pc_port/pc_p2_captain.cpp
    pc_port/pc_p2_second_captain.cpp
    pc_port/pc_p2_economy.cpp
    pc_port/pc_p2_teki_lifetime.cpp
    pc_port/pc_p2_placement_probe.cpp
    pc_port/pc_p2_boss_arena.cpp
    pc_port/pc_held_part.cpp
    pc_port/pc_p2_input_script.cpp
    pc_port/pc_dev_console.cpp
    # TEST-ONLY headless autoplay bot (bot-impl): scripted player driving the
    # normal pad path. Env-gated (PIKMIN_RANDOMIZER_AUTOPLAY), inert otherwise.
    pc_port/pc_p2_autoplay.cpp
    pc_port/pc_p2_test_day_cycle.cpp
    pc_port/pc_p2_ship.cpp
    pc_port/pc_p2_purple.cpp
    pc_port/pc_p2_purple_motion.cpp
    pc_port/pc_p2_purple_impact.cpp
    pc_port/pc_p2_purple_direct.cpp
    pc_port/pc_whistle_pluck.cpp
    pc_port/pc_route_planner.cpp
    pc_port/pc_p2_purple_flight.cpp
    pc_port/pc_p2_purple_feedback.cpp
    pc_port/pc_p2_sfx.cpp
    pc_port/pc_p2_kochappy_stun.cpp
    pc_port/pc_p2_species.cpp
    pc_port/pc_p2_bulbmin.cpp
    pc_port/pc_p2_white.cpp
    pc_port/pc_p2_white_poison.cpp
    pc_port/pc_p2_cave.cpp
    pc_port/pc_p2_cave_dialog_window.cpp
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
    pc_port/pc_p2_chappy.cpp
    pc_port/pc_p2_kochappy_fsm.cpp
    pc_port/pc_p2_breadbug_visual.cpp
    pc_port/pc_p2_giant_breadbug_visual.cpp
    pc_port/pc_p2_bulblax_visual.cpp
    pc_port/pc_p2_queen.cpp
    pc_port/pc_p2_king.cpp
    pc_port/pc_p2_king_teki.cpp
    pc_port/pc_p2_queen_teki.cpp
    pc_port/pc_p2_no_carcass.cpp
    pc_port/pc_p2_breadbug_actor.cpp
    pc_port/pc_p2_breadbug_contest_host.cpp
    pc_port/pc_p2_giant_breadbug_actor.cpp
    pc_port/pc_p2_frog.cpp
    pc_port/pc_p2_kogane.cpp
    pc_port/pc_p2_mamuta.cpp
    pc_port/pc_p2_mamuta_rules.cpp
    pc_port/pc_p2_mamuta_fsm.cpp
    pc_port/pc_p2_tank.cpp
    pc_port/pc_p2_attack_fx.cpp
    pc_port/pc_p2_gas_cloud.cpp
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
    pc_port/pc_p2_uji.cpp
    pc_port/pc_p2_armor.cpp
    pc_port/pc_p2_otakara.cpp
    pc_port/pc_p2_otakara_fx.cpp
    pc_port/pc_p2_bomb_visual.cpp
    pc_port/pc_p2_elecbug.cpp
    pc_port/pc_p2_tamago.cpp
    pc_port/pc_p2_astonish.cpp
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
    pc_port/pc_p2_skewer_cam.cpp
    pc_port/pc_p2_batch2.cpp
    pc_port/pc_p2_proxy.cpp
    pc_port/pc_p2_batch3.cpp
    pc_port/pc_p2_snagret_fsm.cpp
    pc_port/pc_p2_dangomushi_hazard.cpp
    pc_port/pc_p2_long_legs_fsm.cpp
    pc_port/pc_p2_houdai_fsm.cpp
    pc_port/pc_p2_houdai_rig.cpp
    pc_port/pc_p2_long_legs_ik.cpp
    pc_port/pc_p2_bigfoot_fsm.cpp
    pc_port/pc_p2_long_legs.cpp
    pc_port/pc_p2_cannon_stone.cpp
    pc_port/pc_p2_egg_hazard.cpp
pc_port/pc_p2_kabuto_cannon.cpp
pc_port/pc_p2_kabuto_events.cpp
pc_port/pc_p2_kabuto_muzzle.cpp
pc_port/pc_p2_kabuto_binding.cpp
pc_port/pc_p2_kabuto_host.cpp
pc_port/pc_p2_kabuto_fsm.cpp
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
    pc_port/pc_p2_groink_fsm.cpp
    pc_port/pc_p2_groink_teki.cpp
    pc_port/pc_p2_groink_fx.cpp
    pc_port/pc_p2_fuefuki_teki.cpp
    pc_port/pc_p2_breadbug_fsm.cpp
    pc_port/pc_p2_breadbug_teki.cpp
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
    pc_port/pc_p2_bombsarai_own.cpp
    pc_port/pc_p2_bombsarai_own_teki.cpp
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
    pc_port/pc_p2_bigtreasure_own.cpp
    pc_port/pc_p2_bigtreasure_teki.cpp
    pc_port/pc_randomizer.cpp
    # Netplay M4 lane A snapshot codec (issue #885): engine-free, linked in
    # every build next to pc_randomizer.cpp (which calls it). New behaviour
    # is opt-in at runtime, so default builds are byte-identical.
    pc_port/netplay/pc_netplay_randstate.cpp
    # Netplay M4 lane B1 outbox/mirror/ledger module (issue #885): engine-free,
    # linked wherever pc_randomizer.cpp is. Inert unless a netplay session
    # with the external-state stream is active.
    pc_port/pc_randomizer_outbox.cpp
    pc_port/pc_p2_waterwraith.cpp
    pc_port/pc_p2_waterwraith_actor.cpp
    pc_port/pc_p2_kurage.cpp
    pc_port/pc_p2_kurage_arena.cpp
    pc_port/pc_p2_kurage_visual.cpp
    pc_port/pc_p2_kurage_teki.cpp
    pc_port/pc_p2_kurage_own_host.cpp
    pc_port/pc_p2_kurage_fx.cpp
    pc_port/pc_p2_flyer_coll.cpp
    pc_port/pc_p2_body_coll.cpp
    pc_port/pc_p2_onikurage_mouth.cpp
    pc_port/pc_p2_onikurage_teki.cpp
    pc_port/pc_main.cpp
    pc_port/pc_fatal_log.cpp
    pc_port/pc_window.cpp
    pc_port/pc_gyro.cpp
    pc_port/pc_pad_axis.cpp
    pc_port/pc_pad_bindings.cpp
    pc_port/pc_menu_repeat.cpp
    pc_port/pc_photo_mode.cpp
    pc_port/pc_permadeath.cpp
    pc_port/pc_coop.cpp
    # Netplay M4 D-policy (#885): owner co-op randomizer policy (engine-free).
    pc_port/pc_coop_policy.cpp
    # Direct-boot co-op switch (netplay M0): CLI/env parse + apply. New
    # netplay code lives under pc_port/netplay/.
    pc_port/netplay/pc_coop_switch.cpp
    # Netplay determinism harness M1 (#878): input record/replay plus
    # per-tick state hashes. Opt-in via PIKMIN_INPUT_*/PIKMIN_STATE_HASH_*.
    pc_port/netplay/pc_input_log.cpp
    pc_port/netplay/pc_state_hash.cpp
    pc_port/pc_art.cpp
    pc_port/pc_icon.cpp
    pc_port/settings/pc_glass_menu.cpp
    pc_port/pc_gpu_preference.cpp
    pc_port/mods/pc_hd_models.cpp
    pc_port/mods/pc_hd_model_convert.cpp
    pc_port/mods/pc_vs_arena.cpp
    pc_port/pc_vs.cpp
    pc_port/pc_file_dialog.cpp
    pc_port/gl/pc_gfx.cpp
    pc_port/gl/pc_gfx_deferred_tex.cpp
    pc_port/gl/pc_tev_shader.cpp
    pc_port/gl/pc_postprocess.cpp
    pc_port/gl/pc_texpack.cpp
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
if (ANDROID)
    list(APPEND PC_PORT_SOURCES
        pc_port/android/pc_android.cpp
        pc_port/android/pc_texpack_android.cpp
        pc_port/android/pc_save_android.cpp)
endif()
if (PIKMIN_TOUCH)
    list(APPEND PC_PORT_SOURCES pc_port/touch/pc_touch.cpp)
endif()

include_directories(
    ${SDL2_INCLUDE_DIRS}
    ${OPENGL_INCLUDE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/stb
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/bcdec
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/xxhash
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
# En Android el mismo árbol se añade dos veces (USA y PAL) desde
# android/app/jni/CMakeLists.txt; los nombres de target llevan entonces un
# sufijo para no chocar, y la biblioteca resultante se llama según la
# versión (libnectar.so / libnectar-pal.so), igual que los ejecutables del
# paquete de escritorio.
set(PIKMIN_TARGET_SUFFIX "" CACHE STRING "Suffix for the game targets when the tree is added more than once")
set(NECTAR_LEGACY pikmin_legacy${PIKMIN_TARGET_SUFFIX})
set(NECTAR_GAME pikmin_pc${PIKMIN_TARGET_SUFFIX})
# Solo en Android: en escritorio el ejecutable PAL sigue saliendo como
# `nectar` en su propio directorio de build y lo renombra el empaquetado.
if(ANDROID AND PIKMIN_GAME_VERSION STREQUAL "VERSION_GPIP01_00")
    set(NECTAR_OUTPUT_NAME "nectar-pal")
else()
    set(NECTAR_OUTPUT_NAME "nectar")
endif()

add_library(${NECTAR_LEGACY} STATIC
    ${SYSCOMMON_SOURCES}
    ${SYSDOLPHIN_SOURCES}
    ${PLUGPIKI_KANDO_SOURCES}
    ${PLUGPIKI_NAKATA_SOURCES}
    ${PLUGPIKI_NISHIMURA_SOURCES}
    ${PLUGPIKI_COLIN_SOURCES}
    ${PLUGPIKI_OGAWA_SOURCES}
    ${PLUGPIKI_YAMASHITA_SOURCES}
    # Empty unless PIKMIN_NATIVE_JAUDIO is on. The engine belongs here rather
    # than in ${NECTAR_GAME} because it is decompiled code and needs the permissive
    # legacy flags, not the strict ones the port's own sources build with.
    ${JAUDIO_TARGET_SOURCES}
)
target_compile_options(${NECTAR_LEGACY} PRIVATE ${LEGACY_COMPILE_OPTIONS})

# Native executable with strict flags. En Android es una biblioteca
# compartida que carga la actividad Java de SDL (libnectar.so, con SDL_main
# como punto de entrada).
if (ANDROID)
    add_library(${NECTAR_GAME} SHARED ${PC_PORT_SOURCES})
else()
    add_executable(${NECTAR_GAME} ${PC_PORT_SOURCES})
    if (WIN32)
        # Icono del .exe (recurso Windows).
        target_sources(${NECTAR_GAME} PRIVATE packaging/windows/nectar.rc)
    endif()
endif()
target_compile_options(${NECTAR_GAME} PRIVATE ${NATIVE_COMPILE_OPTIONS})
target_link_libraries(${NECTAR_GAME} PRIVATE ${NECTAR_LEGACY})
# P2 fork targets (desktop only; the Android build is a shared library).
if (NOT ANDROID)
add_executable(pc_diary_observer_test tools/test_pc_diary_observer.cpp)
target_include_directories(pc_diary_observer_test PRIVATE pc_port)
add_test(NAME pc_diary_observer_test COMMAND pc_diary_observer_test)
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
    add_executable(pc_bbft_test pc_port/pc_bbft_test.cpp pc_port/pc_bbft.cpp pc_port/pc_randomizer.cpp pc_port/pc_p2_delivery_host.cpp pc_port/pc_p2_proxy.cpp pc_port/netplay/pc_netplay_randstate.cpp pc_port/pc_randomizer_outbox.cpp pc_port/netplay/pc_netplay_det.cpp pc_port/netplay/pc_sim_rng.cpp)
    # The #871 proxy TU pulls the engine header chain (teki.h), which needs
    # the same forced pc_types.h preinclude as the rest of the build.
    target_compile_options(pc_bbft_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_bbft_test COMMAND pc_bbft_test)
    add_test(NAME pc_bbft_background_test COMMAND pc_bbft_test --background)
    add_executable(jaudio_bbft_test pc_port/audio/jaudio_bbft_test.cpp pc_port/audio/jaudio_sink.cpp)
    target_include_directories(jaudio_bbft_test PRIVATE pc_port ${SDL2_INCLUDE_DIRS})
    target_link_libraries(jaudio_bbft_test PRIVATE ${SDL2_LIBRARIES})
    add_test(NAME jaudio_bbft_test COMMAND jaudio_bbft_test)
endif()
endif()

# GX display lists, game logic and the software audio mixer execute on the host
# CPU. Keep optimization level, machine-specific ISA and link-time optimization
# independent so release archives can remain portable.
#
# Both targets must receive all three. The bulk of the per-frame CPU work is in
# ${NECTAR_LEGACY}, not in ${NECTAR_GAME}: renderall(), the scene traversal, the matrix
# and collision maths and every GX call the translator consumes are decompiled
# sources. When these options were attached to ${NECTAR_GAME} alone -- which they
# were from the moment the legacy sources were split out into their own library
# -- the game code silently lost -march=native and LTO, and the library
# boundary also stopped the translator from inlining into it. That is a
# performance regression with no visible symptom other than the frame time.
set(PIKMIN_OPTIMIZED_TARGETS ${NECTAR_GAME} ${NECTAR_LEGACY})
if (NOT ANDROID)
    list(APPEND PIKMIN_OPTIMIZED_TARGETS p2_kurage_runtime)
endif()

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

# Deterministic netplay build flags, M1 (issue #878). Adds -ffp-contract=off
# (no fused multiply-add: identical FP results on any CPU running the same
# binary) and -ftrivial-auto-var-init=zero (no uninitialized-stack garbage in
# legacy code) to the game code targets. Mutually exclusive with
# PIKMIN_NATIVE_OPTIMIZE, and OFF by default so the default build's flags are
# unchanged.
option(PIKMIN_NETPLAY_BUILD "Deterministic netplay build flags" OFF)
if(PIKMIN_NETPLAY_BUILD AND PIKMIN_NATIVE_OPTIMIZE)
    message(FATAL_ERROR "PIKMIN_NETPLAY_BUILD cannot be combined with PIKMIN_NATIVE_OPTIMIZE")
endif()
if(PIKMIN_NETPLAY_BUILD AND CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    foreach(target IN LISTS PIKMIN_OPTIMIZED_TARGETS)
        target_compile_options(${target} PRIVATE -ffp-contract=off -ftrivial-auto-var-init=zero)
    endforeach()
endif()

# Deterministic floating-point libm, M2d (issue #879). When
# PIKMIN_NETPLAY_BUILD=ON, the game executables additionally link
# pc_port/netplay/pc_netplay_libm.c, whose strong C definitions of the
# transcendental entry points (sinf/cosf/sincosf/tanf/atanf/atan2f/
# asinf/acosf/expf/logf/powf/fmodf/hypotf/sqrtf/log10f/log2f/exp2f and the double
# versions) satisfy the game's undefined references at static link. The
# mingw-w64 libm archive members that use x87 (fsin/fcos/fsincos/fpatan/
# f2xm1/fyl2x, plus fldl/fsqrt/fstpl in sqrt/sqrtf) are therefore never
# the netplay exe, and the msvcrt.dll `tan` import thunk disappears.
# The TU is compiled once as an OBJECT library (review m2) so the game
# exes and the host test share the exact same object and flags. Per-name
# -fno-builtin-* (review M1/m5): GCC must never lower one of the
# overridden names to x87 microcode, while memcpy/sqrt builtins stay on
# (the TU uses __builtin_memcpy bit casts and an SSE sqrtsd helper, so
# they fold to moves/sqrtsd instead of CRT calls). -fno-lto: keep this TU
# out of LTO so its strong symbols link by the ordinary static rules
# (LTO partitions have discarded builtin-named definitions like sincosf
# while other partitions still reference them). The default (non-netplay)
# build does not link this TU at all: its FP behavior and its libm
# disassembly are unchanged.
set(PC_NETPLAY_LIBM_NO_BUILTIN_FLAGS
    -fno-builtin-sinf -fno-builtin-cosf -fno-builtin-sincosf -fno-builtin-tanf
    -fno-builtin-atanf -fno-builtin-atan2f -fno-builtin-asinf -fno-builtin-acosf
    -fno-builtin-expf -fno-builtin-logf -fno-builtin-log10f -fno-builtin-log2f
    -fno-builtin-exp2f -fno-builtin-powf -fno-builtin-fmodf -fno-builtin-hypotf
    -fno-builtin-sin -fno-builtin-cos -fno-builtin-sincos -fno-builtin-tan
    -fno-builtin-asin -fno-builtin-acos -fno-builtin-atan -fno-builtin-atan2
    -fno-builtin-exp -fno-builtin-log -fno-builtin-log10 -fno-builtin-log2
    -fno-builtin-exp2 -fno-builtin-pow -fno-builtin-fmod -fno-builtin-hypot)
if(PIKMIN_NETPLAY_BUILD AND NOT ANDROID)
    add_library(pc_netplay_libm_obj OBJECT pc_port/netplay/pc_netplay_libm.c)
    target_include_directories(pc_netplay_libm_obj PRIVATE pc_port)
    target_compile_options(pc_netplay_libm_obj PRIVATE
        ${PC_NETPLAY_LIBM_NO_BUILTIN_FLAGS} -fno-lto -ffp-contract=off -ftrivial-auto-var-init=zero)
    target_sources(${NECTAR_GAME} PRIVATE $<TARGET_OBJECTS:pc_netplay_libm_obj>)
    if(TARGET p2_kurage_runtime)
        target_sources(p2_kurage_runtime PRIVATE $<TARGET_OBJECTS:pc_netplay_libm_obj>)
    endif()
endif()

# Netplay M3 lockstep (issue #880): vendored GekkoNet as its own static
# library. GekkoLib/src/*.cpp with -std=gnu++20, GEKKONET_NO_ASIO and
# GEKKONET_STATIC; include dirs include, include/private and thirdparty
# (zpp). Created and linked into the game exe only when
# PIKMIN_NETPLAY_BUILD=ON, so the default build is untouched. The game's own
# netplay code compiles as C++17 and includes only gekkonet.h, which is
# C-compatible.
if(PIKMIN_NETPLAY_BUILD AND NOT ANDROID)
    file(GLOB GEKKONET_SOURCES "third_party/gekkonet/GekkoLib/src/*.cpp")
    add_library(gekkonet STATIC ${GEKKONET_SOURCES})
    target_include_directories(gekkonet PUBLIC
        third_party/gekkonet/GekkoLib/include
        PRIVATE
        third_party/gekkonet/GekkoLib/include/private
        third_party/gekkonet/GekkoLib/thirdparty)
    target_compile_definitions(gekkonet PUBLIC GEKKONET_STATIC PRIVATE GEKKONET_NO_ASIO)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(gekkonet PRIVATE -std=gnu++20)
    endif()
    # Quoted-include priority: on case-insensitive filesystems the game's
    # include/Event.h would otherwise shadow GekkoNet's private event.h
    # (directory-wide -I flags precede target ones). -iquote dirs are
    # searched first for "..." includes; GekkoNet TUs include nothing else
    # by quoted name, so this is safe.
    target_compile_options(gekkonet PRIVATE
        "-iquote${CMAKE_CURRENT_SOURCE_DIR}/third_party/gekkonet/GekkoLib/include/private"
        "-iquote${CMAKE_CURRENT_SOURCE_DIR}/third_party/gekkonet/GekkoLib/include"
        "-iquote${CMAKE_CURRENT_SOURCE_DIR}/third_party/gekkonet/GekkoLib/thirdparty")
    # M3 session driver + UDP transport (game C++17 TUs).
    target_sources(${NECTAR_GAME} PRIVATE
        pc_port/netplay/pc_netplay_session.cpp
        pc_port/netplay/pc_netplay_udp.cpp)
    # Desync forensics (issue #1037): the session input log, the desync
    # exchange data model and the per-object state dump ring. Netplay exe only.
    target_sources(${NECTAR_GAME} PRIVATE
        pc_port/netplay/pc_netplay_inlog.cpp
        pc_port/netplay/pc_netplay_forensics.cpp
        pc_port/netplay/pc_state_dump.cpp)
    # M4 gap-fix lane K (issue #885): failure-path diagnostics for the
    # netplay exe only (they log, then the game halts as before).
    target_sources(${NECTAR_GAME} PRIVATE
        pc_port/netplay/pc_netplay_diag.cpp
        pc_port/netplay/pc_netplay_diag_bt.cpp)
    target_include_directories(${NECTAR_GAME} PRIVATE third_party/gekkonet/GekkoLib/include)
    target_link_libraries(${NECTAR_GAME} PRIVATE gekkonet)
    if(WIN32)
        target_link_libraries(${NECTAR_GAME} PRIVATE ws2_32 winmm)
    endif()
endif()

# Netplay M5a ICE transport (issue #887): vendored libjuice v1.7.4 as its own
# static library. third_party/libjuice/src/*.c as C11, with JUICE_STATIC and
# the no-Nettle defines from its CMakeLists (USE_NETTLE=0, RELEASE=1 in
# Release); links ws2_32 and bcrypt on Windows. Created and linked only when
# PIKMIN_NETPLAY_BUILD=ON, so the default build is untouched (verified with
# nm: the default exe has 0 juice symbols). NOTE: NATIVE_COMPILE_OPTIONS is
# C++-only (-fpermissive etc.) and is deliberately NOT applied to this C
# target.
if(PIKMIN_NETPLAY_BUILD AND NOT ANDROID)
    file(GLOB LIBJUICE_SOURCES "third_party/libjuice/src/*.c")
    add_library(juice STATIC ${LIBJUICE_SOURCES})
    set_target_properties(juice PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)
    target_include_directories(juice PUBLIC
        third_party/libjuice/include
        PRIVATE
        third_party/libjuice/include/juice
        third_party/libjuice/src)
    target_compile_definitions(juice PUBLIC JUICE_STATIC PRIVATE USE_NETTLE=0)
    if(CMAKE_BUILD_TYPE STREQUAL "Release")
        target_compile_definitions(juice PRIVATE RELEASE=1)
    endif()
    if(WIN32)
        target_compile_definitions(juice PRIVATE WIN32_LEAN_AND_MEAN)
        target_link_libraries(juice PUBLIC ws2_32 bcrypt)
    endif()
    find_package(Threads REQUIRED)
    target_link_libraries(juice PRIVATE Threads::Threads)
    # M5a ICE session driver + transport (game C++17 TUs).
    target_sources(${NECTAR_GAME} PRIVATE
        pc_port/netplay/pc_netplay_ice.cpp)
    target_include_directories(${NECTAR_GAME} PRIVATE third_party/libjuice/include)
    target_link_libraries(${NECTAR_GAME} PRIVATE juice)
    # Launch lane (issue #887): the one-command launcher's pre-init stage and
    # its in-exe self-tests. PIKI_NETPLAY_BUILD compiles the launcher hooks in
    # pc_main/pc_window/pc_settings/pc_randomizer into this exe only, so the
    # default exe carries no launcher code or symbols (m11).
    target_sources(${NECTAR_GAME} PRIVATE
        pc_port/netplay/pc_netplay_launch.cpp
        pc_port/netplay/pc_netplay_launch_selftest.cpp)
    # M5c lane C (issue #887): the session HUD and end banner (drawn from
    # vi_stubs.cpp under PIKI_NETPLAY_BUILD; presentation only).
    target_sources(${NECTAR_GAME} PRIVATE
        pc_port/netplay/pc_netplay_hud.cpp)
    target_compile_definitions(${NECTAR_GAME} PRIVATE PIKI_NETPLAY_BUILD=1)
endif()

# Launch lane (issue #887): in-exe self-tests (they need the game's settings
# and window code). settings: the host-settings adoption round trip over
# every hashed key (M2) and every settings save path (B3). input/input-session:
# input ownership through pc_window_poll_events with an SDL virtual gamepad
# (M4, m5, m7). Each run works in its own subdir of the build dir.
if(PIKMIN_NETPLAY_BUILD AND PIKMIN_BUILD_TESTS AND NOT ANDROID)
    add_test(NAME netplay_launch_settings_selftest
        COMMAND $<TARGET_FILE:${NECTAR_GAME}> --netplay-launch-selftest settings
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
    add_test(NAME netplay_launch_input_selftest
        COMMAND $<TARGET_FILE:${NECTAR_GAME}> --netplay-launch-selftest input
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
    add_test(NAME netplay_launch_input_session_selftest
        COMMAND $<TARGET_FILE:${NECTAR_GAME}> --netplay-launch-selftest input-session
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
endif()

# Netplay M5a host-run ICE test (issue #887): two libjuice agents in one
# process connect over loopback with host candidates only (no STUN/TURN, so
# no external network), a 64 KiB transfer through the channel interface
# arrives intact, and the code encode/decode round-trips while garbage is
# rejected. Netplay builds only (links the juice target, which the default
# build never creates).
if(PIKMIN_NETPLAY_BUILD AND PIKMIN_BUILD_TESTS AND NOT ANDROID)
    add_executable(pc_netplay_ice_test
        pc_port/netplay/pc_netplay_ice_test.cpp
        pc_port/netplay/pc_netplay_ice.cpp)
    target_include_directories(pc_netplay_ice_test PRIVATE
        pc_port
        third_party/libjuice/include
        third_party/gekkonet/GekkoLib/include)
    target_compile_definitions(pc_netplay_ice_test PRIVATE GEKKONET_STATIC GEKKONET_NO_ASIO)
    target_compile_options(pc_netplay_ice_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    target_link_libraries(pc_netplay_ice_test PRIVATE juice gekkonet)
    if(WIN32)
        target_link_libraries(pc_netplay_ice_test PRIVATE ws2_32)
    endif()
    add_test(NAME pc_netplay_ice_test COMMAND pc_netplay_ice_test)
endif()

# Netplay M5a local TURN server helper (issue #887): tiny exe around
# libjuice's own juice_server_create for the TURN-only pair test. Netplay
# builds only.
if(PIKMIN_NETPLAY_BUILD AND NOT ANDROID)
    add_executable(netplay_turn_server tools/netplay/ice_turn_server.cpp)
    target_include_directories(netplay_turn_server PRIVATE third_party/libjuice/include)
    target_compile_options(netplay_turn_server PRIVATE ${NATIVE_COMPILE_OPTIONS})
    target_link_libraries(netplay_turn_server PRIVATE juice)
    if(WIN32)
        target_link_libraries(netplay_turn_server PRIVATE ws2_32)
    endif()
endif()

# Netplay M5c lane B (issue #887): loopback UDP impairment proxy for pair
# tests (latency schedule, jitter, loss, periodic link blocks; model in
# pc_netplay_impair.h). Exe-independent, so a baseline on an older exe sees
# the same link. Test tool, netplay builds on Windows only.
if(PIKMIN_NETPLAY_BUILD AND WIN32 AND NOT ANDROID)
    add_executable(netplay_impair_proxy tools/netplay/udp_impair_proxy.cpp)
    target_include_directories(netplay_impair_proxy PRIVATE pc_port)
    target_compile_options(netplay_impair_proxy PRIVATE ${NATIVE_COMPILE_OPTIONS})
    target_link_libraries(netplay_impair_proxy PRIVATE ws2_32 winmm)
endif()

# Host-run accuracy/determinism test for the netplay libm (issue #879).
# Engine-free: links the libm OBJECT plus the test driver. The driver
# calls the entry points by their standard names (proving the override
# links) and compares against the platform libm loaded explicitly from
# msvcrt.dll, so the reference is never shadowed by our definitions.
# Registered only for netplay builds (review m4): the ulp half compares
# against msvcrt.dll, which varies with the Windows version, so a
# default-build ctest could fail elsewhere for unrelated reasons.
if(PIKMIN_NETPLAY_BUILD AND PIKMIN_BUILD_TESTS AND NOT ANDROID)
    add_executable(pc_netplay_libm_test
        pc_port/netplay/pc_netplay_libm_test.cpp
        $<TARGET_OBJECTS:pc_netplay_libm_obj>)
    target_include_directories(pc_netplay_libm_test PRIVATE pc_port)
    target_compile_options(pc_netplay_libm_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_netplay_libm_test COMMAND pc_netplay_libm_test)
endif()

# Netplay M3 lockstep transport test (issue #880): two GekkoNet sessions in
# one process over an in-memory adapter with the lossy wrapper, a toy
# deterministic state, window 0 and 2,000 frames; expects 0 desyncs and
# identical checksums. Netplay builds only (links the gekkonet target, which
# the default build never creates).
if(PIKMIN_NETPLAY_BUILD AND PIKMIN_BUILD_TESTS AND NOT ANDROID)
    add_executable(pc_netplay_transport_test
        pc_port/netplay/pc_netplay_transport_test.cpp
        pc_port/netplay/pc_netplay_udp.cpp)
    target_include_directories(pc_netplay_transport_test PRIVATE
        pc_port
        third_party/gekkonet/GekkoLib/include)
    target_compile_definitions(pc_netplay_transport_test PRIVATE GEKKONET_STATIC GEKKONET_NO_ASIO)
    target_compile_options(pc_netplay_transport_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    target_link_libraries(pc_netplay_transport_test PRIVATE gekkonet)
    if(WIN32)
        target_link_libraries(pc_netplay_transport_test PRIVATE ws2_32)
    endif()
    add_test(NAME pc_netplay_transport_test COMMAND pc_netplay_transport_test)
endif()

# Netplay M4 gap-fix lane S (issue #885): the load guard's engine-free policy
# (pc_netplay_loadguard.h: stall-injector parsing/slicing, load window,
# keep-alive gate) and the GekkoNet behaviour it relies on, checked against
# the vendored library with two in-memory sessions (a silent peer is dropped
# by both sides; network polls keep a stalled peer alive without an Advance
# and leave an executing Advance untouched; a raised timeout survives one
# block; a dead peer is still detected). Netplay builds only (links gekkonet).
if(PIKMIN_NETPLAY_BUILD AND PIKMIN_BUILD_TESTS AND NOT ANDROID)
    add_executable(pc_netplay_loadguard_test pc_port/netplay/pc_netplay_loadguard_test.cpp)
    target_include_directories(pc_netplay_loadguard_test PRIVATE
        pc_port
        third_party/gekkonet/GekkoLib/include)
    target_compile_definitions(pc_netplay_loadguard_test PRIVATE GEKKONET_STATIC GEKKONET_NO_ASIO)
    target_compile_options(pc_netplay_loadguard_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    target_link_libraries(pc_netplay_loadguard_test PRIVATE gekkonet)
    if(WIN32)
        target_link_libraries(pc_netplay_loadguard_test PRIVATE ws2_32)
    endif()
    add_test(NAME pc_netplay_loadguard_test COMMAND pc_netplay_loadguard_test)
endif()

# Netplay M5c lane B (issue #887): adaptive input delay and session stats
# (pc_netplay_adaptive.h: controller, frame-time histogram, schedule parsing,
# transition arithmetic), the impairment model (pc_netplay_impair.h), and
# delay transitions against the vendored GekkoNet (two in-memory sessions
# growing and shrinking their delays mid-run with scripted per-frame inputs:
# both peers see identical inputs, and every frame F carries record F - d0).
# Netplay builds only (links gekkonet).
if(PIKMIN_NETPLAY_BUILD AND PIKMIN_BUILD_TESTS AND NOT ANDROID)
    add_executable(pc_netplay_adaptive_test pc_port/netplay/pc_netplay_adaptive_test.cpp)
    target_include_directories(pc_netplay_adaptive_test PRIVATE
        pc_port
        third_party/gekkonet/GekkoLib/include)
    target_compile_definitions(pc_netplay_adaptive_test PRIVATE GEKKONET_STATIC GEKKONET_NO_ASIO)
    target_compile_options(pc_netplay_adaptive_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    target_link_libraries(pc_netplay_adaptive_test PRIVATE gekkonet)
    if(WIN32)
        target_link_libraries(pc_netplay_adaptive_test PRIVATE ws2_32)
    endif()
    add_test(NAME pc_netplay_adaptive_test COMMAND pc_netplay_adaptive_test)
endif()

# FP determinism gate (issue #879). Runs objdump over the linked game exe
# and fails on any x87 op (transcendentals and fsqrt), any FMA
# instruction, any libm sqrt call from the netplay TU, or any
# tan/sin/cos/atan/exp/log/pow/hypot-family import from msvcrt/ucrt. Only
# meaningful (and only registered) for netplay builds, where the software
# libm must have removed all of them. Both game-linked exes are gated
# (review m3); objdump comes from ${CMAKE_OBJDUMP}, not PATH.
if(PIKMIN_NETPLAY_BUILD AND PIKMIN_BUILD_TESTS AND NOT ANDROID)
    if(WIN32)
        add_test(NAME netplay_fp_gate
            COMMAND py -3.12 "${CMAKE_CURRENT_SOURCE_DIR}/tools/netplay/fp_gate.py" --objdump "${CMAKE_OBJDUMP}" "$<TARGET_FILE:${NECTAR_GAME}>")
        if(TARGET p2_kurage_runtime)
            add_test(NAME netplay_fp_gate_kurage
                COMMAND py -3.12 "${CMAKE_CURRENT_SOURCE_DIR}/tools/netplay/fp_gate.py" --objdump "${CMAKE_OBJDUMP}" "$<TARGET_FILE:p2_kurage_runtime>")
        endif()
    else()
        find_package(Python3 COMPONENTS Interpreter)
        add_test(NAME netplay_fp_gate
            COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/netplay/fp_gate.py" --objdump "${CMAKE_OBJDUMP}" "$<TARGET_FILE:${NECTAR_GAME}>")
        if(TARGET p2_kurage_runtime)
            add_test(NAME netplay_fp_gate_kurage
                COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/netplay/fp_gate.py" --objdump "${CMAKE_OBJDUMP}" "$<TARGET_FILE:p2_kurage_runtime>")
        endif()
    endif()
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
    target_link_libraries(${NECTAR_GAME} PRIVATE ${SDL2_LIBRARIES} opengl32 comdlg32)
    target_link_libraries(p2_kurage_runtime PRIVATE ${SDL2_LIBRARIES} opengl32 comdlg32)
elseif (ANDROID)
    # En Android no hay X11 ni OpenGL de escritorio. GLESv3 y EGL vienen del
    # NDK; log y android los necesita la capa de plataforma (logcat, ciclo de
    # vida de la actividad) cuando el ejecutable se convierta en biblioteca
    # compartida en la fase 4.
    target_link_libraries(${NECTAR_GAME} PRIVATE m ${SDL2_LIBRARIES} GLESv3 EGL log android)
    # Android 15 exige bibliotecas alineadas a páginas de 16 KB en arm64.
    target_link_options(${NECTAR_GAME} PRIVATE "-Wl,-z,max-page-size=16384")
else()
    if(PIKMIN_GLES)
        target_link_libraries(${NECTAR_GAME} PRIVATE m ${SDL2_LIBRARIES} OpenGL::GLES3 X11)
        target_link_libraries(p2_kurage_runtime PRIVATE m ${SDL2_LIBRARIES} OpenGL::GLES3 X11)
    else()
        target_link_libraries(${NECTAR_GAME} PRIVATE m ${SDL2_LIBRARIES} OpenGL::GL X11)
        target_link_libraries(p2_kurage_runtime PRIVATE m ${SDL2_LIBRARIES} OpenGL::GL X11)
    endif()
endif()
# Export symbol names so the diagnostic backtrace in pc_gfx.cpp prints function
# names rather than bare addresses. Costs nothing at runtime.
#
# GNU-ld only: MinGW rejects the flag outright, and the backtrace it serves is
# compiled out on Windows anyway (glibc's execinfo.h has no equivalent there).
# En Android tampoco: el binario será una biblioteca compartida, no un
# ejecutable con símbolos exportados.
if (NOT WIN32 AND NOT ANDROID)
    target_link_options(${NECTAR_GAME} PRIVATE -rdynamic)
    target_link_options(p2_kurage_runtime PRIVATE -rdynamic)
elseif (WIN32)
    # SDL2's CMake package links -mwindows, which hides the console and with it
    # every printf the port uses to report what it is doing. Keep a console on
    # the game so a failed launch says why instead of vanishing. The launcher
    # stays windowed: it talks through native dialogs.
    target_link_options(${NECTAR_GAME} PRIVATE -mconsole)
    target_link_options(p2_kurage_runtime PRIVATE -mconsole)
endif()

# Set output name
set_target_properties(${NECTAR_GAME} PROPERTIES
    OUTPUT_NAME "${NECTAR_OUTPUT_NAME}"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)
if (NOT ANDROID AND NOT WIN32)
    add_custom_command(TARGET ${NECTAR_GAME} POST_BUILD
        COMMAND /bin/chmod 775 "$<TARGET_FILE:${NECTAR_GAME}>"
        COMMENT "Ensuring the native Pikmin executable is runnable")
endif()

# Standalone first-run launcher. It accepts an original, uncompressed
# GameCube ISO/GCM supplied by the user, extracts its FST into the per-user
# data directory and then starts the game from there. Keeping the extractor in
# a small library also lets CI test the legal install path without game assets.
#
# Es un programa de escritorio con diálogos nativos y dolphin-tool: en Android
# se rehace como interfaz propia (fase 7 del plan de docs/ANDROID_PLAN.md),
# así que con PIKMIN_BUILD_LAUNCHER=OFF aquí ni se compila.
if((PIKMIN_BUILD_LAUNCHER OR ANDROID) AND NOT TARGET pikmin_disc_image)
    add_library(pikmin_disc_image STATIC
        pc_port/launcher/gamecube_image.cpp
        pc_port/launcher/sha256.cpp)
    target_include_directories(pikmin_disc_image PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/pc_port/launcher)
    target_compile_options(pikmin_disc_image PRIVATE ${NATIVE_COMPILE_OPTIONS})
    set_property(TARGET pikmin_disc_image PROPERTY POSITION_INDEPENDENT_CODE ON)
endif()

# Instalador Android: la misma biblioteca de extracción, con un puente JNI
# fino, en una .so aparte para que la pantalla de instalación no cargue el
# juego (y su arena de 256 MB) antes de tiempo.
if(ANDROID AND NOT TARGET nectar_installer)
    add_library(nectar_installer SHARED pc_port/android/pc_installer_jni.cpp)
    target_compile_options(nectar_installer PRIVATE ${NATIVE_COMPILE_OPTIONS})
    target_link_libraries(nectar_installer PRIVATE pikmin_disc_image log)
    target_link_options(nectar_installer PRIVATE "-Wl,-z,max-page-size=16384")
endif()

# P2 fork engine-free tests (host-run only, like the upstream suites below).
if(PIKMIN_BUILD_TESTS)
# P2 Challenge host-state unit test (#651), landed per #676. Guard include dir
# is an explicit, validated cache PATH (per the pinned #651/#186 review): it
# defaults to the root-relative scripts/ when present, and private builds pass
# -DP2_CHALLENGE_GUARD_INCLUDE_DIR=<canonical scripts dir>. No vendored copy.
set(P2_CHALLENGE_GUARD_INCLUDE_DIR "${CMAKE_SOURCE_DIR}/../scripts" CACHE PATH
    "Directory containing the canonical p2_fixture_captain_guard.h")
# A standalone native checkout (upstream CI, packaging) has no root scripts/;
# the two guard-dependent fixtures are then skipped instead of failing the
# whole configure. An explicitly passed directory must still hold the header.
set(P2_CHALLENGE_GUARD_FOUND OFF)
if(EXISTS "${P2_CHALLENGE_GUARD_INCLUDE_DIR}/p2_fixture_captain_guard.h")
    set(P2_CHALLENGE_GUARD_FOUND ON)
elseif(DEFINED CACHE{P2_CHALLENGE_GUARD_INCLUDE_DIR} AND NOT P2_CHALLENGE_GUARD_INCLUDE_DIR STREQUAL "${CMAKE_SOURCE_DIR}/../scripts")
    message(FATAL_ERROR
        "p2_fixture_captain_guard.h not found in ${P2_CHALLENGE_GUARD_INCLUDE_DIR}; "
        "pass -DP2_CHALLENGE_GUARD_INCLUDE_DIR=<canonical scripts dir>")
else()
    message(STATUS "p2_fixture_captain_guard.h not found (no root scripts/); "
        "skipping p2_challenge_mode_fixture and p2_challenge_boot_fixture")
endif()
if(P2_CHALLENGE_GUARD_FOUND)
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
endif() # P2_CHALLENGE_GUARD_FOUND

add_executable(p2_dangomushi_hazard_test
    tools/p2_dangomushi_hazard_test.cpp
    pc_port/pc_p2_dangomushi_hazard.cpp)
target_include_directories(p2_dangomushi_hazard_test PRIVATE pc_port)
target_compile_options(p2_dangomushi_hazard_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_dangomushi_hazard_test COMMAND p2_dangomushi_hazard_test)
add_executable(p2_sfx_policy_test
    tools/p2_sfx_policy_test.cpp)
target_include_directories(p2_sfx_policy_test PRIVATE pc_port)
target_compile_options(p2_sfx_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_sfx_policy_test COMMAND p2_sfx_policy_test)
add_executable(p2_dangomushi_policy_test
    tools/p2_dangomushi_policy_test.cpp)
target_include_directories(p2_dangomushi_policy_test PRIVATE pc_port)
target_compile_options(p2_dangomushi_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_dangomushi_policy_test COMMAND p2_dangomushi_policy_test)
add_executable(p2_navi_select_test
    tools/p2_navi_select_test.cpp)
target_include_directories(p2_navi_select_test PRIVATE pc_port)
target_compile_options(p2_navi_select_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_navi_select_test COMMAND p2_navi_select_test)
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
# #884: elemental Dweevil (59-62) creature escape + territory clamp; Bomb 93 chase.
add_executable(p2_otakara_move_test
    tools/p2_otakara_move_test.cpp)
target_include_directories(p2_otakara_move_test PRIVATE pc_port)
target_compile_options(p2_otakara_move_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_otakara_move_test COMMAND p2_otakara_move_test)
# #884: registered Dweevils (59-62, 93) skip the P1 Chappy host squash (thrown-
# landing smash and InteractPress) like source OtakaraBase (no pressCallBack);
# policy is engine-free, the hook wiring is checked against the source text.
add_executable(p2_otakara_press_test
    tools/p2_otakara_press_test.cpp)
target_include_directories(p2_otakara_press_test PRIVATE pc_port)
target_compile_options(p2_otakara_press_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
target_compile_definitions(p2_otakara_press_test PRIVATE
    P2_OTAKARA_PRESS_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
add_test(NAME p2_otakara_press_test COMMAND p2_otakara_press_test)

# Dweevil family fidelity (owner playtest 2026-09-30): collision parts (legs carry none, the
# partless ground punch is refused), treasure pickup/carry/drop, the elemental attack window and
# effect lifecycle, and slope speed / stall side-step. All policy is engine-free; the wiring is
# checked against the source text.
foreach(dweevil_test IN ITEMS part item attack stall)
    string(TOUPPER ${dweevil_test} dweevil_test_upper)
    add_executable(p2_otakara_${dweevil_test}_test
        tools/p2_otakara_${dweevil_test}_test.cpp)
    target_include_directories(p2_otakara_${dweevil_test}_test PRIVATE pc_port)
    target_compile_options(p2_otakara_${dweevil_test}_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
    target_compile_definitions(p2_otakara_${dweevil_test}_test PRIVATE
        P2_OTAKARA_${dweevil_test_upper}_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
    add_test(NAME p2_otakara_${dweevil_test}_test COMMAND p2_otakara_${dweevil_test}_test)
endforeach()

# wf7 dweevil-impl (#871): dead-Dweevil clip choice is engine-free and covers
# all four species 59-62 (dead forces dead, never attack1).
add_executable(p2_dweevil_death_clip_test
    tools/p2_dweevil_death_clip_test.cpp)
target_include_directories(p2_dweevil_death_clip_test PRIVATE pc_port)
target_compile_options(p2_dweevil_death_clip_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_dweevil_death_clip_test COMMAND p2_dweevil_death_clip_test)

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

add_executable(p2_long_legs_pose_test
    tools/p2_long_legs_pose_test.cpp)
target_include_directories(p2_long_legs_pose_test PRIVATE pc_port)
target_compile_options(p2_long_legs_pose_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_long_legs_pose_test COMMAND p2_long_legs_pose_test)

add_executable(p2_houdai_fsm_test
    tools/p2_houdai_fsm_test.cpp
    pc_port/pc_p2_houdai_fsm.cpp
    pc_port/pc_p2_long_legs_fsm.cpp)
target_include_directories(p2_houdai_fsm_test PRIVATE pc_port)
target_compile_options(p2_houdai_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_houdai_fsm_test COMMAND p2_houdai_fsm_test)

add_executable(p2_houdai_rig_test
    tools/p2_houdai_rig_test.cpp
    pc_port/pc_p2_houdai_rig.cpp
    pc_port/pc_p2_long_legs_ik.cpp)
target_include_directories(p2_houdai_rig_test PRIVATE pc_port)
target_compile_options(p2_houdai_rig_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_houdai_rig_test COMMAND p2_houdai_rig_test)

add_executable(p2_long_legs_ik_test
    tools/p2_long_legs_ik_test.cpp
    pc_port/pc_p2_long_legs_ik.cpp)
target_include_directories(p2_long_legs_ik_test PRIVATE pc_port)
target_compile_options(p2_long_legs_ik_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_long_legs_ik_test COMMAND p2_long_legs_ik_test)

add_executable(p2_bigfoot_fsm_test
    tools/p2_bigfoot_fsm_test.cpp
    pc_port/pc_p2_bigfoot_fsm.cpp
    pc_port/pc_p2_long_legs_ik.cpp
    pc_port/pc_p2_long_legs_fsm.cpp)
target_include_directories(p2_bigfoot_fsm_test PRIVATE pc_port)
target_compile_options(p2_bigfoot_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bigfoot_fsm_test COMMAND p2_bigfoot_fsm_test)

add_executable(p2_inst_legs_policy_test
    tools/p2_inst_legs_policy_test.cpp
    pc_port/pc_p2_long_legs_fsm.cpp)
target_include_directories(p2_inst_legs_policy_test PRIVATE pc_port)
target_compile_options(p2_inst_legs_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_inst_legs_policy_test COMMAND p2_inst_legs_policy_test)

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

# #244 OWN campaign port: source-faithful engine-free BombSarai machine.
add_executable(p2_bombsarai_own_test
    tools/p2_bombsarai_own_test.cpp
    pc_port/pc_p2_bombsarai_own.cpp)
target_include_directories(p2_bombsarai_own_test PRIVATE pc_port)
target_compile_options(p2_bombsarai_own_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bombsarai_own_test COMMAND p2_bombsarai_own_test)

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

# #245 OWN campaign policy: seven engine-free regressions, each paired with a
# mutant build that injects the defect the case guards (WILL_FAIL). A case that
# passes against its own mutant is not evidence.
add_executable(p2_fuefuki_teki_policy_test tools/p2_fuefuki_teki_policy_test.cpp)
target_include_directories(p2_fuefuki_teki_policy_test PRIVATE pc_port)
target_compile_options(p2_fuefuki_teki_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_fuefuki_teki_policy_test COMMAND p2_fuefuki_teki_policy_test)
foreach(pair IN ITEMS "APPEAR_ZERO:appear_roll" "NO_HIDE:host_outputs" "TOKEN_UNUSED:multi_token"
                      "NO_PANIC:owner_panic" "RING_IGNORED:ring_filter"
                      "PRESS_ALWAYS:press_gate" "NO_TARGET_GUARD:target_guard")
    string(REPLACE ":" ";" parts "${pair}")
    list(GET parts 0 mutant)
    list(GET parts 1 testcase)
    string(TOLOWER "${mutant}" mutant_lower)
    add_executable(p2_fuefuki_teki_policy_mutant_${mutant_lower} tools/p2_fuefuki_teki_policy_test.cpp)
    target_include_directories(p2_fuefuki_teki_policy_mutant_${mutant_lower} PRIVATE pc_port)
    target_compile_options(p2_fuefuki_teki_policy_mutant_${mutant_lower} PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
    target_compile_definitions(p2_fuefuki_teki_policy_mutant_${mutant_lower} PRIVATE P2_FUEFUKI_MUTANT_${mutant}=1)
    add_test(NAME p2_fuefuki_teki_policy_mutant_${mutant_lower}
             COMMAND p2_fuefuki_teki_policy_mutant_${mutant_lower} ${testcase})
    set_tests_properties(p2_fuefuki_teki_policy_mutant_${mutant_lower} PROPERTIES WILL_FAIL TRUE)
endforeach()
# Engine-side sidecar compile check (object only; product engine link deps).
add_library(p2_fuefuki_teki_sidecar OBJECT pc_port/pc_p2_fuefuki_teki.cpp)
target_include_directories(p2_fuefuki_teki_sidecar PRIVATE pc_port)
target_compile_options(p2_fuefuki_teki_sidecar PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_dependencies(p2_fuefuki_teki_policy_test p2_fuefuki_teki_sidecar)

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

# #246 OWN: Titan Dweevil campaign core (source-order FSM, IK gait, key-event
# animator, damage routing, element aim). Engine-free.
add_executable(p2_bigtreasure_own_test
    tools/p2_bigtreasure_own_test.cpp
    pc_port/pc_p2_bigtreasure_own.cpp
    pc_port/pc_p2_bigtreasure.cpp
    pc_port/pc_p2_bigtreasure_attacks.cpp
    pc_port/pc_p2_bigtreasure_elements.cpp
    pc_port/pc_p2_bigtreasure_receiver.cpp)
target_include_directories(p2_bigtreasure_own_test PRIVATE pc_port)
target_compile_options(p2_bigtreasure_own_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_bigtreasure_own_test COMMAND p2_bigtreasure_own_test)
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
add_executable(p2_hana_residual_policy_test
    tools/p2_hana_residual_policy_test.cpp)
target_include_directories(p2_hana_residual_policy_test PRIVATE pc_port)
target_compile_options(p2_hana_residual_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_hana_residual_policy_test COMMAND p2_hana_residual_policy_test)
add_executable(p2_hana_sleep_policy_test
    tools/p2_hana_sleep_policy_test.cpp)
target_include_directories(p2_hana_sleep_policy_test PRIVATE pc_port)
target_compile_options(p2_hana_sleep_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_hana_sleep_policy_test COMMAND p2_hana_sleep_policy_test)

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

add_executable(p2_proxy_table_test
    tools/test_p2_proxy_table.cpp)
target_include_directories(p2_proxy_table_test PRIVATE pc_port)
target_compile_options(p2_proxy_table_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_proxy_table_test COMMAND p2_proxy_table_test)

# Campaign host policy (#871): engine-free hostType/hasStaticHost contract.
add_executable(p2_queen_own_test
    pc_port/pc_p2_queen_own_test.cpp)
target_include_directories(p2_queen_own_test PRIVATE pc_port)
target_compile_options(p2_queen_own_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_queen_own_test COMMAND p2_queen_own_test)

# Dense Queen/larva pose bank + shared blend (#972): engine-free.
add_executable(p2_queen_pose_test
    pc_port/pc_p2_queen_pose_test.cpp)
target_include_directories(p2_queen_pose_test PRIVATE pc_port)
target_compile_options(p2_queen_pose_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_queen_pose_test COMMAND p2_queen_pose_test)

add_executable(p2_campaign_policy_test
    pc_port/pc_p2_campaign_policy_test.cpp)
target_include_directories(p2_campaign_policy_test PRIVATE pc_port)
target_compile_options(p2_campaign_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_campaign_policy_test COMMAND p2_campaign_policy_test)

add_executable(p2_no_carcass_policy_test
    pc_port/pc_p2_no_carcass_policy_test.cpp)
target_include_directories(p2_no_carcass_policy_test PRIVATE pc_port)
target_compile_options(p2_no_carcass_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_no_carcass_policy_test COMMAND p2_no_carcass_policy_test)

add_executable(p2_kurage_bank_test
    pc_port/pc_p2_kurage_bank_test.cpp)
target_include_directories(p2_kurage_bank_test PRIVATE pc_port)
target_compile_options(p2_kurage_bank_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kurage_bank_test COMMAND p2_kurage_bank_test)

add_executable(p2_captive_navi_policy_test
    pc_port/pc_p2_captive_navi_policy_test.cpp)
target_include_directories(p2_captive_navi_policy_test PRIVATE pc_port)
target_compile_options(p2_captive_navi_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_captive_navi_policy_test COMMAND p2_captive_navi_policy_test)

add_executable(p2_tamago_policy_test
    pc_port/pc_p2_tamago_policy_test.cpp)
target_include_directories(p2_tamago_policy_test PRIVATE pc_port)
target_compile_options(p2_tamago_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_tamago_policy_test COMMAND p2_tamago_policy_test)

# Smoke-seed slot bypass (#944): engine-free env-gated predicate contract.
add_executable(p2_smoke_any_slot_test
    pc_port/pc_p2_smoke_any_slot_test.cpp)
target_include_directories(p2_smoke_any_slot_test PRIVATE pc_port)
target_compile_options(p2_smoke_any_slot_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_smoke_any_slot_test COMMAND p2_smoke_any_slot_test)

# P2 boss arenas (owner ruling 2026-09-29): engine-free suppress/probe table.
add_executable(p2_boss_arena_policy_test
    pc_port/pc_p2_boss_arena_policy_test.cpp)
target_include_directories(p2_boss_arena_policy_test PRIVATE pc_port)
target_compile_options(p2_boss_arena_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_boss_arena_policy_test COMMAND p2_boss_arena_policy_test)

# Generic held ship part (#901): engine-free birth/drop contract.
add_executable(pc_held_part_policy_test
    pc_port/pc_held_part_policy_test.cpp)
target_include_directories(pc_held_part_policy_test PRIVATE pc_port)
target_compile_options(pc_held_part_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME pc_held_part_policy_test COMMAND pc_held_part_policy_test)

# Frog identity policy (inst-frogs #871): engine-free params/FSM/clip contract.
add_executable(p2_frog_policy_test tools/p2_frog_policy_test.cpp)
target_include_directories(p2_frog_policy_test PRIVATE pc_port)
target_compile_options(p2_frog_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_frog_policy_test COMMAND p2_frog_policy_test)

# Tank/Wtank identity policy (inst2-frogs #871).
add_executable(p2_tank_policy_test tools/p2_tank_policy_test.cpp)
target_include_directories(p2_tank_policy_test PRIVATE pc_port)
target_compile_options(p2_tank_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_tank_policy_test COMMAND p2_tank_policy_test)

# Tank/Wtank breath exposure: no receiver cap, source box, KEYEVENT_2, growth (#884).
add_executable(p2_tank_breath_test tools/p2_tank_breath_test.cpp)
target_include_directories(p2_tank_breath_test PRIVATE pc_port)
target_compile_options(p2_tank_breath_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_tank_breath_test COMMAND p2_tank_breath_test)

# Watery Blowhog breath stream layout (visual only).
add_executable(p2_tank_stream_test tools/p2_tank_stream_test.cpp)
target_include_directories(p2_tank_stream_test PRIVATE pc_port)
target_compile_options(p2_tank_stream_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_tank_stream_test COMMAND p2_tank_stream_test)
# Shared P2 attack-effect layouts/lifecycle and the Titan Dweevil weapon visuals
# (engine-free). Laser selection finding for the owner playtest 2026-09-30.
add_executable(p2_attack_fx_test tools/p2_attack_fx_test.cpp)
target_include_directories(p2_attack_fx_test PRIVATE pc_port)
target_compile_options(p2_attack_fx_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_attack_fx_test COMMAND p2_attack_fx_test)
add_executable(p2_gas_cloud_test tools/p2_gas_cloud_test.cpp)
target_include_directories(p2_gas_cloud_test PRIVATE pc_port)
target_compile_options(p2_gas_cloud_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_gas_cloud_test COMMAND p2_gas_cloud_test)
add_executable(p2_bigtreasure_fx_test
    tools/p2_bigtreasure_fx_test.cpp
    pc_port/pc_p2_bigtreasure.cpp
    pc_port/pc_p2_bigtreasure_attacks.cpp
    pc_port/pc_p2_bigtreasure_elements.cpp)
target_include_directories(p2_bigtreasure_fx_test PRIVATE pc_port)
target_compile_options(p2_bigtreasure_fx_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_bigtreasure_fx_test COMMAND p2_bigtreasure_fx_test)


# Kabuto identity policy (inst2-frogs #871).
# Camera-facing billboard vertex groups (#1027, Dirigibug balloons): engine-free.
add_executable(p2_billboard_groups_test tools/p2_billboard_groups_test.cpp)
target_include_directories(p2_billboard_groups_test PRIVATE pc_port)
target_compile_options(p2_billboard_groups_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_billboard_groups_test COMMAND p2_billboard_groups_test)

# Antenna Beetle / Dirigibug smoothing helpers (#972): engine-free.
add_executable(p2_fuefuki_bombsarai_smooth_test tools/p2_fuefuki_bombsarai_smooth_test.cpp)
target_include_directories(p2_fuefuki_bombsarai_smooth_test PRIVATE pc_port)
target_compile_options(p2_fuefuki_bombsarai_smooth_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_fuefuki_bombsarai_smooth_test COMMAND p2_fuefuki_bombsarai_smooth_test)

add_executable(p2_kabuto_fsm_policy_test tools/p2_kabuto_fsm_policy_test.cpp)
target_include_directories(p2_kabuto_fsm_policy_test PRIVATE pc_port)
target_compile_options(p2_kabuto_fsm_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kabuto_fsm_policy_test COMMAND p2_kabuto_fsm_policy_test)
# #884 Kabuto 75 travelling Stone: KEYEVENT_2 emission + fleet lifecycle (engine-free).
add_executable(p2_kabuto_stone_fleet_test tools/p2_kabuto_stone_fleet_test.cpp pc_port/pc_p2_cannon_stone.cpp)
target_include_directories(p2_kabuto_stone_fleet_test PRIVATE pc_port)
target_compile_options(p2_kabuto_stone_fleet_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kabuto_stone_fleet_test COMMAND p2_kabuto_stone_fleet_test)
# #884 wiring guard: the shipped Kabuto FSM / gameCoreSection / MapMgr glue must
# call the seam p2_kabuto_stone_fleet_test drives (fails on a revert of the glue).
add_executable(p2_kabuto_stone_wiring_test tools/p2_kabuto_stone_wiring_test.cpp)
target_compile_definitions(p2_kabuto_stone_wiring_test PRIVATE P2_KABUTO_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_options(p2_kabuto_stone_wiring_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_kabuto_stone_wiring_test COMMAND p2_kabuto_stone_wiring_test)

# Mamuta OWN FSM policy (own44 #871): engine-free params/state/config contract.
add_executable(p2_mamuta_fsm_policy_test tools/p2_mamuta_fsm_policy_test.cpp)
target_include_directories(p2_mamuta_fsm_policy_test PRIVATE pc_port)
target_compile_options(p2_mamuta_fsm_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_mamuta_fsm_policy_test COMMAND p2_mamuta_fsm_policy_test)

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

# #215 Demon (Bumbling Snitchbug, 32) species-profile policy test. Engine-free:
# retail parms loader, the Demon 3 s attack timer, Demon::getAttackableTarget
# geometry, hunt descent, climb/weight decisions and the EnemyBase simulation.
add_executable(p2_demon_profile_test tools/p2_demon_profile_test.cpp)
target_include_directories(p2_demon_profile_test PRIVATE pc_port)
target_compile_options(p2_demon_profile_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_demon_profile_test COMMAND p2_demon_profile_test)

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

add_executable(p2_kurage_suction_test tools/test_p2_kurage_suction.cpp)
target_include_directories(p2_kurage_suction_test PRIVATE pc_port)
target_compile_options(p2_kurage_suction_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kurage_suction_test COMMAND p2_kurage_suction_test)

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

endif()


if(PIKMIN_BUILD_LAUNCHER)

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
        pc_port/pc_icon.cpp
        ${LAUNCHER_PLATFORM_SOURCE})
    if (WIN32)
        target_sources(pikmin_launcher PRIVATE packaging/windows/nectar.rc)
    endif()
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

    # Both executables must remain side by side: the launcher resolves the game
    # binary relative to itself, so this also works in relocatable archives.
    install(TARGETS pikmin_launcher RUNTIME DESTINATION bin)
endif()

install(TARGETS ${NECTAR_GAME} RUNTIME DESTINATION bin)

# Tests del launcher: necesitan tanto los tests habilitados como el launcher.
if(PIKMIN_BUILD_TESTS AND PIKMIN_BUILD_LAUNCHER)
    add_executable(gamecube_image_test
        pc_port/launcher/gamecube_image_test.cpp)
    target_link_libraries(gamecube_image_test PRIVATE pikmin_disc_image)
    target_compile_options(gamecube_image_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME gamecube_image_test COMMAND gamecube_image_test)

    add_executable(sha256_test
        pc_port/launcher/sha256_test.cpp)
    target_link_libraries(sha256_test PRIVATE pikmin_disc_image)
    target_compile_options(sha256_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME sha256_test COMMAND sha256_test)

    add_executable(installer_ui_test
        pc_port/launcher/installer_ui_test.cpp
        pc_port/launcher/installer_ui.cpp
        pc_port/pc_icon.cpp)
    target_include_directories(installer_ui_test PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/pc_port/launcher
        ${SDL2_INCLUDE_DIRS})
    target_link_libraries(installer_ui_test PRIVATE ${SDL2_LIBRARIES})
    target_compile_options(installer_ui_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
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
endif()

if(PIKMIN_BUILD_TESTS)
    add_executable(pc_generator_cache_validation_test
        pc_port/save/pc_generator_cache_validation_test.cpp)
    target_include_directories(pc_generator_cache_validation_test PRIVATE pc_port/save)
    target_compile_options(pc_generator_cache_validation_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_generator_cache_validation_test COMMAND pc_generator_cache_validation_test)

    # Better Pathfinding planner checked against brute force (not linked into main game)
    add_executable(pc_route_planner_test pc_port/pc_route_planner_test.cpp pc_port/pc_route_planner.cpp)
    target_compile_options(pc_route_planner_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_route_planner_test COMMAND pc_route_planner_test)

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

    # Gamepad binding routing and its settings lines (no controller needed)
    add_executable(pc_pad_bindings_test pc_port/pc_pad_bindings_test.cpp pc_port/pc_pad_bindings.cpp)
    target_include_directories(pc_pad_bindings_test PRIVATE ${SDL2_INCLUDE_DIRS} pc_port)
    target_compile_options(pc_pad_bindings_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_pad_bindings_test COMMAND pc_pad_bindings_test)
    # Netplay input record/replay format (#878, host-only, no game needed)
    add_executable(pc_input_log_test pc_port/netplay/pc_input_log_test.cpp pc_port/netplay/pc_input_log.cpp)
    target_include_directories(pc_input_log_test PRIVATE pc_port include)
    target_compile_options(pc_input_log_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_input_log_test COMMAND pc_input_log_test)

    # Netplay desync forensics (#1037, host-only, no game needed): session input
    # log format and the desync exchange data model.
    add_executable(pc_netplay_forensics_test
        pc_port/netplay/pc_netplay_forensics_test.cpp
        pc_port/netplay/pc_netplay_inlog.cpp
        pc_port/netplay/pc_netplay_forensics.cpp)
    target_include_directories(pc_netplay_forensics_test PRIVATE pc_port)
    target_compile_options(pc_netplay_forensics_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_netplay_forensics_test COMMAND pc_netplay_forensics_test)

    # Netplay replay tool self test (#878, tool logic only, launches no game)
    # Portable interpreter: py -3.12 on Windows (tree convention), python3
    # elsewhere so PIKMIN_BUILD_TESTS also works on non-Windows hosts.
    if(WIN32)
        add_test(NAME netplay_replay_selftest
            COMMAND py -3.12 "${CMAKE_CURRENT_SOURCE_DIR}/tools/netplay/selftest.py")
    else()
        find_package(Python3 COMPONENTS Interpreter)
        add_test(NAME netplay_replay_selftest
            COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/netplay/selftest.py")
    endif()

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

    # Direct-boot co-op switch parse/apply (netplay M0; no game needed)
    add_executable(pc_coop_switch_test pc_port/netplay/pc_coop_switch_test.cpp pc_port/netplay/pc_coop_switch.cpp pc_port/pc_coop.cpp)
    target_include_directories(pc_coop_switch_test PRIVATE pc_port)
    target_compile_options(pc_coop_switch_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_coop_switch_test COMMAND pc_coop_switch_test)

    # Netplay M4 D-policy co-op randomizer rules (#885; engine-free, no game needed)
    add_executable(pc_coop_policy_test pc_port/pc_coop_policy_test.cpp pc_port/pc_coop_policy.cpp)
    target_include_directories(pc_coop_policy_test PRIVATE pc_port)
    target_compile_options(pc_coop_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_coop_policy_test COMMAND pc_coop_policy_test)

    # Co-op geyser launch gate (#1035; header-only, no game needed)
    add_executable(pc_geyser_gate_test pc_port/pc_geyser_gate_test.cpp)
    target_include_directories(pc_geyser_gate_test PRIVATE pc_port)
    target_compile_options(pc_geyser_gate_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_geyser_gate_test COMMAND pc_geyser_gate_test)

    # Netplay input-ownership selection (launch lane; header-only, no SDL/game)
    add_executable(pc_netplay_input_sel_test pc_port/netplay/pc_netplay_input_sel_test.cpp)
    target_include_directories(pc_netplay_input_sel_test PRIVATE pc_port)
    target_compile_options(pc_netplay_input_sel_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_netplay_input_sel_test COMMAND pc_netplay_input_sel_test)

    # Netplay launcher pure pieces (launch lane; header-only, no SDL/game):
    # SESSION re-stamp, bootstrap acceptance, run layout, code classes.
    add_executable(pc_netplay_launch_test pc_port/netplay/pc_netplay_launch_test.cpp)
    target_include_directories(pc_netplay_launch_test PRIVATE pc_port)
    target_compile_options(pc_netplay_launch_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_netplay_launch_test COMMAND pc_netplay_launch_test)

    # Netplay M5c lane C (issue #887; header-only, no SDL/game): --continue's
    # run folders, checkpoint checks, campaign record and recovery message,
    # and the session HUD's stall window, quality colour and text.
    add_executable(pc_netplay_continue_test pc_port/netplay/pc_netplay_continue_test.cpp)
    target_include_directories(pc_netplay_continue_test PRIVATE pc_port)
    target_compile_options(pc_netplay_continue_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_netplay_continue_test COMMAND pc_netplay_continue_test)
    add_executable(pc_netplay_hud_model_test pc_port/netplay/pc_netplay_hud_model_test.cpp)
    target_include_directories(pc_netplay_hud_model_test PRIVATE pc_port)
    target_compile_options(pc_netplay_hud_model_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_netplay_hud_model_test COMMAND pc_netplay_hud_model_test)

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
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/assets/dataDir/SndData/Banks/pikibank.bx")
        add_test(NAME pc_jam_test COMMAND pc_jam_test)
        set_tests_properties(pc_jam_test PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")
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
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/assets/dataDir/SndData/Banks/pikibank.bx")
        add_test(NAME pc_audio_mixer_test COMMAND pc_audio_mixer_test)
        set_tests_properties(pc_audio_mixer_test PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")
    endif()

    # Netplay audio ownership gate (issue #1030). Host-run, header-only.
    add_executable(pc_audio_source_test pc_port/audio/pc_audio_source_test.cpp)
    target_include_directories(pc_audio_source_test PRIVATE pc_port)
    target_compile_options(pc_audio_source_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_audio_source_test COMMAND pc_audio_source_test)

    # Sequencer clock guard (issue #1030). Host-run, header-only.
    add_executable(pc_audio_clock_test pc_port/audio/pc_audio_clock_test.cpp)
    target_include_directories(pc_audio_clock_test PRIVATE pc_port)
    target_compile_options(pc_audio_clock_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_audio_clock_test COMMAND pc_audio_clock_test)

    add_executable(pc_frame_scheduler_test
        pc_port/timing/pc_frame_scheduler_test.cpp
        pc_port/timing/pc_frame_scheduler.cpp)
    target_compile_options(pc_frame_scheduler_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_frame_scheduler_test COMMAND pc_frame_scheduler_test)

    # Deterministic netplay RNG streams, M1 (issue #878). Host-run; covers
    # the MSL sequence, state round-trip, stream independence and the
    # rand() passthrough when deterministic mode is off.
    add_executable(pc_sim_rng_test
        pc_port/netplay/pc_sim_rng_test.cpp
        pc_port/netplay/pc_sim_rng.cpp
        pc_port/netplay/pc_netplay_det.cpp)
    target_compile_options(pc_sim_rng_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_sim_rng_test COMMAND pc_sim_rng_test)

    # Netplay sim-visibility policy, M2a (issue #879). Host-run; covers the
    # pass-through contract with the switch off and the pinned sim values
    # (visible / 16:9 / near LOD) with the switch on.
    add_executable(pc_netplay_policy_test
        pc_port/netplay/pc_netplay_policy_test.cpp
        pc_port/netplay/pc_netplay_policy.cpp
        pc_port/netplay/pc_netplay_det.cpp
        pc_port/netplay/pc_sim_rng.cpp)
    target_compile_options(pc_netplay_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_netplay_policy_test COMMAND pc_netplay_policy_test)

    # Netplay M2b two-pass present module (issue #879). Host-run; covers the
    # skip-presentation flag and the null-GX counters.
    add_executable(pc_netplay_present_test
        pc_port/netplay/pc_netplay_present_test.cpp
        pc_port/netplay/pc_netplay_present.cpp
        pc_port/netplay/pc_netplay_det.cpp
        pc_port/netplay/pc_sim_rng.cpp)
    target_compile_definitions(pc_netplay_present_test PRIVATE PC_NETPLAY_PRESENT_HOST=1)
    target_compile_options(pc_netplay_present_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_netplay_present_test COMMAND pc_netplay_present_test)

    # Netplay M5c lane A lead camera core (issue #887; header-only, no game):
    # key mapping, input history, prediction window, correction filter.
    add_executable(pc_netplay_camlead_test pc_port/netplay/pc_netplay_camlead_test.cpp)
    target_include_directories(pc_netplay_camlead_test PRIVATE pc_port)
    target_compile_options(pc_netplay_camlead_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_netplay_camlead_test COMMAND pc_netplay_camlead_test)

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

    add_executable(pc_tev_order_test pc_port/gl/pc_tev_order_test.cpp)
    target_include_directories(pc_tev_order_test PRIVATE pc_port/gl)
    target_compile_options(pc_tev_order_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_tev_order_test COMMAND pc_tev_order_test)

    # Post-process shader generation (no GL context needed)
    add_executable(pc_postprocess_test
        pc_port/gl/pc_postprocess_test.cpp
        pc_port/gl/pc_postprocess.cpp
    )
    target_include_directories(pc_postprocess_test PRIVATE pc_port/gl)
    target_compile_options(pc_postprocess_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_postprocess_test COMMAND pc_postprocess_test)

    # Polish deferred texture-init store (issues #879 #880, fix2 m3): links
    # the real unit, not a model of it. No GL context needed.
    add_executable(pc_gfx_deferred_test
        pc_port/gl/pc_gfx_deferred_test.cpp
        pc_port/gl/pc_gfx_deferred_tex.cpp
    )
    target_include_directories(pc_gfx_deferred_test PRIVATE pc_port/gl)
    target_compile_options(pc_gfx_deferred_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_gfx_deferred_test COMMAND pc_gfx_deferred_test)

    add_executable(pc_render_packet_test
        pc_port/timing/pc_render_packet_test.cpp
        pc_port/timing/pc_render_packet.cpp)
    target_compile_options(pc_render_packet_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_render_packet_test COMMAND pc_render_packet_test)

    add_executable(pc_tick_profiler_test
        pc_port/timing/pc_tick_profiler_test.cpp
        pc_port/timing/pc_tick_profiler.cpp
        pc_port/netplay/pc_netplay_det.cpp
        pc_port/netplay/pc_sim_rng.cpp)
    target_include_directories(pc_tick_profiler_test PRIVATE pc_port/timing)
    target_compile_options(pc_tick_profiler_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
    add_test(NAME pc_tick_profiler_test COMMAND pc_tick_profiler_test)
endif()

message(STATUS "")
message(STATUS "╔══════════════════════════════════════════╗")
message(STATUS "║   Pikmin PC Port - Build Configuration   ║")
message(STATUS "╠══════════════════════════════════════════╣")
message(STATUS "║   Version:  USA Rev 1 (GPIE01_01)       ║")
if(PIKMIN_GLES)
    message(STATUS "║   Graphics: Native GX → OpenGL ES 3.0   ║")
else()
    message(STATUS "║   Graphics: Native GX → OpenGL          ║")
endif()
message(STATUS "║   Audio:    SDL mixer/STX; JAudio WIP   ║")
message(STATUS "║   Input:    Native SDL keyboard/gamepad ║")
message(STATUS "╚══════════════════════════════════════════╝")
message(STATUS "")

if(PIKMIN_NATIVE_JAUDIO AND PIKMIN_BUILD_TESTS)
    add_test(NAME pc_jaudio_integration_test COMMAND ${NECTAR_GAME} --audio-self-test)
    set_tests_properties(pc_jaudio_integration_test PROPERTIES
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" TIMEOUT 30
        SKIP_RETURN_CODE 77 LABELS "game-assets")
endif()

# Standalone adapter harness; exercises real file I/O without game assets.
# Include the P2 ordinary delivery ledger because pc_randomizer.cpp always links
# against its host entry points; this only changes probe linkage, not behavior.
add_executable(pc_randomizer_probe pc_port/pc_randomizer_probe.cpp pc_port/pc_randomizer.cpp pc_port/netplay/pc_netplay_randstate.cpp pc_port/pc_randomizer_outbox.cpp pc_port/pc_p2_delivery_host.cpp pc_port/pc_p2_proxy.cpp)
# Same engine-header preinclude as pc_bbft_test above (pc_p2_proxy.cpp needs it).
target_compile_options(pc_randomizer_probe PRIVATE ${NATIVE_COMPILE_OPTIONS})

# Netplay M4 lane A snapshot codec + reassembler test (issue #885).
# Engine-free (no gekkonet/game/SDL link), registered in every build.
add_executable(pc_netplay_randstate_test pc_port/netplay/pc_netplay_randstate_test.cpp pc_port/netplay/pc_netplay_randstate.cpp)
target_include_directories(pc_netplay_randstate_test PRIVATE pc_port)
target_compile_options(pc_netplay_randstate_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_netplay_randstate_test COMMAND pc_netplay_randstate_test)

# Netplay M4 lane B1 outbox / mirror line / session.json ledger test
# (issue #885). Engine-free, registered in every build.
add_executable(pc_randomizer_outbox_test pc_port/pc_randomizer_outbox_test.cpp pc_port/pc_randomizer_outbox.cpp)
target_include_directories(pc_randomizer_outbox_test PRIVATE pc_port)
target_compile_options(pc_randomizer_outbox_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_randomizer_outbox_test COMMAND pc_randomizer_outbox_test)
# B1 fix round 1: pc_randomizer.cpp's outbox-active host journals and client
# mirror (exact bytes) against stub session hooks, one process per role.
add_executable(pc_randomizer_outbox_io_test pc_port/pc_randomizer_outbox_io_test.cpp pc_port/pc_randomizer.cpp pc_port/netplay/pc_netplay_randstate.cpp pc_port/pc_randomizer_outbox.cpp pc_port/pc_p2_delivery_host.cpp pc_port/pc_p2_proxy.cpp)
target_include_directories(pc_randomizer_outbox_io_test PRIVATE pc_port)
target_compile_options(pc_randomizer_outbox_io_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_randomizer_outbox_io_host_test COMMAND pc_randomizer_outbox_io_test host)
add_test(NAME pc_randomizer_outbox_io_host_noledger_test COMMAND pc_randomizer_outbox_io_test host-noledger)
add_test(NAME pc_randomizer_outbox_io_client_test COMMAND pc_randomizer_outbox_io_test client)
add_test(NAME pc_randomizer_outbox_io_client_unknown_test COMMAND pc_randomizer_outbox_io_test client-unknown)

# Netplay M4 lane B2 (issue #885): the engine-free Hello v3 / decision table /
# bundle / SAVE_RESULT codecs (header-only pc_netplay_transfer.h), and
# pc_randomizer.cpp's day-end save barrier path, checkpoint info, adoption
# and join-mode stale set-aside against stub session hooks (one process per
# role; host-stale must print the historical fatal message and exit).
add_executable(pc_netplay_transfer_test pc_port/netplay/pc_netplay_transfer_test.cpp)
target_include_directories(pc_netplay_transfer_test PRIVATE pc_port)
target_compile_options(pc_netplay_transfer_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_netplay_transfer_test COMMAND pc_netplay_transfer_test)
add_executable(pc_randomizer_campaign_net_test pc_port/pc_randomizer_campaign_net_test.cpp pc_port/pc_randomizer.cpp pc_port/netplay/pc_netplay_randstate.cpp pc_port/pc_randomizer_outbox.cpp pc_port/pc_p2_delivery_host.cpp pc_port/pc_p2_proxy.cpp)
target_include_directories(pc_randomizer_campaign_net_test PRIVATE pc_port)
target_compile_options(pc_randomizer_campaign_net_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME pc_randomizer_campaign_net_host_test COMMAND pc_randomizer_campaign_net_test host)
add_test(NAME pc_randomizer_campaign_net_client_test COMMAND pc_randomizer_campaign_net_test client)
add_test(NAME pc_randomizer_campaign_net_join_stale_test COMMAND pc_randomizer_campaign_net_test join-stale)
# B2 fix round 1: the pending mirror checkpoint retracted by an abandoned
# barrier (C2), and the host's two fatal stale cases split (X8); each fatal
# role runs itself as a child and asserts exit code 2 plus the exact message.
add_test(NAME pc_randomizer_campaign_net_client_abandon_test COMMAND pc_randomizer_campaign_net_test client-abandon)
add_test(NAME pc_randomizer_campaign_net_host_stale_foreign_test COMMAND pc_randomizer_campaign_net_test host-stale-foreign)
add_test(NAME pc_randomizer_campaign_net_host_stale_badname_test COMMAND pc_randomizer_campaign_net_test host-stale-badname)

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
add_executable(p2_elecbug_fsm_test tools/p2_elecbug_fsm_test.cpp)
target_include_directories(p2_elecbug_fsm_test PRIVATE pc_port)
target_compile_options(p2_elecbug_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_elecbug_fsm_test COMMAND p2_elecbug_fsm_test)
add_executable(p2_elecbug_fx_test tools/p2_elecbug_fx_test.cpp)
target_include_directories(p2_elecbug_fx_test PRIVATE pc_port)
target_compile_options(p2_elecbug_fx_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_elecbug_fx_test COMMAND p2_elecbug_fx_test)
add_executable(p2_species_unit_test tools/p2_species_unit_test.cpp)
target_include_directories(p2_species_unit_test PRIVATE pc_port)
target_compile_options(p2_species_unit_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_species_unit_test COMMAND p2_species_unit_test)

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
# Kurage57 campaign fixes (#871): engine-free gate/hover/probe contract for the
# bridge-mode concessions skip, visual hover height and once-per-frame tail.
add_executable(p2_kurage_campaign_test tools/test_p2_kurage_campaign.cpp)
target_include_directories(p2_kurage_campaign_test PRIVATE pc_port)
target_compile_options(p2_kurage_campaign_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_kurage_campaign_test COMMAND p2_kurage_campaign_test)
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
# inst-chappy (#871): engine-free Chappy-family policy/FSM unit tests
# (header-only retail parms, sidecar parse, per-actor health registry and
# the adult/kuma/kumako/king transition tables).
add_executable(p2_chappy_policy_test tools/p2_chappy_policy_test.cpp)
target_include_directories(p2_chappy_policy_test PRIVATE pc_port)
target_compile_options(p2_chappy_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_chappy_policy_test COMMAND p2_chappy_policy_test)
add_executable(p2_chappy_fsm_test tools/p2_chappy_fsm_test.cpp)
target_include_directories(p2_chappy_fsm_test PRIVATE pc_port)
target_compile_options(p2_chappy_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_chappy_fsm_test COMMAND p2_chappy_fsm_test)
add_executable(p2_chappy_adult_test tools/p2_chappy_adult_test.cpp)
target_include_directories(p2_chappy_adult_test PRIVATE pc_port)
target_compile_options(p2_chappy_adult_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_chappy_adult_test COMMAND p2_chappy_adult_test)
# p2-884-chappy (#884): engine-free source mouth-slot eating (EnemyFunc::eatPikmin
# geometry, capacity, eligibility, host-part mapping, King sweep, legacy oracle).
add_executable(p2_mouth_snapshot_test tools/p2_mouth_snapshot_test.cpp)
target_include_directories(p2_mouth_snapshot_test PRIVATE pc_port)
target_compile_options(p2_mouth_snapshot_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_mouth_snapshot_test COMMAND p2_mouth_snapshot_test)
add_executable(p2_chappy_mouth_test tools/p2_chappy_mouth_test.cpp)
target_include_directories(p2_chappy_mouth_test PRIVATE pc_port)
target_compile_options(p2_chappy_mouth_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_chappy_mouth_test COMMAND p2_chappy_mouth_test)
# #996: engine-free Skitter Leaf shake-off / carcass policy (source isStartFlick).
add_executable(p2_sokkuri_flick_test tools/p2_sokkuri_flick_test.cpp)
target_include_directories(p2_sokkuri_flick_test PRIVATE pc_port)
target_compile_options(p2_sokkuri_flick_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_sokkuri_flick_test COMMAND p2_sokkuri_flick_test)
# wave3 lane 53 (#289): engine-free Emperor Bulblax life-cycle rules (buried spawn,
# proximity Appear, cross-Emperor request, bomb ingestion + stun clock, tongue tip table).
add_executable(p2_king_life_test tools/p2_king_life_test.cpp)
target_include_directories(p2_king_life_test PRIVATE pc_port)
target_compile_options(p2_king_life_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_king_life_test COMMAND p2_king_life_test)
# p2-886 (#886): engine-free captor mouth slots (Jigumo/Snagret/UmiMushi/
# Armor/Uji eatPikmin geometry, Jigumo height check, Snagret facing boxes,
# held registry + swallow, legacy XZ-nearest/raw-pointer oracle).
add_executable(p2_captor_mouth_test tools/p2_captor_mouth_test.cpp)
target_include_directories(p2_captor_mouth_test PRIVATE pc_port)
target_compile_options(p2_captor_mouth_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_captor_mouth_test COMMAND p2_captor_mouth_test)
# Cloaking Burrow-nit (Armor 15, #1014): retail collision tree (only dmg1 stickable), attack cone,
# kamujnt bite sweep, captain hit and damage predicates. Engine-free.
add_executable(p2_armor_policy_test tools/p2_armor_policy_test.cpp)
target_include_directories(p2_armor_policy_test PRIVATE pc_port)
target_compile_options(p2_armor_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_armor_policy_test COMMAND p2_armor_policy_test)

# #995: Bloyster source policy (tail bulb is the only stickable part, damageCallBack, tongue tables).
add_executable(p2_umimushi_policy_test tools/p2_umimushi_policy_test.cpp)
target_include_directories(p2_umimushi_policy_test PRIVATE pc_port)
target_compile_options(p2_umimushi_policy_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_umimushi_policy_test COMMAND p2_umimushi_policy_test)
add_executable(p2_skewer_test tools/p2_skewer_test.cpp)
target_include_directories(p2_skewer_test PRIVATE pc_port)
target_compile_options(p2_skewer_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_skewer_test COMMAND p2_skewer_test)
# bot-impl (#871): TEST-ONLY headless autoplay bot policy. Engine-free:
# the header-only Brain (states, timeouts, giveup/result markers, Kogane
# damage-and-move-on) plus the inert-when-unset gate (registration only).
add_executable(p2_autoplay_test tools/p2_autoplay_test.cpp)
target_include_directories(p2_autoplay_test PRIVATE pc_port)
target_compile_options(p2_autoplay_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_autoplay_test COMMAND p2_autoplay_test)
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

# #215 latch fix: engine-free fixtures for the Demon anchor collision tree,
# body offset, CF_IsFlying mirror and Lock-On peak pin (pc_p2_demon_anchor.h).
add_executable(p2_demon_anchor_test tools/p2_demon_anchor_test.cpp)
target_include_directories(p2_demon_anchor_test PRIVATE pc_port)
target_compile_options(p2_demon_anchor_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_demon_anchor_test COMMAND p2_demon_anchor_test)

# Wave 3 flyers (#960): CF_IsFlying mirror rule, retail Kurage collision tree,
# walk/turn maths and the source clip clock driving the Kurage FSM.
add_executable(p2_flyer_test tools/p2_flyer_test.cpp)
target_include_directories(p2_flyer_test PRIVATE pc_port)
target_compile_options(p2_flyer_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_flyer_test COMMAND p2_flyer_test)

# Shared P2 body-collision fit (stuck Pikmin sit on the drawn surface).
add_executable(p2_body_fit_test tools/p2_body_fit_test.cpp)
target_include_directories(p2_body_fit_test PRIVATE pc_port)
target_compile_options(p2_body_fit_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_body_fit_test COMMAND p2_body_fit_test)
# Dev audit: fit every species rest pose in a content tree (tools/p2_body_fit_audit.cpp).
add_executable(p2_body_fit_audit EXCLUDE_FROM_ALL tools/p2_body_fit_audit.cpp)
target_include_directories(p2_body_fit_audit PRIVATE pc_port)

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

foreach(policy IN ITEMS demon_captor demon_escape demon_pose sarai_fsm sarai_policy sarai_capture fuefuki_follow fuefuki_follow_binding uji)
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
add_executable(p2_pose_motion_test tools/p2_pose_motion_test.cpp )
target_include_directories(p2_pose_motion_test PRIVATE pc_port)
target_compile_options(p2_pose_motion_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_pose_motion_test COMMAND p2_pose_motion_test)
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
# #892: three-shell burst policy (one emit key, same tick, +-0.1 jitter) and the retail
# armour-cover collision policy (only `body` is stickable).
add_executable(p2_groink_burst_test tools/p2_groink_burst_test.cpp pc_port/pc_p2_groink_volley.cpp pc_port/pc_p2_groink.cpp)
target_include_directories(p2_groink_burst_test PRIVATE pc_port)
target_compile_options(p2_groink_burst_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_burst_test COMMAND p2_groink_burst_test)
add_executable(p2_groink_coll_test tools/p2_groink_coll_test.cpp)
target_include_directories(p2_groink_coll_test PRIVATE pc_port)
target_compile_options(p2_groink_coll_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_coll_test COMMAND p2_groink_coll_test)
# #888 WP5: engine-free NormMiniHoudai/FixMiniHoudai source FSM (states,
# animation key events, gun aim, 3-shell volleys, shake-off, death).
# #898 Breadbug (PanModoki 38) engine-free source FSM.
add_executable(p2_breadbug_fsm_test tools/p2_breadbug_fsm_test.cpp pc_port/pc_p2_breadbug_fsm.cpp)
target_include_directories(p2_breadbug_fsm_test PRIVATE pc_port)
target_compile_options(p2_breadbug_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_breadbug_fsm_test COMMAND p2_breadbug_fsm_test)
add_executable(p2_groink_fsm_test tools/p2_groink_fsm_test.cpp pc_port/pc_p2_groink_fsm.cpp
    pc_port/pc_p2_groink.cpp pc_port/pc_p2_groink_attack.cpp pc_port/pc_p2_groink_volley.cpp
    pc_port/pc_p2_groink_hit.cpp pc_port/pc_p2_groink_target.cpp)
target_include_directories(p2_groink_fsm_test PRIVATE pc_port)
target_compile_options(p2_groink_fsm_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_fsm_test COMMAND p2_groink_fsm_test)
# #892: Groink shell visuals (TChibiShoot/TChibiShell/TChibiHit timing ->
# P1 one-shot effects), policy-only under P2_GROINK_FX_NO_ENGINE.
add_executable(p2_groink_fx_test tools/p2_groink_fx_test.cpp pc_port/pc_p2_groink_fx.cpp pc_port/pc_p2_groink_fsm.cpp
    pc_port/pc_p2_groink.cpp pc_port/pc_p2_groink_attack.cpp pc_port/pc_p2_groink_volley.cpp
    pc_port/pc_p2_groink_hit.cpp pc_port/pc_p2_groink_target.cpp)
target_include_directories(p2_groink_fx_test PRIVATE pc_port)
target_compile_definitions(p2_groink_fx_test PRIVATE P2_GROINK_FX_NO_ENGINE)
target_compile_options(p2_groink_fx_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_groink_fx_test COMMAND p2_groink_fx_test)
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

# Dev console grammar (#942): engine-free parser/species table contract.
add_executable(pc_dev_console_parser_test pc_port/pc_dev_console_parser_test.cpp)
target_include_directories(pc_dev_console_parser_test PRIVATE pc_port)
target_compile_options(pc_dev_console_parser_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME pc_dev_console_parser_test COMMAND pc_dev_console_parser_test)
add_executable(pc_p2_life_gauge_test pc_port/pc_p2_life_gauge_test.cpp)
target_include_directories(pc_p2_life_gauge_test PRIVATE pc_port)
target_compile_options(pc_p2_life_gauge_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME pc_p2_life_gauge_test COMMAND pc_p2_life_gauge_test)

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

add_executable(p2_bomb_pulse_test tools/p2_bomb_pulse_test.cpp)
target_include_directories(p2_bomb_pulse_test PRIVATE pc_port)
target_compile_options(p2_bomb_pulse_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_bomb_pulse_test COMMAND p2_bomb_pulse_test)
# Explicit replacement-main diagnostics: CI compiles/packages but never runs
# them or receives local game assets. Default production builds stay unchanged.
file(WRITE "${CMAKE_BINARY_DIR}/ci-fixtures.txt" "")
function(pikmin_add_ci_fixture name source)
    if(ANDROID)
        return()
    endif()
    if(NOT name MATCHES "^[a-z0-9_]+$" OR NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${source}")
        message(FATAL_ERROR "Invalid explicit CI fixture: ${name} ${source}")
    endif()
    set(target "pikmin_ci_fixture_${name}")
    # Clone the final production source set, including late-added NETPLAY
    # ICE/launcher/session/HUD TUs, platform resources and libm object binding.
    # PC_PORT_SOURCES predates those additions. Cloning it omitted real symbols;
    # attaching libm separately here would duplicate its existing object source.
    get_target_property(sources ${NECTAR_GAME} SOURCES)
    list(REMOVE_ITEM sources pc_port/pc_main.cpp)
    list(APPEND sources "${source}")
    add_executable(${target} EXCLUDE_FROM_ALL ${sources})
    # Copy final production settings, including platform libraries and IPO.
    # Inherited directory includes/definitions and source properties also apply.
    foreach(prop COMPILE_OPTIONS COMPILE_DEFINITIONS INCLUDE_DIRECTORIES LINK_LIBRARIES LINK_OPTIONS INTERPROCEDURAL_OPTIMIZATION)
        get_target_property(value ${NECTAR_GAME} ${prop})
        if(NOT value STREQUAL "value-NOTFOUND")
            set_property(TARGET ${target} PROPERTY ${prop} "${value}")
        endif()
    endforeach()
    target_include_directories(${target} PRIVATE tools)
    set_target_properties(${target} PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/fixtures")
    file(APPEND "${CMAKE_BINARY_DIR}/ci-fixtures.txt" "${target}\n")
endfunction()

# #928 opt-in captain switching acceptance (requires local assets to run).
pikmin_add_ci_fixture(captain_switch tools/p2_captain_switch_runtime.cpp)

# #1154/#1161 ordinary natural WFG acquisition and cave party route; build only.
pikmin_add_ci_fixture(cave_route tools/p2_cave_route_runtime.cpp)
if(TARGET pikmin_ci_fixture_cave_route)
    target_include_directories(pikmin_ci_fixture_cave_route PRIVATE ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
endif()
# #1157 matched captain combined SDL fixture; opt-in compile/package only.
pikmin_add_ci_fixture(captain_combined_sdl tools/p2_captain_combined_sdl_fixture.cpp)
if(TARGET pikmin_ci_fixture_captain_combined_sdl)
    target_include_directories(pikmin_ci_fixture_captain_combined_sdl PRIVATE ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
endif()
# #1148 ordinary paired SDL/AP acceptance. Explicit compile-only target; the
# NETPLAY=OFF profile cannot substitute for its deterministic consumer linkage.
if(PIKMIN_NETPLAY_BUILD)
    pikmin_add_ci_fixture(coop_state_protocol tools/p2_coop_state_protocol_runtime.cpp)
    if(TARGET pikmin_ci_fixture_coop_state_protocol)
        target_sources(pikmin_ci_fixture_coop_state_protocol PRIVATE tools/p2_coop_fixture_input_snapshot.cpp)
        target_include_directories(pikmin_ci_fixture_coop_state_protocol PRIVATE ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
    endif()
endif()
add_executable(p2_bomb_telegraph_test tools/p2_bomb_telegraph_test.cpp)
target_include_directories(p2_bomb_telegraph_test PRIVATE pc_port)
target_compile_options(p2_bomb_telegraph_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_bomb_telegraph_test COMMAND p2_bomb_telegraph_test)
add_executable(p2_breadbug_corpse_test tools/p2_breadbug_corpse_test.cpp pc_port/pc_p2_breadbug_fsm.cpp)
target_include_directories(p2_breadbug_corpse_test PRIVATE pc_port)
target_compile_options(p2_breadbug_corpse_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_breadbug_corpse_test COMMAND p2_breadbug_corpse_test)
# Demon living-body fade advance regression (#972): engine-free.
add_executable(p2_demon_fade_test
    pc_port/pc_p2_demon_fade_test.cpp)
target_include_directories(p2_demon_fade_test PRIVATE pc_port)
target_compile_options(p2_demon_fade_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
target_compile_definitions(p2_demon_fade_test PRIVATE DEMON_SOURCE="${CMAKE_CURRENT_SOURCE_DIR}/pc_port/pc_p2_sarai_demon.cpp")
add_test(NAME p2_demon_fade_test COMMAND p2_demon_fade_test)

add_executable(pc_corpse_origin_test tools/pc_corpse_origin_test.cpp)
target_include_directories(pc_corpse_origin_test PRIVATE pc_port)
target_compile_options(pc_corpse_origin_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME pc_corpse_origin_test COMMAND pc_corpse_origin_test)

add_executable(p2_breadbug_nest_test tools/p2_breadbug_nest_test.cpp)
target_include_directories(p2_breadbug_nest_test PRIVATE pc_port)
target_compile_options(p2_breadbug_nest_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_breadbug_nest_test COMMAND p2_breadbug_nest_test)

# #1052 live squad reconciliation (engine-free, assertions enabled in Release).
add_executable(p2_captain_reconciliation_test tools/test_p2_captain_reconciliation.cpp)
target_include_directories(p2_captain_reconciliation_test PRIVATE pc_port)
target_compile_options(p2_captain_reconciliation_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_captain_reconciliation_test COMMAND p2_captain_reconciliation_test)

# #940 ordinary Purple combat: bounded local runtime only, never run by CI.
pikmin_add_ci_fixture(purple_combat tools/preview_p2_purple_combat.cpp)
add_executable(p2_purple_combat_bindings_test tools/test_p2_purple_combat_bindings.cpp)
target_include_directories(p2_purple_combat_bindings_test PRIVATE pc_port)
target_compile_options(p2_purple_combat_bindings_test PRIVATE ${NATIVE_COMPILE_OPTIONS} -UNDEBUG)
add_test(NAME p2_purple_combat_bindings_test COMMAND p2_purple_combat_bindings_test)

# Issue1074 bounded local scene reentry; CI builds only.
pikmin_add_ci_fixture(captain_reentry tools/p2_captain_reentry_runtime.cpp)

# #1079 local native card save/resume acceptance, built only on CI.
pikmin_add_ci_fixture(captain_campaign_resume tools/p2_captain_campaign_resume_runtime.cpp)
pikmin_add_ci_fixture(captain_onion_owner_sdl tools/p2_captain_onion_owner_sdl_fixture.cpp)
if(TARGET pikmin_ci_fixture_captain_onion_owner_sdl)
    target_include_directories(pikmin_ci_fixture_captain_onion_owner_sdl PRIVATE ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
endif()

# #1148 complete codec consumer against real randomizer and proxy implementations.
add_executable(pc_randomizer_state_stream_test pc_port/pc_randomizer_state_stream_test.cpp pc_port/pc_randomizer.cpp pc_port/netplay/pc_netplay_randstate.cpp pc_port/pc_randomizer_outbox.cpp pc_port/pc_p2_delivery_host.cpp pc_port/pc_p2_proxy.cpp)
target_include_directories(pc_randomizer_state_stream_test PRIVATE pc_port)
target_compile_options(pc_randomizer_state_stream_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
foreach(mode p1 thelynk)
    add_test(NAME pc_randomizer_state_stream_${mode} COMMAND pc_randomizer_state_stream_test ${mode})
    foreach(fault bad-mode bad-disabled bad-unknown bad-trailing bad-progression)
        add_test(NAME pc_randomizer_state_stream_${mode}_${fault} COMMAND pc_randomizer_state_stream_test ${mode} ${fault})
    endforeach()
endforeach()
# #1150 compile-only original tutorial encounter/carry diagnostic.
pikmin_add_ci_fixture(tutorial_encounter tools/p2_tutorial_encounter_runtime.cpp)
if(TARGET pikmin_ci_fixture_tutorial_encounter)
    target_include_directories(pikmin_ci_fixture_tutorial_encounter PRIVATE ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
endif()

# #1177 compile-only ordinary all-roster upper-terrain traversal.
pikmin_add_ci_fixture(tutorial_upper_traversal tools/p2_tutorial_upper_traversal_runtime.cpp)
if(TARGET pikmin_ci_fixture_tutorial_upper_traversal)
    target_include_directories(pikmin_ci_fixture_tutorial_upper_traversal PRIVATE ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
endif()

# #1178 ordinary Ivory acquisition into sole-White engineering cargo haul; build only.
pikmin_add_ci_fixture(white_carry tools/p2_white_carry_runtime.cpp)
if(TARGET pikmin_ci_fixture_white_carry)
    target_include_directories(pikmin_ci_fixture_white_carry PRIVATE ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
endif()

# #1164 ordinary Anode landing and electrical contact; build only.
pikmin_add_ci_fixture(elecbug_contact tools/p2_elecbug_contact_runtime.cpp)
if(TARGET pikmin_ci_fixture_elecbug_contact)
    target_include_directories(pikmin_ci_fixture_elecbug_contact PRIVATE ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
endif()
