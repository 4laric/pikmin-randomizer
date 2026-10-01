// Engine-free regression for the P2 -> P1 sound approximation policy
// (pc_port/pc_p2_sfx_policy.h). Sections:
//   TABLE    every covered species maps Damage and Dead; unmapped pairs are kNone
//   IDS      the mirrored P1 ids are the SoundID.h values (spot-checked)
//   GATE     per-actor rate limit (0.3 s damage cry), first play never limited
//   BUDGET   noisy events log a bounded number of markers, others always
//   STRIDE   distance-based footsteps: none while still, one per stride,
//            no burst on a teleport
//   MARKER   the P2_SFX evidence line format
#include "pc_p2_sfx_policy.h"

#include <cstdio>
#include <cstring>

namespace {
int gFailures = 0;
int gSectionFailures = 0;
#define CHECK(cond)                                                         \
    do {                                                                    \
        if (!(cond)) {                                                      \
            ++gFailures;                                                    \
            ++gSectionFailures;                                             \
            std::printf("  FAIL %s:%d %s\n", __FILE__, __LINE__, #cond);    \
        }                                                                   \
    } while (0)

void section(const char* name, void (*fn)()) {
    gSectionFailures = 0;
    fn();
    std::printf("%s %s\n", gSectionFailures ? "FAIL" : "PASS", name);
}

using namespace p2sfx;

void table() {
    const unsigned species[] = {kBreadbug, kGiantBreadbug, kSnitchbug, kDirigibug, kCrawbster, kAntennaBeetle,
                                kTitanDweevil, kGroink, kGroinkArmored, kCannonLarva, kEmpress,
                                kEmperor, kKurage, kOniKurage,
                                kCatfish, kTadpole, kHana, kBombOtakara};
    for (unsigned s : species) {
        CHECK(seFor(s, Event::Damage) != kNone);
        CHECK(seFor(s, Event::Dead) != kNone);
        // Every mapped id is a real P1 id (SoundID.h enemy range < 0xBD).
        for (int e = 0; e < int(Event::Count); ++e) {
            const int se = seFor(s, Event(e));
            CHECK(se == kNone || (se > 0 && se < 0xBD));
        }
    }
    // Signature events land on the intended species only.
    CHECK(seFor(kBreadbug, Event::Step) == kCollecWalk);
    CHECK(seFor(kBreadbug, Event::Pull) == kCollecPull);
    CHECK(seFor(kGiantBreadbug, Event::Pull) == kCollecPull);   // #958: same TEKI_Collec bank
    CHECK(seFor(kGiantBreadbug, Event::Dead) == kCollecDead);
    CHECK(seFor(kSnitchbug, Event::Hover) == kSaraiHover);
    CHECK(seFor(kSnitchbug, Event::Step) == kNone);
    CHECK(seFor(kDirigibug, Event::Burst) == kBomb);
    CHECK(seFor(kBombOtakara, Event::Fuse) == kSpiderBomb);   // lit Dweevil bomb crackle
    CHECK(seFor(kDirigibug, Event::Fuse) == kSpiderBomb);     // lit Dirigibug bomb tick (#1066)
    CHECK(seFor(kCrawbster, Event::Roll) == kRockRoll);
    CHECK(seFor(kCrawbster, Event::Crash) == kRockBreak);
    CHECK(seFor(kAntennaBeetle, Event::Whistle) == kMinicAlert);
    CHECK(seFor(kTitanDweevil, Event::Fire) == kTankFire);
    CHECK(seFor(kTitanDweevil, Event::Step) == kSpiderWalk);
    CHECK(seFor(kGroink, Event::Shot) == kKabutoShot);
    CHECK(seFor(kCannonLarva, Event::Shot) == kKabutoShot);
    CHECK(seFor(kKurage, Event::Hover) == kSaraiHover);
    CHECK(seFor(kKurage, Event::Attack) == kSaraiAttack);
    CHECK(seFor(kOniKurage, Event::Dead) == kSaraiDead);
    CHECK(seFor(kKurage, Event::Step) == kNone);
    CHECK(seFor(kEmpress, Event::Roll) == kKingReady);
    CHECK(seFor(kEmpress, Event::Dead) == kKingDead1);
    // Emperor Bulblax (53) borrows the P1 Emperor boss bank.
    CHECK(seFor(kEmperor, Event::Step) == kKingWalk);
    CHECK(seFor(kEmperor, Event::Appear) == kKingAppear);
    CHECK(seFor(kEmperor, Event::Dive) == kKingSink);
    CHECK(seFor(kEmperor, Event::Roar) == kKingReady);
    CHECK(seFor(kEmperor, Event::Attack) == kKingBero1);
    CHECK(seFor(kEmperor, Event::Eat) == kKingEat);
    CHECK(seFor(kEmperor, Event::Flick) == kKingHip);
    CHECK(seFor(kEmperor, Event::Damage) == kKingCheek);
    CHECK(seFor(kEmperor, Event::Dead) == kKingDead1);
    CHECK(seFor(kEmperor, Event::Hover) == kNone);
    CHECK(seFor(kBreadbug, Event::Appear) == kNone);   // new events stay silent elsewhere
    CHECK(std::strcmp(eventName(Event::Roar), "roar") == 0);
    // Wave 3 mechanics (#964): aquatics, Chrysanthemum, Volatile Dweevil.
    CHECK(seFor(kBombOtakara, Event::Burst) == kBomb);
    CHECK(seFor(kTadpole, Event::Jump) == kFlogJump);
    CHECK(seFor(kTadpole, Event::Land) == kFlogLand);
    CHECK(seFor(kCatfish, Event::Attack) == kChappySwing);
    CHECK(seFor(kHana, Event::Attack) == kChappySwing);
    CHECK(seFor(kHana, Event::Burst) == kNone);
    // Unknown species: silent.
    CHECK(seFor(1, Event::Damage) == kNone);
    CHECK(seFor(0, Event::Step) == kNone);
    CHECK(std::strcmp(eventName(Event::Burst), "burst") == 0);
    CHECK(std::strcmp(eventName(Event::Count), "?") == 0);
}

void ids() {
    // Mirrors of include/SoundID.h (pc_p2_sfx.cpp static_asserts the rest).
    CHECK(kCollecWalk == 0x70);
    CHECK(kCollecDead == 0x72);
    CHECK(kSaraiHover == 0x78);
    CHECK(kSaraiDead == 0x7B);
    CHECK(kBomb == 0x1F);
    CHECK(kKabutoShot == 0x5E);
    CHECK(kSpiderWalk == 0x29);
    CHECK(kRockRoll == 0x64);
    CHECK(kKingWalk == 0x4D);
    CHECK(kKingReady == 0x4E);
    CHECK(kKingBero1 == 0x4F);
    CHECK(kKingEat == 0x53);
    CHECK(kKingCheek == 0x54);
    CHECK(kKingHip == 0x56);
    CHECK(kKingDead1 == 0x57);
    CHECK(kKingAppear == 0x59);
    CHECK(kKingSink == 0x5A);
}

void gate() {
    ActorGate g;
    bool log = false;
    CHECK(g.admit(kBreadbug, Event::Damage, 0.0f, &log) == kCollecDamage);
    CHECK(log);
    CHECK(g.admit(kBreadbug, Event::Damage, 0.1f, &log) == kNone);   // < 0.3 s
    CHECK(!log);
    CHECK(g.admit(kBreadbug, Event::Damage, 0.29f, &log) == kNone);
    CHECK(g.admit(kBreadbug, Event::Damage, 0.31f, &log) == kCollecDamage);
    // Events gate independently.
    CHECK(g.admit(kBreadbug, Event::Dead, 0.32f, &log) == kCollecDead);
    CHECK(g.admit(kBreadbug, Event::Dead, 0.5f, &log) == kNone);      // one cry
    // Unmapped never plays and never touches the gate.
    CHECK(g.admit(kBreadbug, Event::Burst, 1.0f, &log) == kNone);
    CHECK(!log);
    // First play after a large clock (wall time) is never limited.
    ActorGate h;
    CHECK(h.admit(kSnitchbug, Event::Hover, 12345.0f, nullptr) == kSaraiHover);
    CHECK(h.admit(kSnitchbug, Event::Hover, 12345.5f, nullptr) == kNone);
    CHECK(h.admit(kSnitchbug, Event::Hover, 12346.1f, nullptr) == kSaraiHover);
    h.reset();
    CHECK(h.admit(kSnitchbug, Event::Hover, 12346.2f, nullptr) == kSaraiHover);
    CHECK(minInterval(Event::Damage) > 0.29f && minInterval(Event::Damage) < 0.31f);
}

void budget() {
    ActorGate g;
    int stepLogs = 0, damageLogs = 0;
    float t = 0.0f;
    for (int i = 0; i < 40; ++i) {
        bool log = false;
        t += 1.0f;
        if (g.admit(kCrawbster, Event::Step, t, &log) != kNone && log) ++stepLogs;
        log = false;
        if (g.admit(kCrawbster, Event::Damage, t, &log) != kNone && log) ++damageLogs;
    }
    CHECK(stepLogs == markerBudget(Event::Step));
    CHECK(stepLogs < 40);
    CHECK(damageLogs == 40);
}

void stride() {
    Stride s;
    CHECK(!s.advance(0.0f, 0.0f, 30.0f));   // priming
    CHECK(!s.advance(0.0f, 0.0f, 30.0f));   // still
    int steps = 0;
    for (int i = 1; i <= 100; ++i) if (s.advance(float(i) * 3.0f, 0.0f, 30.0f)) ++steps; // 300 units
    CHECK(steps == 10);
    // Teleport: no burst.
    CHECK(!s.advance(5000.0f, 5000.0f, 30.0f));
    CHECK(!s.advance(5000.0f, 5000.0f, 30.0f));
    // Diagonal travel counts Euclidean distance.
    Stride d;
    d.advance(0.0f, 0.0f, 10.0f);
    CHECK(!d.advance(6.0f, 0.0f, 10.0f));
    CHECK(d.advance(6.0f, 8.0f, 10.0f)); // 6 + 8 = 14 >= 10
    CHECK(!d.advance(6.0f, 8.0f, 0.0f));   // zero stride: never
}

void marker() {
    char buf[96];
    const int n = formatMarker(buf, sizeof buf, kDirigibug, 7u, Event::Burst, kBomb);
    CHECK(n > 0);
    CHECK(std::strcmp(buf, "P2_SFX source_id=58 generator=7 event=burst se=0x1F") == 0);
}
} // namespace

int main() {
    section("TABLE", table);
    section("IDS", ids);
    section("GATE", gate);
    section("BUDGET", budget);
    section("STRIDE", stride);
    section("MARKER", marker);
    std::printf("%s p2_sfx_policy_test failures=%d\n", gFailures ? "FAIL" : "PASS", gFailures);
    return gFailures ? 1 : 0;
}
