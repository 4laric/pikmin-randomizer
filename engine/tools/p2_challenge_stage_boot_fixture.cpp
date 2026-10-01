// Guarded P2 challenge-stage selection boot fixture (lane
// challenge-stage-boot-native-hook, #675).
//
// Replacement-main convention: mirrors tools/p2_cave_guarded_boot_fixture.cpp
// (#642) -- scenario main instead of pc_main.cpp, 960x540 centred window, and
// the --experimental-pikmin2-room boot. The lane build script links this TU
// against the private pikmin_pc graph without editing shared build files.
//
// What this proves (and only this): the engine parses the new
// --experimental-challenge-stage <cave_id> flag (engine/pc_port/pc_bbft.cpp),
// the run directory carries the #669 P2_CHALLENGE_STAGE_SELECT_1 record, and
// the engine's decoded P2 stage table resolves that key to the canonical
// pins. Flag, record and table must agree field by field or the fixture
// refuses. Stage records are accepted only from a pinned allowlist
// (ch_NARI_01kusachi, and ch_NARI_02tile per #537/#711); a record whose engine
// table row is not yet serialized (#710 follow-on) resolves at the record
// level and exits BLOCKED before boot instead of PASS. It boots the real engine privately under the
// room-preview path with a guarded captain.
//
// It does NOT prove P2 challenge content wiring: the engine still selects the
// P1 room-preview stage, so all six gameplay gates stay UNTESTED and the
// P2_CHALLENGE_STAGE_GATES marker says so. Content wiring is the downstream
// consumer's job (#533). No PASS is emitted without observed evidence.
//
// Markers: P2_CHALLENGE_STAGE_FLAG (engine parse), _SIDECAR / _TABLE /
// _RESOLVED (selection chain), _WINDOW (boot environment), _READY (engine
// up), _GATES all=UNTESTED, then "PASS CHALLENGE_STAGE_BOOT" and exit 0.
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

