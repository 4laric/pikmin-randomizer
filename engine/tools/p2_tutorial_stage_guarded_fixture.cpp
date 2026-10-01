// Guarded P2 tutorial-stage boot fixture (lane tutorial-stage-table-row-native,
// #754, consumer #534).
//
// Replacement-main convention: mirrors tools/p2_challenge_stage_boot_fixture.cpp
// (#675) -- scenario main instead of pc_main.cpp, 960x540 centred window, and
// the --experimental-pikmin2-room boot. The lane build script links this TU
// against the private pikmin_pc graph without editing shared build files.
// The pinned tutorial row TU is compiled in verbatim below (same technique as
// the #701 content fixture); no engine table is modified.
//
// What this proves (and only this): the engine parses the
// --experimental-challenge-stage ch_ABEM_tutorial flag, the run directory
// carries the P2_TUTORIAL_STAGE_SELECT_1 record, the engine's own decoded P2
// stage table does NOT resolve the key (serialized boundary: selected is
// null until the #186-reviewed integration lands), and the lane-owned pinned
// tutorial row DOES resolve it with field-by-field agreement. Flag, record
// and row must agree or the fixture refuses. It boots the real engine
// privately under the room-preview path with a guarded captain.
//
// It does NOT prove P2 tutorial content wiring: the engine still selects the
// P1 room-preview stage, so all six gameplay gates stay UNTESTED and the
// P2_TUTORIAL_STAGE_GATES marker says so. Content wiring is the downstream
// consumer's job (#534). No PASS is emitted without observed evidence.
// Unguarded runs are refused: the #632 guard is unconditional below (no flag
// disables it) and a missing room-preview flag or record refuses before boot.
//
// Markers: P2_TUTORIAL_STAGE_FLAG (engine parse), _SIDECAR / _TABLE /
// _RESOLVED (selection chain), _WINDOW (boot environment), _READY (engine
// up), _GATES all=UNTESTED, then "PASS TUTORIAL_STAGE_BOOT" and exit 0.
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
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

// Pinned tutorial row TU, compiled into this fixture (same technique as the
// #701 content fixture). The lane-owned lookup resolves ch_ABEM_tutorial;
// the engine table is never touched.
#include "../pc_port/pc_p2_challenge_tutorial_stage.h"
#include "../pc_port/pc_p2_challenge_tutorial_stage.cpp"

// Captain-safety guard (#632), vendored verbatim from
// scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474).
// Observation-only; the canonical header is consumed read-only at review. A
// replacement-main TU cannot include a Python-tree script header at native
// build time, so the exact guard body is vendored here. The guard is
// unconditional: there is no unguarded mode to refuse separately.
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

