// Guarded P2 challenge stage extension table fixture (lane
// challenge-stage-table-extension-native, issue #730).
//
// Replacement-main convention: mirrors tools/p2_challenge_stage_boot_fixture.cpp
// (#675) -- scenario main instead of pc_main.cpp, 960x540 centred window, and
// the --experimental-pikmin2-room boot. The extension table TU is production
// membership in pikmin_pc (#730 wiring follow-on, #186 decision), so this TU
// links it from the graph and the engine lookup falls through to it.
//
// What this proves (and only this): the wired engine lookup resolves
// ch_ABEM_LeafChappy (#550 pins) and ch_NARI_02tile (#537 pins) field by field
// through the extension fallthrough, the engine table still resolves kusachi
// identically (untouched), and unknown keys are refused everywhere. It boots
// the real engine privately under the room-preview path with a guarded captain.
//
// It does NOT prove content wiring or challenge gameplay: all six gates stay
// UNTESTED and the P2_CHALLENGE_STAGE_EXT_GATES marker says so.
//
// Markers: P2_CHALLENGE_STAGE_EXT_RESOLVED (per-key pin lines),
// P2_CHALLENGE_STAGE_EXT_ENGINE_UNTOUCHED (kusachi via engine only),
// P2_CHALLENGE_STAGE_EXT_FALLTHROUGH (both new keys resolved by the engine
// lookup through the extension), P2_CHALLENGE_STAGE_EXT_WINDOW, _READY,
// _GATES all=UNTESTED, then "PASS CHALLENGE_STAGE_TABLE_EXT" and exit 0.
// Refusals exit 1 with a reason; a guard trip exits BLOCKED (86); timeout 2.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "Node.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "PikiMgr.h"
#include "Piki.h"
#include "Creature.h"
#include "GameStat.h"
#include "MoviePlayer.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "system.h"
#include "teki.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "pc_p2_challenge_stages_ext.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// Extension table TU is production membership in pikmin_pc now, so the graph
// provides pc_p2_challenge_stages_ext_count()/lookup(); no unity include and no
// duplicate definitions.

// Engine table lookup, read-only (defined in pc_port/pc_bbft.cpp, owned by
// lane #675 / READY #728; never modified here).
struct P2ChallengeStageRowEngine {
    const char* caveId;
    const char* cavePath;
    const char* sourceSha256;
    int uiIndex;
    int tableOrder;
    int floors;
    float floorSeconds[8];
    int roster[7][3];
    int bitterSprays;
    int spicySprays;
    float legacyTime;
    int treasureCountField;
};
extern const P2ChallengeStageRowEngine* pc_p2_challenge_stage_lookup(const char* caveId);

// Captain-safety guard (#632), vendored verbatim from
// scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474).
// Observation-only; the canonical header is consumed read-only at review. A
// replacement-main TU cannot include a Python-tree script header at native
// build time, so the exact guard body is vendored here.
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86); // interrupted observation, never a successful fixture exit
}

