#include "pc_bbft.h"
#include "pc_randomizer.h"
#include "pc_p2_challenge_persistence.h"
#include "pc_p2_challenge_runtime.h"
#include "pc_p2_challenge_content.h"
#include "pc_p2_challenge_stages_ext.h"
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <chrono>
#include <string>
#ifdef _WIN32
#include "bbft/bbft_transport.h"
#endif
static bool enabled = false;
static int challengeLevel = -1;
static bool p2RoomPreview = false;
bool pc_pikipelago_room_preview() { return p2RoomPreview; }
int pc_pikipelago_challenge_level() { return challengeLevel; }
static std::string p2ChallengeStage;
const char* pc_p2_challenge_stage() { return p2ChallengeStage.empty() ? nullptr : p2ChallengeStage.c_str(); }
// Decoded P2 challenge stage table (lane challenge-stage-boot-native-hook,
// #675). Keyed by cave_id and transcribed from the canonical plan/inventory
// pins via the #669 selector record. The engine hook records the requested
// key; this table resolves it; the guarded fixture cross-checks flag, table
// and the #669 P2_CHALLENGE_STAGE_SELECT_1 record. P1
// --experimental-challenge-level is a different namespace and stays untouched.
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
static const P2ChallengeStageRow kP2ChallengeStages[] = {
    { "ch_NARI_01kusachi",
      "user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt",
      "b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85",
      3, 3, 1,
      { 180.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f },
      { {0,0,50}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },
      1, 2, 350.0f, 0 },
};
// Challenge stage-table extension fallthrough (#730; #186 decision
// output/workflow/integration-recovery/species-owner/stagetable730-186-decision.md).
// The additive LeafChappy/02tile table (pc_p2_challenge_stages_ext.{h,cpp}) is
// linked only into pikmin_pc, so this reference is weak: pc_bbft_test stays
// link-inert without the module, while every build that carries the TU resolves
// the two additive rows on an engine miss. It coexists with the landed #718
// persistence, #722 runtime and #728 content hooks (all null-by-default).
#if defined(__GNUC__)
const P2ChallengeStageExtRow* pc_p2_challenge_stages_ext_lookup(const char*) __attribute__((weak));
#endif
static_assert(sizeof(P2ChallengeStageRow) == sizeof(P2ChallengeStageExtRow),
              "stage-table extension row layout drifted from the engine row");
