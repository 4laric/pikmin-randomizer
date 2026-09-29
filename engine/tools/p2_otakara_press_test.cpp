// p2_otakara_press_test (#884): a registered Dweevil (59-62, 93) must not take the P1
// TEKI_Chappy host squash. Runtime evidence (#884 bot probes, FireOtakara 59):
//   P2_OTAKARA_HIT ... health=105.0->-45.0 delta=150.0 interaction=unknown attacker=none
// The only unclamped Nakata-side subtraction is TaiLifeDamageAction::start
// (taireactionactions.cpp:41-44; BTeki::makeDamaged clamps at 0, TaiLifeZeroAction
// sets 0), reached from a PIKISTATE_Flying Piki Entity contact through
// TaiChappySmashedAction -> CHAPPYSTATE_Unk13 (taichappy.cpp:335,357-369,626-633).
// The InteractPress path (TaiPressedAction -> CHAPPYSTATE_Unk2, TaiLifeZeroAction)
// is the second host squash. P2 OtakaraBase has no pressCallBack/flyCollisionCallBack
// override, so both resolve to "no damage, the Pikmin latches"
// (pc_p2_otakara_press_policy.h cites the source).
//
// Engine-free parts exercise pc_p2_otakara_press_policy.h against a small model of
// the two host reactions. The wiring part reads the engine sources as text and
// checks InteractPress::actTeki calls pc_p2_otakara_pressed before eventPerformed
// and TaiSmashedAction::actByEvent calls pc_p2_otakara_smashed before its
// `return true` transit, both under PIKI_PC_PORT.
//
// Negative controls:
//   * -DP2_OTAKARA_PRESS_TEST_USE_LEGACY swaps in legacyDecide (the pre-fix
//     behaviour: nothing intercepts, the host squash runs), making the test fail.
//   * Passing a source root as argv[1] that holds the pre-fix tekiinteraction.cpp /
//     taireactionactions.cpp / pc_p2_otakara.h makes the wiring checks fail.
//
// NOTE: checks use an always-evaluated CHECK macro, never bare assert().
#include "pc_p2_otakara_press_policy.h"

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#ifndef P2_OTAKARA_PRESS_SOURCE_ROOT
#define P2_OTAKARA_PRESS_SOURCE_ROOT "."
#endif

using namespace p2otakarapress;

static int failures = 0;