namespace {

void fail(const char* reason) {
    std::printf("P2_CHALLENGE_STAGE_EXT_REFUSED reason=%s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

int guardSelfTest() {
    struct Row { bool orima; bool dead; float hp; bool expectDown; };
    const Row rows[] = {
        {false, false, 100.0f, false},
        {false, false, 1.5f, false},
        {false, false, 1.0f, true},
        {false, false, 0.0f, true},
        {false, true, 100.0f, true},
        {true, false, 100.0f, true},
        {true, true, 0.0f, true},
    };
    for (size_t i = 0; i < sizeof(rows) / sizeof(rows[0]); ++i) {
        const bool down = p2_fixture_captain_down(rows[i].orima, rows[i].dead, rows[i].hp);
        if (down != rows[i].expectDown) {
            std::printf("FAIL CHALLENGE_STAGE_TABLE_EXT selftest row=%d\n", int(i));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_CHALLENGE_STAGE_EXT_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

int rosterTotal(const int roster[7][3]) {
    int total = 0;
    for (int c = 0; c < 7; ++c)
        for (int h = 0; h < 3; ++h) total += roster[c][h];
    return total;
}

// Pinned expectations (#550 LeafChappy, #537 02tile). Any deviation is a
// refusal, never a default.
struct Expect {
    const char* caveId;
    const char* cavePath;
    const char* sha;
    int uiIndex;
    int tableOrder;
    int floors;
    float sec0;
    float sec1;
    int roster[7][3];
    int bitter;
    int spicy;
    float legacy;
    int treasure;
};

bool checkRow(const P2ChallengeStageExtRow* row, const Expect& e) {
    if (!row) return false;
    if (std::strcmp(row->caveId, e.caveId) || std::strcmp(row->cavePath, e.cavePath)
        || std::strcmp(row->sourceSha256, e.sha)) return false;
    if (row->uiIndex != e.uiIndex || row->tableOrder != e.tableOrder || row->floors != e.floors)
        return false;
    if (row->floorSeconds[0] != e.sec0 || row->floorSeconds[1] != e.sec1) return false;
    if (row->bitterSprays != e.bitter || row->spicySprays != e.spicy) return false;
    if (row->legacyTime != e.legacy || row->treasureCountField != e.treasure) return false;
    for (int c = 0; c < 7; ++c)
        for (int h = 0; h < 3; ++h)
            if (row->roster[c][h] != e.roster[c][h]) return false;
    return true;
}

class ChallengeStageTableExtApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL CHALLENGE_STAGE_TABLE_EXT timeout observed=%d\n", observed);
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) return result;
        Navi* n = naviMgr->getNavi();
        if (!n) return result;
        // Guard FIRST: immediately after engine idle, before readiness/PASS.
        p2_fixture_require_captain(GameStat::orimaDead, !n->isAlive(), n->mHealth, observed);
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++observed;
        // Readiness here means the engine runs this binary live in the room:
        // pc_p2_preview_ready() additionally requires a preview treasure,
        // which a pure table proof does not stage, so this fixture counts
        // guarded live ticks with a live squad instead (600 ticks ~= 20 s).
        if (observed == 600) {
            int red = 0, blue = 0;
            if (pikiMgr) {
                Iterator it(pikiMgr);
                CI_LOOP(it) {
                    Piki* piki = static_cast<Piki*>(*it);
                    if (piki && piki->isAlive()) {
                        if (piki->mColor == Red) ++red;
                        else if (piki->mColor == Blue) ++blue;
                    }
                }
            }
            std::printf("P2_CHALLENGE_STAGE_EXT_READY observed=%d red=%d blue=%d\n",
                        observed, red, blue);
            std::fflush(stdout);
            if (red + blue < 1) {
                std::printf("P2_CHALLENGE_STAGE_EXT_REFUSED reason=no-live-squad\n");
                std::fflush(stdout);
                std::_Exit(1);
            }
            std::printf("P2_CHALLENGE_STAGE_EXT_GATES all=UNTESTED content_wired=0\n");
            std::fflush(stdout);
            std::puts("PASS CHALLENGE_STAGE_TABLE_EXT");
            std::fflush(stdout);
            std::_Exit(0);
        }
        if (observed % 600 == 0) {
            std::printf("P2_CHALLENGE_STAGE_EXT_WAIT observed=%d\n", observed);
            std::fflush(stdout);
        }
        return result;
    }
};

} // namespace

int main(int argc, char** argv) {
    const char* want = nullptr;
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL CHALLENGE_STAGE_TABLE_EXT negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
        if (!std::strcmp(argv[i], "--ext-stage") && i + 1 < argc) want = argv[++i];
    }
    if (!want) fail("missing---ext-stage");
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) fail("requires --experimental-pikmin2-room");

