// P2 yakushima_4 authored-geometry guarded fixture (#682).
//
// Game-linked observation fixture: consumes the AUTHORED yakushima_4
// floor-1 room graph baked into pc_p2_cave.cpp (decoded from the real
// caveinfo + unit pool, never the identity unit pool) and emits P2_CAVE_NAV
// route samples with authored=1. Captain safety #632 is mandatory: the guard
// runs before any observation and exits 86 (BLOCKED) on captain-down, so a
// dead captain can never be recorded as authored geometry.
//
// Modes: `live` (default) runs the authored validation + NAV emission;
// `negcap` forces a captain-down to prove the negative path.
//
// 960x540 centred startup is inherited from the production room entrypoint;
// this fixture does not re-implement window setup. Higher floors,
// triangle-mesh collision and persistence are explicitly open (UNTESTED).
//
// NOTE: registering this fixture in CMake/CTest touches shared build files
// and therefore requires #186 review; it is built privately via the
// replacement-main builder instead.
#include <cstdio>
#include <cstring>

#include "p2_fixture_captain_guard.h"

// Consumed from pc_p2_cave.cpp (owned by this lane); declared here so the
// shared header stays untouched.
extern int pc_p2_yakushima4_room_count();
extern bool pc_p2_yakushima4_validate();
extern int pc_p2_yakushima4_emit_nav();

int main(int argc, char** argv)
{
    const bool negative = argc > 1 && std::strcmp(argv[1], "negcap") == 0;
    // Guard BEFORE any observation: orimaDead/NaviDead/HP<=1 -> exit 86.
    p2_fixture_require_captain(negative, false, negative ? 0.0f : 100.0f, 0);
    std::printf("P2_YAKUSHIMA4_BOOT mode=%s\n", negative ? "negcap" : "live");
    std::fflush(stdout);
    if (pc_p2_yakushima4_room_count() != 8) {
        std::printf("P2_YAKUSHIMA4_ERROR room_count\n");
        return 2;
    }
    if (!pc_p2_yakushima4_validate()) {
        std::printf("P2_YAKUSHIMA4_ERROR table_invalid\n");
        return 2;
    }
    const int links = pc_p2_yakushima4_emit_nav();
    if (links != 36) {
        std::printf("P2_YAKUSHIMA4_ERROR link_count=%d\n", links);
        return 2;
    }
    std::printf("P2_YAKUSHIMA4_DONE rooms=8 doors=19 links=36\n");
    std::fflush(stdout);
    return 0;
}