#define CHECK(cond)                                                                        \
    do {                                                                                   \
        if (!(cond)) {                                                                     \
            std::printf("P2_OTAKARA_PRESS_TEST_FAIL line=%d check=%s\n", __LINE__, #cond); \
            ++failures;                                                                    \
        }                                                                                  \
    } while (0)

namespace {

// Pre-fix behaviour: InteractPress::actTeki had no Dweevil hook and
// TaiSmashedAction::actByEvent always transited, so nothing was consumed.
Decision legacyDecide(bool, Path) { return Decision{}; }

#ifdef P2_OTAKARA_PRESS_TEST_USE_LEGACY
Decision underTest(bool registered, Path path) { return legacyDecide(registered, path); }
#else
Decision underTest(bool registered, Path path) { return decide(registered, path); }
#endif

// Model of the P1 TEKI_Chappy host reactions a consumed=false press falls into.
struct Host {
    float health;
    bool alive = true;
    int state = 15; // CHAPPYSTATE_Unk15 wait/idle
};
constexpr float kSmashDamage = 150.0f; // CHAPPYPF_SmashDamage observed at runtime (delta=150.0)

// Returns the health drop the Dweevil module would log as P2_OTAKARA_HIT.
float applyContact(Host& h, bool registered, Path path, bool& consumed) {
    const float before = h.health;
    const Decision d = underTest(registered, path);
    consumed = d.consume;
    if (d.consume) {
        h.health -= d.damage;
    } else if (path == Path::ThrownLanding) {
        h.state = 13;                // CHAPPYSTATE_Unk13
        h.health -= kSmashDamage;    // TaiLifeDamageAction::start, no clamp
        if (h.health <= 0.0f) h.state = 1; // TaiDeadAction -> CHAPPYSTATE_Unk1
    } else {
        h.state = 2;                 // CHAPPYSTATE_Unk2
        h.health = 0.0f;             // TaiLifeZeroAction::start
        h.alive = false;             // TaiBeingPressedAction::start clears ALIVE
    }
    if (h.health <= 0.0f) h.alive = false;
    return before - h.health;
}

std::string readFile(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return std::string();
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

// Body of the first function whose signature starts with `signature`, up to the
// first line that is exactly "}" (engine style: the closing brace at column 0).
std::string functionBody(const std::string& text, const std::string& signature) {
    const size_t at = text.find(signature);
    if (at == std::string::npos) return std::string();
    size_t end = text.find("\n}", at);
    if (end == std::string::npos) end = text.size();
    return text.substr(at, end - at);
}

void checkWiring(const std::string& root) {
    const std::string inter = readFile(root + "/src/plugPikiNakata/tekiinteraction.cpp");
    const std::string react = readFile(root + "/src/plugPikiNakata/taireactionactions.cpp");
    const std::string header = readFile(root + "/pc_port/pc_p2_otakara.h");
    CHECK(!inter.empty());
    CHECK(!react.empty());
    CHECK(!header.empty());

    CHECK(header.find("bool pc_p2_otakara_pressed(BTeki*") != std::string::npos);
    CHECK(header.find("bool pc_p2_otakara_smashed(BTeki*") != std::string::npos);
    CHECK(inter.find("#include \"pc_p2_otakara.h\"") != std::string::npos);
    CHECK(react.find("#include \"pc_p2_otakara.h\"") != std::string::npos);

    // InteractPress::actTeki: hook inside the PIKI_PC_PORT block, before the host
    // Pressed event, and consuming (return true).
    const std::string press = functionBody(inter, "bool InteractPress::actTeki(");
    CHECK(!press.empty());
    const size_t pcIf = press.find("#if defined(PIKI_PC_PORT) && PIKI_PC_PORT");
    const size_t hook = press.find("if (pc_p2_otakara_pressed(teki, mOwner))");
    const size_t pcEnd = press.find("#endif", pcIf == std::string::npos ? 0 : pcIf);
    const size_t event = press.find("eventPerformed(");
    CHECK(pcIf != std::string::npos);
    CHECK(hook != std::string::npos);
    CHECK(event != std::string::npos);
    CHECK(hook != std::string::npos && pcIf != std::string::npos && pcIf < hook);
    CHECK(hook != std::string::npos && pcEnd != std::string::npos && hook < pcEnd);
    CHECK(hook != std::string::npos && event != std::string::npos && hook < event);
    if (hook != std::string::npos) {
        const size_t ret = press.find("return true;", hook);
        CHECK(ret != std::string::npos && ret < pcEnd);
    }

    // TaiSmashedAction::actByEvent: the flying-Piki branch asks the hook before its
    // `return true` (the transit to the host smash state) and returns false.
    const std::string smash = functionBody(react, "bool TaiSmashedAction::actByEvent(");
    CHECK(!smash.empty());
    const size_t flying = smash.find("PIKISTATE_Flying");
    const size_t sHook = smash.find("if (pc_p2_otakara_smashed(teki, other))");
    const size_t sIf = smash.find("#if defined(PIKI_PC_PORT) && PIKI_PC_PORT");
    CHECK(flying != std::string::npos);
    CHECK(sHook != std::string::npos);
    CHECK(sHook != std::string::npos && flying != std::string::npos && flying < sHook);
    CHECK(sHook != std::string::npos && sIf != std::string::npos && sIf < sHook);
    if (sHook != std::string::npos) {
        const size_t retFalse = smash.find("return false;", sHook);
        const size_t retTrue = smash.find("return true;", sHook);
        CHECK(retFalse != std::string::npos && retTrue != std::string::npos && retFalse < retTrue);
    }
}

} // namespace

int main(int argc, char** argv) {
    // 1. Policy: registered Dweevils consume both host squash paths with the source
    //    pressCallBack=false outcome; unregistered actors keep the host reaction.
    for (Path path : {Path::HostPress, Path::ThrownLanding}) {
        const Decision reg = underTest(true, path);
        CHECK(reg.consume);
        CHECK(reg.damage == 0.0f);
        CHECK(!reg.countsAsHit);
        CHECK(!reg.detonatesBomb); // BombOtakara has no pressCallBack either
        CHECK(std::string(reg.outcome) == "ignored_source_press");
        const Decision unreg = underTest(false, path);
        CHECK(!unreg.consume);
    }
    // The negative control itself never consumes (pre-fix host squash).
    CHECK(!legacyDecide(true, Path::ThrownLanding).consume);
    CHECK(!legacyDecide(true, Path::HostPress).consume);
    CHECK(std::string(pathName(Path::HostPress)) == "InteractPress");
    CHECK(std::string(pathName(Path::ThrownLanding)) == "ThrownLanding");

    // 2. The #884 runtime case: FireOtakara at 105/150 after hits, then a thrown
    //    Pikmin lands on it. Pre-fix: -150 lump to -45, dead. Fixed: untouched.
    {
        Host h{105.0f};
        bool consumed = false;
        const float drop = applyContact(h, true, Path::ThrownLanding, consumed);
        CHECK(consumed);
        CHECK(drop == 0.0f);
        CHECK(h.health == 105.0f);
        CHECK(h.alive);
        CHECK(h.state == 15);
    }
    {
        // Base run: 95 -> -55 (delta 150) must not happen either.
        Host h{95.0f};
        bool consumed = false;
        const float drop = applyContact(h, true, Path::ThrownLanding, consumed);
        CHECK(drop == 0.0f);
        CHECK(h.alive);
    }
    {
        // Host InteractPress (e.g. an Iwagon boulder TaiBangingAction or a
        // DangoMushi rock Press strike) must not zero it either.
        Host h{150.0f};
        bool consumed = false;
        const float drop = applyContact(h, true, Path::HostPress, consumed);
        CHECK(consumed);
        CHECK(drop == 0.0f);
        CHECK(h.alive);
        CHECK(h.state == 15);
    }
    {
        // Unregistered Dwarf Bulborb keeps the P1 squash (behaviour-neutral).
        Host h{105.0f};
        bool consumed = true;
        const float drop = applyContact(h, false, Path::ThrownLanding, consumed);
        CHECK(!consumed);
        CHECK(drop == kSmashDamage);
        CHECK(!h.alive);
    }

    // 3. Once-per-press log gate.
    int a = 0, b = 0;
    CHECK(shouldLog(nullptr, 1.0e6f, &a));
    CHECK(!shouldLog(&a, 0.0f, &a));
    CHECK(!shouldLog(&a, LOG_WINDOW * 0.5f, &a));
    CHECK(shouldLog(&a, LOG_WINDOW, &a));
    CHECK(shouldLog(&a, 0.0f, &b));

    // 4. Source wiring.
    const std::string root = argc > 1 ? std::string(argv[1]) : std::string(P2_OTAKARA_PRESS_SOURCE_ROOT);
    checkWiring(root);

    if (failures) {
        std::printf("P2_OTAKARA_PRESS_TEST_RESULT pass=0 failures=%d root=%s\n", failures, root.c_str());
        return 1;
    }
    std::printf("P2_OTAKARA_PRESS_TEST_RESULT pass=1 root=%s\n", root.c_str());
    return 0;
}