    static const Expect kExpects[] = {
        { "ch_ABEM_LeafChappy",
          "user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt",
          "49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf",
          17, 4, 2, 85.0f, 100.0f,
          { {10,0,0}, {10,0,0}, {10,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },
          1, 1, 400.0f, 11 },
        { "ch_NARI_02tile",
          "user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt",
          "d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6",
          4, 19, 2, 200.0f, 150.0f,
          { {0,0,50}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },
          0, 5, 0.0f, 0 },
    };
    if (pc_p2_challenge_stages_ext_count() != 2) fail("ext-count");
    const P2ChallengeStageExtRow* row = pc_p2_challenge_stages_ext_lookup(want);
    if (!row) fail("unknown-stage");
    const Expect* expect = nullptr;
    for (size_t i = 0; i < sizeof(kExpects) / sizeof(kExpects[0]); ++i)
        if (!std::strcmp(kExpects[i].caveId, want)) expect = &kExpects[i];
    if (!expect || !checkRow(row, *expect)) fail("pin-mismatch");
    std::printf("P2_CHALLENGE_STAGE_EXT_RESOLVED cave=%s ui_index=%d table_order=%d floors=%d "
                "roster_total=%d timers=%.1f,%.1f sprays=%d,%d legacy=%.1f treasure=%d sha=%.8s\n",
                row->caveId, row->uiIndex, row->tableOrder, row->floors,
                rosterTotal(row->roster), row->floorSeconds[0], row->floorSeconds[1],
                row->bitterSprays, row->spicySprays, row->legacyTime,
                row->treasureCountField, row->sourceSha256);
    std::fflush(stdout);
    // kusachi must resolve ONLY through the untouched engine table, and the
    // extension must never shadow it.
    {
        const P2ChallengeStageRowEngine* kusachi =
            pc_p2_challenge_stage_lookup("ch_NARI_01kusachi");
        if (!kusachi || std::strcmp(kusachi->caveId, "ch_NARI_01kusachi")
            || kusachi->uiIndex != 3) fail("engine-kusachi-changed");
        if (pc_p2_challenge_stages_ext_lookup("ch_NARI_01kusachi")) fail("ext-shadows-kusachi");
        std::printf("P2_CHALLENGE_STAGE_EXT_ENGINE_UNTOUCHED cave=ch_NARI_01kusachi ui_index=3\n");
        std::fflush(stdout);
    }
    // The wired engine lookup must now resolve both new keys through the
    // extension fallthrough with the pinned identity (this is the serialized
    // #730 integration proof), while unknown keys stay refused everywhere.
    for (size_t i = 0; i < sizeof(kExpects) / sizeof(kExpects[0]); ++i) {
        const P2ChallengeStageRowEngine* wired =
            pc_p2_challenge_stage_lookup(kExpects[i].caveId);
        if (!wired || std::strcmp(wired->caveId, kExpects[i].caveId)
            || wired->uiIndex != kExpects[i].uiIndex) fail("engine-fallthrough");
        std::printf("P2_CHALLENGE_STAGE_EXT_FALLTHROUGH cave=%s ui_index=%d\n",
                    wired->caveId, wired->uiIndex);
        std::fflush(stdout);
    }
    if (pc_p2_challenge_stage_lookup("ch_NARI_99bogus")) fail("engine-accepts-bogus");
    if (pc_p2_challenge_stages_ext_lookup("ch_NARI_99bogus")) fail("ext-accepts-bogus");
    if (pc_p2_challenge_stage_lookup(nullptr)) fail("engine-null-accepted");
    if (pc_p2_challenge_stages_ext_lookup(nullptr)) fail("ext-null-accepted");
    if (!pc_window_init("P2 Challenge stage table ext fixture", 960, 540)) fail("window");
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0;
        SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        // Attribute the window against EVERY display, not just the one
        // SDL_GetWindowDisplayIndex reports: on multi-display or scaled
        // setups the reported index can disagree with where pc_window_center
        // placed the window, while the window itself is exactly centered.
        // Passing requires 960x540 and centered on at least one display.
        const int displays = SDL_GetNumVideoDisplays();
        bool centered = false;
        SDL_Rect usedBounds{0, 0, 0, 0};
        for (int d = 0; d < displays; ++d) {
            SDL_Rect bounds{0, 0, 0, 0};
            if (SDL_GetDisplayBounds(d, &bounds) != 0) continue;
            const bool onThis = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
                && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
            std::printf("P2_CHALLENGE_STAGE_EXT_DISPLAY index=%d origin=%d,%d size=%dx%d\n",
                        d, bounds.x, bounds.y, bounds.w, bounds.h);
            if (onThis && !centered) {
                centered = true;
                usedBounds = bounds;
            }
        }
        std::fflush(stdout);
        std::printf("P2_CHALLENGE_STAGE_EXT_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, usedBounds.w, usedBounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new ChallengeStageTableExtApp());
    return 0;
}
