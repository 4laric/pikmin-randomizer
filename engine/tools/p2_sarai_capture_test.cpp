// Isolated fixtures for pc_p2_sarai_capture.h (Swooping Snitchbug #242, lane 30).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_sarai_capture_test.cpp -o p2_sarai_capture_test.exe
#include <cstdio>
#include <cstdlib>
#include "pc_p2_sarai_capture.h"

using namespace p2sarai;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_sarai_capture_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

int main()
{
    // --- captureEligible: source eatPikmin predicate ---
    {
        MouthCandidate ok;
        require(captureEligible(ok), "default candidate eligible");
        MouthCandidate dead = ok; dead.alive = false;
        require(!captureEligible(dead), "dead candidate rejected");
        MouthCandidate nonPiki = ok; nonPiki.isPikmin = false;
        require(!captureEligible(nonPiki), "non-Pikmin candidate rejected");
        MouthCandidate stuck = ok; stuck.stuckToMouth = true;
        require(!captureEligible(stuck), "mouth-stuck candidate rejected");
        MouthCandidate self = ok; self.stickerIsSelf = true;
        require(!captureEligible(self), "body-latched-to-self candidate rejected");
        MouthCandidate far = ok; far.withinMouthRadius = false;
        require(!captureEligible(far), "out-of-mouth-radius candidate rejected");
    }

    // --- selectMouthCaptures: nearest-first up to two slots, exactly-once ---
    {
        MouthCandidate c[4];
        float d[4] = { 9.0f, 4.0f, 1.0f, 25.0f };
        int chosen[2] = { -1, -1 };
        const int n = selectMouthCaptures(c, 4, d, chosen);
        require(n == 2, "two candidates chosen for two slots");
        require(chosen[0] == 2 && chosen[1] == 1, "nearest-first ordering");
    }
    {
        // Only one eligible -> one slot filled.
        MouthCandidate c[3];
        c[0].stuckToMouth = true;
        c[1].alive = false;
        float d[3] = { 1.0f, 2.0f, 3.0f };
        int chosen[2] = { -1, -1 };
        require(selectMouthCaptures(c, 3, d, chosen) == 1 && chosen[0] == 2,
            "only eligible candidate chosen once");
    }
    {
        // Non-finite / negative distances must never be selected.
        MouthCandidate c[2];
        float d[2] = { -1.0f, 2.0f };
        int chosen[2] = { -1, -1 };
        const float nan = std::nanf("");
        float dn[2] = { nan, 2.0f };
        require(selectMouthCaptures(c, 2, dn, chosen) == 1 && chosen[0] == 1,
            "non-finite distance candidate skipped");
        require(selectMouthCaptures(c, 2, d, chosen) == 1 && chosen[0] == 1,
            "negative distance candidate skipped");
    }
    {
        // No candidates -> zero captures; degenerate inputs rejected.
        int chosen[2] = { -1, -1 };
        require(selectMouthCaptures(nullptr, 0, nullptr, chosen) == 0, "null inputs safe");
        MouthCandidate c[1];
        float d[1] = { 1.0f };
        require(selectMouthCaptures(c, 65, d, chosen) == 0, "count over limit rejected");
    }

    // --- fallMeckReleaseVelocity: source -fp41 downward velocity ---
    {
        require(fallMeckReleaseVelocity(200.0f) == -200.0f, "fallmeck default downward velocity");
        require(fallMeckReleaseVelocity(0.0f) == -0.0f, "zero fallmeck speed");
        require(fallMeckReleaseVelocity(-5.0f) == -200.0f, "negative speed falls back to default");
    }

    // --- fallMeckDamage: source general mAttackDamage default ---
    {
        require(fallMeckDamage(10.0f) == 10.0f, "attack damage passthrough");
        require(fallMeckDamage(-1.0f) == kFallMeckDamage, "negative damage falls back");
    }

    // --- shared constants (source initMouthSlots / Parms) ---
    {
        require(kMouthSlots == 2 && kMouthRadius == 15.0f, "two mouth slots, radius 15");
        require(kNoSlot == -1, "no-slot sentinel");
        require(Parms().fallMeckSpeed == 200.0f, "fallmeck speed constant");
    }

    std::printf("p2_sarai_capture_test PASS checks=%d\n", gChecks);
    std::fflush(stdout);
    return 0;
}