const P2ChallengeStageRow* pc_p2_challenge_stage_lookup(const char* caveId) {
    if (caveId == nullptr) return nullptr;
    for (size_t i = 0; i < sizeof(kP2ChallengeStages) / sizeof(kP2ChallengeStages[0]); ++i)
        if (!std::strcmp(kP2ChallengeStages[i].caveId, caveId)) return &kP2ChallengeStages[i];
#if defined(__GNUC__)
    if (pc_p2_challenge_stages_ext_lookup != nullptr) {
        const P2ChallengeStageExtRow* ext = pc_p2_challenge_stages_ext_lookup(caveId);
        return reinterpret_cast<const P2ChallengeStageRow*>(ext);
    }
#endif
    return nullptr;
}
const P2ChallengeStageRow* pc_p2_challenge_stage_selected() {
    return p2ChallengeStage.empty() ? nullptr : pc_p2_challenge_stage_lookup(p2ChallengeStage.c_str());
}
// Challenge runtime bridge glue (ported from #710 db245877, #722). Engine-free:
// plain field copy plus a null-by-default hook pointer, so the small
// pc_bbft_test target (no engine objects) keeps linking and runs inert. The
// engine-dependent bridge registers itself at startup in pikmin_pc.
bool p2_challenge_stage_params(P2ChallengeStageParams& out) {
    const P2ChallengeStageRow* row = pc_p2_challenge_stage_selected();
    if (row == nullptr) return false;
    out.caveId = row->caveId;
    out.uiIndex = row->uiIndex;
    out.floors = row->floors;
    for (int i = 0; i < 8; ++i) out.floorSeconds[i] = row->floorSeconds[i];
    for (int c = 0; c < 7; ++c)
        for (int h = 0; h < 3; ++h) out.roster[c][h] = row->roster[c][h];
    out.bitterSprays = row->bitterSprays;
    out.spicySprays = row->spicySprays;
    return true;
}
static P2ChallengeRuntimeHook sChallengeRuntimeHook = nullptr;
void p2_challenge_runtime_set_hook(P2ChallengeRuntimeHook hook) {
    sChallengeRuntimeHook = hook;
}
// Challenge stage content wiring (#728). Same link-safety contract: plain
// hook pointer, null by default, engine-free here; the engine-dependent
// content module registers itself at startup in pikmin_pc only.
static P2ChallengeContentHook sChallengeContentHook = nullptr;
void p2_challenge_content_set_hook(P2ChallengeContentHook hook) {
    sChallengeContentHook = hook;
}
static bool testBackground = false;
void pc_bbft_milestone(const char* text) {
    if (!enabled) return;
    std::printf("[BBFT] %s\n", text);
#ifdef _WIN32
    bbft_logf("%s", text);
#endif
}
const char* pc_bbft_save_root() {
    if (pc_randomizer_enabled()) return pc_randomizer_save_root();
    if (!enabled && challengeLevel < 0 && p2ChallengeStage.empty()) return "save";
    // A quick-boot run must never reuse a user's named memory-card slot.
    static const std::string session = "save/bbft_sessions/" + std::to_string(
        std::chrono::system_clock::now().time_since_epoch().count());
    return session.c_str();
}
static bool startDown = false, skipRequested = false;
void pc_bbft_start_button(bool down) {
    skipRequested = pc_bbft_accept_input() && down && !startDown;
    startDown = down;
}
bool pc_bbft_take_skip() {
    bool result = skipRequested;
    skipRequested = false;
    return result;
}
void pc_bbft_init(int argc, char** argv) {
    for (int i=1; i<argc; ++i) {
        if (!std::strcmp(argv[i], "--experimental-pikmin2-room")) {
            if (challengeLevel >= 0) { std::fprintf(stderr,"Only one experimental preview may be selected\n"); std::exit(2); }
            p2RoomPreview = true; challengeLevel = 0;
        } else if (!std::strcmp(argv[i], "--experimental-challenge-stage")) {
            if (++i>=argc) { std::fprintf(stderr,"--experimental-challenge-stage needs a stage key\n"); std::exit(2); }
            const char* key = argv[i];
            size_t len = std::strlen(key);
            bool ok = len >= 1 && len <= 64 && ((key[0]>='A'&&key[0]<='Z')||(key[0]>='a'&&key[0]<='z'));
            for (size_t k = 1; ok && k < len; ++k) {
                char c = key[k];
                ok = (c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='_';
            }
            if (!ok) { std::fprintf(stderr,"--experimental-challenge-stage needs a stage key ([A-Za-z][A-Za-z0-9_]{0,63})\n"); std::exit(2); }
            p2ChallengeStage = key;
            std::printf("P2_CHALLENGE_STAGE_FLAG cave=%s\n", key); std::fflush(stdout);
        } else if (!std::strcmp(argv[i], "--experimental-challenge-level")) {
            if (++i>=argc || challengeLevel>=0 || std::strlen(argv[i])!=1 || argv[i][0]<'0' || argv[i][0]>'4') {
                std::fprintf(stderr,"--experimental-challenge-level requires one ID 0-4\n"); std::exit(2);
            }
            challengeLevel=argv[i][0]-'0';
        }
    }
    if (challengeLevel>=0) {
        for(int i=1;i<argc;++i) if(!std::strcmp(argv[i],"--bbft-port")) {
            std::fprintf(stderr,"Challenge layout preview cannot use BBFT sessions\n"); std::exit(2);
        }
        // lane-03 hook: the room preview may carry an ENEMY_P2 seed; feed it a
        // bridge-only bootstrap (no full session, so the preview never holds).
        for(int i=1;i<argc;++i) if(!std::strcmp(argv[i],"--randomizer-seed")) {
            if (i+1 >= argc) { std::fprintf(stderr,"--randomizer-seed needs a file\n"); std::exit(2); }
            pc_randomizer_p2_room_bootstrap(argv[i+1]);
            break;
        }
        return;
    }
    if (pc_randomizer_init(argc, argv)) { enabled = true; return; }
#ifdef _WIN32
    const char* port = std::getenv("BBFT_PORT");
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--bbft-port") == 0) {
            if (++i >= argc) { std::fprintf(stderr, "--bbft-port needs a port\n"); std::exit(2); }
            port = argv[i];
        }
    }
    if (port && *port) {
        char* end = nullptr;
        long value = std::strtol(port, &end, 10);
        if (*end || value < 1 || value > 65535) { std::fprintf(stderr, "Invalid BBFT port\n"); std::exit(2); }
        enabled = true;
        bbft_transport_init("pikmin", nullptr, nullptr);
        const char* test = std::getenv("PIKMIN_BBFT_TEST_BACKGROUND");
        testBackground = test && !std::strcmp(test, "1");
        if (testBackground) pc_bbft_milestone("TEST_BACKGROUND_ENABLED input_still_requires_foreground");
    }