// Mirrors the engine table row in pc_port/pc_bbft.cpp. pc_bbft.h is not owned
// by this lane, so the struct shape is repeated here; the authoritative data
// lives in the engine TU and is reached only through the extern lookups below.
struct P2ChallengeStageRow {
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
extern const char* pc_p2_challenge_stage();
extern const P2ChallengeStageRow* pc_p2_challenge_stage_lookup(const char* caveId);
extern const P2ChallengeStageRow* pc_p2_challenge_stage_selected();

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
    std::printf("P2_CHALLENGE_STAGE_REFUSED reason=%s\n", reason);
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
            std::printf("FAIL CHALLENGE_STAGE_BOOT selftest row=%d orima=%d dead=%d hp=%.3f\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp);
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_CHALLENGE_STAGE_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

// Pinned #669 stage records this fixture accepts (cave_id, source path,
// source sha256). The engine table row is authoritative when it exists; where
// it is not yet serialized (ch_NARI_02tile, follow-on after #710 releases
// pc_bbft.cpp) the record is still resolved from these pinned #537 pins and
// the run stops BLOCKED before boot. Every other record stays refused.
struct P2PinnedSource {
    const char* caveId;
    const char* path;
    const char* sha256;
};
static const P2PinnedSource kP2PinnedSources[] = {
    { "ch_NARI_01kusachi",
      "user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt",
      "b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85" },
    { "ch_NARI_02tile",
      "user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt",
      "d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6" },
};
bool pinnedSource(const std::string& cave, const std::string& path, const std::string& sha) {
    for (size_t i = 0; i < sizeof(kP2PinnedSources) / sizeof(kP2PinnedSources[0]); ++i)
        if (cave == kP2PinnedSources[i].caveId && path == kP2PinnedSources[i].path
            && sha == kP2PinnedSources[i].sha256) return true;
    return false;
}

// Parses the canonical #669 P2_CHALLENGE_STAGE_SELECT_1 record emitted by
// render_boot_request(). Strict shape: any deviation is a refusal, never a
// default.
bool readRecord(const char* path, Record& out) {
    std::ifstream in(path);
    if (!in) return false;
    std::string magic;
    if (!std::getline(in, magic) || magic != "P2_CHALLENGE_STAGE_SELECT_1") return false;
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
        if (!pinnedSource(out.cave, out.sourcePath, out.sourceSha)) return false;
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

bool matches(const Record& r, const P2ChallengeStageRow* row) {
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

class ChallengeStageBootApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL CHALLENGE_STAGE_BOOT timeout observed=%d\n", observed);
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
        if (pc_p2_preview_ready()) {
            std::printf("P2_CHALLENGE_STAGE_READY observed=%d\n", observed);
            std::fflush(stdout);
            std::printf("P2_CHALLENGE_STAGE_GATES all=UNTESTED content_wired=0\n");
            std::fflush(stdout);
            std::puts("PASS CHALLENGE_STAGE_BOOT");
            std::fflush(stdout);
            std::_Exit(0);
        }
        if (observed % 600 == 0) {
            std::printf("P2_CHALLENGE_STAGE_WAIT observed=%d\n", observed);
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
            std::printf("FAIL CHALLENGE_STAGE_BOOT negative test did not trip\n");
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
    std::printf("P2_CHALLENGE_STAGE_ARGV cave=%s\n", flagStage);
    std::fflush(stdout);
    Record record;
    if (!readRecord("p2-challenge-stage-select.txt", record)) fail("bad-record");
    std::printf("P2_CHALLENGE_STAGE_SIDECAR cave=%s ui_index=%d\n", record.cave.c_str(), record.uiIndex);
    std::fflush(stdout);
    if (record.cave != flagStage) fail("flag-record-mismatch");
    const P2ChallengeStageRow* row = pc_p2_challenge_stage_lookup(record.cave.c_str());
    if (!row) {
        // The record is accepted from the pinned #537 pins, but the engine
        // table row is a specified follow-on (blocked on #710 releasing
        // pc_bbft.cpp). Resolve the record honestly and stop BLOCKED before
        // boot: never READY and never PASS. Exit 3 is distinct from the
        // guard's 86 and the refusals' 1.
        std::printf("P2_CHALLENGE_STAGE_RESOLVED cave=%s ui_index=%d floors=%d roster_total=%d engine_row=pending\n",
                    record.cave.c_str(), record.uiIndex, record.floors, rosterTotal(record.roster));
        std::fflush(stdout);
        std::printf("P2_CHALLENGE_STAGE_ENGINE_ROW_PENDING cave=%s follow_on=710 source_sha=%s\n",
                    record.cave.c_str(), record.sourceSha.c_str());
        std::fflush(stdout);
        std::printf("P2_CHALLENGE_STAGE_GATES all=UNTESTED content_wired=0\n");
        std::fflush(stdout);
        std::printf("P2_CHALLENGE_STAGE_BLOCKED reason=engine-table-row-pending follow_on=710\n");
        std::fflush(stdout);
        std::_Exit(3); // accepted record; boot awaits the engine table row
    }
    const P2ChallengeStageRow* selected = pc_p2_challenge_stage_selected();
    if (selected != row) fail("selected-table-mismatch");
    std::printf("P2_CHALLENGE_STAGE_TABLE cave=%s ui_index=%d floors=%d\n",
                row->caveId, row->uiIndex, row->floors);
    std::fflush(stdout);
    if (!matches(record, row)) fail("pin-mismatch");
    std::printf("P2_CHALLENGE_STAGE_RESOLVED cave=%s ui_index=%d floors=%d roster_total=%d\n",
                row->caveId, row->uiIndex, row->floors, rosterTotal(row->roster));
    std::fflush(stdout);
    if (!pc_window_init("P2 Challenge stage boot fixture", 960, 540)) fail("window");
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
        std::printf("P2_CHALLENGE_STAGE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new ChallengeStageBootApp());
    return 0;
}