// Engine stage-flag accessor (defined in pc_port/pc_bbft.cpp; pc_bbft.h is
// not owned by this lane). The engine table lookup below is mirrored
// read-only to prove the serialization boundary (engine selected stays null
// for the tutorial key until integration); authoritative resolution always
// uses p2tutorialstage::tutorialLookup.
extern const char* pc_p2_challenge_stage();
struct P2EngineStageRow {
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
extern const P2EngineStageRow* pc_p2_challenge_stage_lookup(const char* caveId);
extern const P2EngineStageRow* pc_p2_challenge_stage_selected();

namespace {

struct Record {
    std::string cave;
    int uiIndex = -1;
    int tableOrder = -1;
    int floors = 0;
    std::string sourcePath;
    std::string sourceSha;
    float floorSeconds[8] = {0};
    float legacy = 0;
    int roster[7][3] = {{0}};
    int bitter = -1;
    int spicy = -1;
    int treasureField = -1;
};

void fail(const char* reason) {
    std::printf("P2_TUTORIAL_STAGE_REFUSED reason=%s\n", reason);
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
            std::printf("FAIL TUTORIAL_STAGE_BOOT selftest row=%d orima=%d dead=%d hp=%.3f\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp);
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_TUTORIAL_STAGE_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

// Parses the lane-owned P2_TUTORIAL_STAGE_SELECT_1 record staged by
// scripts/build_p2_tutorial_stage_table.py (field layout mirrors the #669
// selector record). Strict shape: any deviation is a refusal, never a
// default.
bool readRecord(const char* path, Record& out) {
    std::ifstream in(path);
    if (!in) return false;
    std::string magic;
    if (!std::getline(in, magic) || magic != "P2_TUTORIAL_STAGE_SELECT_1") return false;
    std::string line, word;
    {
        std::getline(in, line);
        std::istringstream s(line);
        int floors = 0;
        if (!(s >> word) || word != "cave" || !(s >> out.cave)) return false;
        if (!(s >> word) || word != "ui_index" || !(s >> out.uiIndex)) return false;
        if (!(s >> word) || word != "table_order" || !(s >> out.tableOrder)) return false;
        if (!(s >> word) || word != "floors" || !(s >> floors)) return false;
        out.floors = floors;
        if (out.uiIndex < 0 || out.tableOrder < 0 || out.floors < 1 || out.floors > 8) return false;
    }
    {
        std::getline(in, line);
        std::istringstream s(line);
        if (!(s >> word) || word != "source" || !(s >> out.sourcePath) || !(s >> out.sourceSha)) return false;
        if (out.sourcePath != "user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt") return false;
    }
    {
        std::getline(in, line);
        std::istringstream s(line);
        if (!(s >> word) || word != "timers") return false;
        for (int i = 0; i < out.floors; ++i) if (!(s >> out.floorSeconds[i])) return false;
        if (!(s >> word) || word != "legacy" || !(s >> out.legacy)) return false;
        if (out.floorSeconds[0] <= 0.0f) return false;
    }
    {
        std::getline(in, line);
        std::istringstream s(line);
        if (!(s >> word) || word != "sprays") return false;
        if (!(s >> word) || word != "bitter" || !(s >> out.bitter)) return false;
        if (!(s >> word) || word != "spicy" || !(s >> out.spicy)) return false;
        if (!(s >> word) || word != "treasure_field" || !(s >> out.treasureField)) return false;
    }
    for (int i = 0; i < 7; ++i) {
        if (!std::getline(in, line)) return false;
        std::istringstream s(line);
        if (!(s >> word) || word != "roster") return false;
        if (!(s >> out.roster[i][0] >> out.roster[i][1] >> out.roster[i][2])) return false;
    }
    std::getline(in, line); // trailing newline only
    return line.empty();
}

int rosterTotal(const int roster[7][3]) {
    int total = 0;
    for (int c = 0; c < 7; ++c)
        for (int h = 0; h < 3; ++h) total += roster[c][h];
    return total;
}

bool matches(const Record& r, const p2tutorialstage::TutorialStageRow* row) {
    if (r.cave != row->caveId) return false;
    if (r.uiIndex != row->uiIndex || r.tableOrder != row->tableOrder) return false;
    if (r.floors != row->floors) return false;
    for (int i = 0; i < r.floors; ++i)
        if (r.floorSeconds[i] != row->floorSeconds[i]) return false;
    if (r.legacy != row->legacyTime) return false;
    if (r.bitter != row->bitterSprays || r.spicy != row->spicySprays) return false;
    if (r.treasureField != row->treasureCountField) return false;
    if (r.sourceSha != row->sourceSha256) return false;
    if (rosterTotal(r.roster) != rosterTotal(row->roster)) return false;
    for (int c = 0; c < 7; ++c)
        for (int h = 0; h < 3; ++h)
            if (r.roster[c][h] != row->roster[c][h]) return false;
    return true;
}

class TutorialStageBootApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL TUTORIAL_STAGE_BOOT timeout observed=%d\n", observed);
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) return result;
        Navi* n = naviMgr->getNavi();
        if (!n) return result;
        // Guard FIRST: immediately after engine idle, before readiness/PASS.
        // Unconditional: this fixture has no unguarded mode.
        p2_fixture_require_captain(GameStat::orimaDead, !n->isAlive(), n->mHealth, observed);
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++observed;
        if (pc_p2_preview_ready()) {
            std::printf("P2_TUTORIAL_STAGE_READY observed=%d\n", observed);
            std::fflush(stdout);
            std::printf("P2_TUTORIAL_STAGE_GATES all=UNTESTED content_wired=0\n");
            std::fflush(stdout);
            std::puts("PASS TUTORIAL_STAGE_BOOT");
            std::fflush(stdout);
            std::_Exit(0);
        }
        if (observed % 600 == 0) {
            std::printf("P2_TUTORIAL_STAGE_WAIT observed=%d\n", observed);
            std::fflush(stdout);
        }
        return result;
    }
};

} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL TUTORIAL_STAGE_BOOT negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    // The engine parses the flag itself and emits P2_CHALLENGE_STAGE_FLAG.
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) fail("requires --experimental-pikmin2-room");
    const char* flagStage = pc_p2_challenge_stage();
    if (!flagStage) fail("missing-flag");
    std::printf("P2_TUTORIAL_STAGE_ARGV cave=%s\n", flagStage);
    std::fflush(stdout);
    if (std::strcmp(flagStage, "ch_ABEM_tutorial") != 0) fail("flag-not-tutorial");
    Record record;
    if (!readRecord("p2-tutorial-stage-select.txt", record)) fail("bad-record");
    std::printf("P2_TUTORIAL_STAGE_SIDECAR cave=%s ui_index=%d\n", record.cave.c_str(), record.uiIndex);
    std::fflush(stdout);
    if (record.cave != flagStage) fail("flag-record-mismatch");
    // Serialization boundary: the engine table must NOT resolve the tutorial
    // key yet (integration is follow-on). The lane-owned row must resolve it.
    if (pc_p2_challenge_stage_lookup(record.cave.c_str()) != nullptr) fail("engine-table-premature");
    if (pc_p2_challenge_stage_selected() != nullptr) fail("engine-selected-premature");
    std::printf("P2_TUTORIAL_STAGE_ENGINE_TABLE hit=0 (integration follow-on)\n");
    std::fflush(stdout);
    const p2tutorialstage::TutorialStageRow* row =
        p2tutorialstage::tutorialLookup(record.cave.c_str());
    if (!row) fail("unknown-stage");
    if (!p2tutorialstage::tutorialRowMatches(row)) fail("row-self-mismatch");
    std::printf("P2_TUTORIAL_STAGE_TABLE cave=%s ui_index=%d floors=%d\n",
                row->caveId, row->uiIndex, row->floors);
    std::fflush(stdout);
    if (!matches(record, row)) fail("pin-mismatch");
    std::printf("P2_TUTORIAL_STAGE_RESOLVED cave=%s ui_index=%d floors=%d roster_total=%d\n",
                row->caveId, row->uiIndex, row->floors, rosterTotal(row->roster));
    std::fflush(stdout);
    if (!pc_window_init("P2 Tutorial stage boot fixture", 960, 540)) fail("window");
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0;
        SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{0, 0, 0, 0};
        SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_TUTORIAL_STAGE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new TutorialStageBootApp());
    return 0;
}