#endif
}
bool pc_bbft_enabled() { return enabled || challengeLevel >= 0; }
bool pc_bbft_skip_tutorial() {
    if (challengeLevel >= 0) return true;
    if (pc_randomizer_enabled()) return true;
#ifdef _WIN32
    return enabled && bbft_pikmin_skip_tutorial();
#else
    return false;
#endif
}

// Challenge persistence call site (#718). The #713 module
// (pc_p2_challenge_persistence.{h,cpp}) is engine-free and not yet in any
// CMake target, so its recorders are referenced WEAKLY here: pc_bbft_test
// stays link-inert without the module, while every build that does compile
// the module (the #718 callsite fixture, and pikmin_pc once the module joins
// its sources under #186) resolves them and emits the 7 probe markers for a
// selected stage.
#if defined(__GNUC__)
namespace p2challengepersist {
bool selectStage(const char*, StageAnchors*) __attribute__((weak));
bool recordSave(StageAnchors*) __attribute__((weak));
bool recordLoad(StageAnchors*) __attribute__((weak));
bool recordClear(StageAnchors*) __attribute__((weak));
bool recordHighscore(StageAnchors*, int, double, int) __attribute__((weak));
bool recordUnlock(StageAnchors*) __attribute__((weak));
bool recordReceipt(StageAnchors*, int) __attribute__((weak));
bool recordReentry(StageAnchors*) __attribute__((weak));
}
#endif

// Overworld save-serializer session call (#736). The module
// (pc_p2_overworld_save.{h,cpp}) joins pikmin_pc sources, so the reference
// below is weak: pc_bbft_test stays link-inert without the module, while
// pikmin_pc resolves it. The poll itself is context-gated (no-op unless a
// fixture set explicit session context), so production runs that never set
// context perform no file I/O.
#if defined(__GNUC__)
void pc_p2_overworld_save_poll(void) __attribute__((weak));
#endif

static void p2OverworldSaveCallSite() {
#if defined(__GNUC__)
    if (pc_p2_overworld_save_poll == nullptr) return;
    pc_p2_overworld_save_poll();
#endif
}

static bool sPersistenceEmitted = false;
static void p2ChallengePersistenceCallSite() {
#if defined(__GNUC__)
    if (sPersistenceEmitted) return;
    if (p2challengepersist::selectStage == nullptr) return; // module not linked
    const char* caveId = pc_p2_challenge_stage();
    if (caveId == nullptr) return;
    p2challengepersist::StageAnchors anchors;
    if (!p2challengepersist::selectStage(caveId, &anchors)) {
        sPersistenceEmitted = true; // refusal already emitted its marker
        return;
    }
    p2challengepersist::recordSave(&anchors);
    p2challengepersist::recordLoad(&anchors);
    p2challengepersist::recordClear(&anchors);
    // Deterministic result-screen sample (mirrors #713: 42 pokos, 120.5 s, 15 squad).
    p2challengepersist::recordHighscore(&anchors, 42, 120.5, 15);
    p2challengepersist::recordUnlock(&anchors);
    p2challengepersist::recordReceipt(&anchors, 1);
    p2challengepersist::recordReentry(&anchors);
    sPersistenceEmitted = true;
#endif
}
void pc_bbft_update() {
    if (pc_randomizer_enabled()) { pc_randomizer_update(); return; }
#ifdef _WIN32
    if (enabled) bbft_transport_update();
#endif
    // Challenge persistence call site (#718): emits the 7 probe markers for a
    // selected challenge stage via the #713 module; inert without it.
    p2ChallengePersistenceCallSite();
    // Overworld save-serializer session call (#736): context-gated save+verify
    // via the overworld save module; inert without the module or context.
    p2OverworldSaveCallSite();
    // Challenge host-mode runtime bridge (#722, ported from #710). Null (inert)
    // unless the pikmin_pc bridge registered at startup; pc_bbft_test never
    // registers.
    if (sChallengeRuntimeHook) sChallengeRuntimeHook();
    // Challenge stage content wiring (#728). Null (inert) unless the pikmin_pc
    // content module registered at startup; pc_bbft_test never registers.
    if (sChallengeContentHook) sChallengeContentHook();
}
bool pc_bbft_hold() {
    if (pc_randomizer_enabled()) {
#ifdef _WIN32
        const char* background = std::getenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND");
        return !pc_randomizer_ready() || (!(background && !std::strcmp(background, "1")) && !bbft_is_foreground());
#else
        return !pc_randomizer_ready();
#endif
    }
#ifdef _WIN32
    return enabled && (!bbft_state_ready() || bbft_warp_held() || (!testBackground && !bbft_is_foreground())
        || (bbft_region_unlocks() && !bbft_has("Pikmin Access")));
#else
    return false;
#endif
}
bool pc_bbft_accept_input() {
#ifdef _WIN32
    return !enabled || (bbft_is_foreground() && !pc_bbft_hold());
#else
    return true;
#endif
}
void pc_bbft_warp() {
    if (pc_randomizer_enabled()) return; // No cross-game switching in standalone mode.
#ifdef _WIN32
    if (enabled && pc_bbft_accept_input()) bbft_warp_out();
#endif
}
bool pc_bbft_forest_access() {
    if (pc_randomizer_enabled()) return pc_randomizer_has("Pikmin: Forest of Hope Access");
#ifdef _WIN32
    return !enabled || pc_bbft_skip_tutorial() || bbft_has("Pikmin: Forest of Hope Access");
#else
    return true;
#endif
}
void pc_bbft_check(const char* name) {
    if (pc_randomizer_enabled()) { pc_randomizer_check(name); return; }
#ifdef _WIN32
    if (enabled) bbft_check(name);
#endif
}
bool pc_bbft_checked(const char* name) {
    if (pc_randomizer_enabled()) return pc_randomizer_checked(name);
#ifdef _WIN32
    return enabled && bbft_checked(name);
#else
    return false;
#endif
}

bool pc_bbft_progression() {
    if (pc_randomizer_enabled()) return true;
#ifdef _WIN32
    return enabled && bbft_pikmin_progression();
#else
    return false;
#endif
}
bool pc_bbft_has(const char* name) {
    if (pc_randomizer_enabled()) return pc_randomizer_has(name);
#ifdef _WIN32
    return !enabled || bbft_has(name);
#else
    return true;
#endif
}
bool pc_bbft_color_access(int color) {
    // Engine colors: blue=0, red=1, yellow=2.
    if (pc_randomizer_enabled()) return (color == 0 && pc_randomizer_has("Blue Onion"))
        || (color == 1 && pc_randomizer_has("Red Onion")) || (color == 2 && pc_randomizer_has("Yellow Onion"));
    return !pc_bbft_progression() || color == 1 ||
        (color == 0 && pc_bbft_has(pc_bbft_shared_capabilities() ? "Zora Tunic" : "Blue Onion")) ||
        (color == 2 && pc_bbft_has("Yellow Onion"));
}

static bool onionSiteKnown[3] = {};
static float onionSiteX[3], onionSiteZ[3];
void pc_bbft_onion_site(int color, float x, float z) {
    if (!pc_bbft_progression() || color < 0 || color > 2) return;
    onionSiteKnown[color] = true; onionSiteX[color] = x; onionSiteZ[color] = z;
}
bool pc_bbft_near_onion_site(int color, float x, float z, float radius) {
    if (color < 0 || color > 2 || !onionSiteKnown[color]) return false;
    const float dx = x-onionSiteX[color], dz = z-onionSiteZ[color];
    return dx*dx+dz*dz <= radius*radius;
}

bool pc_bbft_shared_capabilities() {
    if (pc_randomizer_enabled()) return false;
#ifdef _WIN32
    return enabled && bbft_shared_capabilities();
#else
    return false;
#endif
}
bool pc_bbft_bomb_rocks() {
    return !pc_bbft_shared_capabilities() || (pc_bbft_has("Yellow Onion") && pc_bbft_has("Bomb Bag"));
}
