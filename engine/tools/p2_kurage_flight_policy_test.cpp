// Isolated fixtures for pc_p2_kurage_flight_policy.h (Lesser Jellyfloat, #243).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_kurage_flight_policy_test.cpp -o p2_kurage_flight_policy_test.exe
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include "pc_p2_kurage_flight_policy.h"

using namespace p2kurage;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_kurage_flight_policy_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}
static bool near(float a, float b, float eps = 1e-3f) { return std::fabs(a - b) <= eps; }

int main()
{
    Parms parms;

    // --- setHeightVelocity ---
    require(near(heightVelocity(parms, 0.0f, 0.0f, 0.0f, 10.0f), 80.0f), "rises toward flight height when below");
    require(near(heightVelocity(parms, 0.0f, 0.0f, 0.0f, 90.0f), 0.0f), "zero velocity at flight height");
    require(heightVelocity(parms, 0.0f, 0.0f, 0.0f, 140.0f) < 0.0f, "descends when above flight height");
    require(near(heightVelocity(parms, 20.0f, 2.0f, 0.0f, 110.0f), 3.0f * 0.0f), "speedFactor and yOffset shift the target");
    require(near(altitude(0.0f, 55.0f), 55.0f), "altitude is position minus map");

    // --- move pitch timer ---
    {
        float timer = 0.0f;
        const float value = movePitchOffset(timer, 1.0f / 30.0f);
        require(near(timer, kPi / 30.0f), "move pitch timer advances by dt*PI");
        require(near(value, 50.0f * std::sin(kPi / 30.0f)), "move pitch is a 50-unit sine");
        float wrap = kTau - 0.05f;
        movePitchOffset(wrap, 1.0f);
        require(wrap <= kTau, "move pitch timer wraps below TAU");
    }

    // --- keyframe pitch offsets ---
    require(near(attackPitchOffset(0.0f), 0.0f), "attack pitch starts at zero");
    require(near(attackPitchOffset(45.0f), -5.0f), "attack pitch interpolates key 30..65");
    require(near(flickPitchOffset(12.0f), -10.0f), "flick pitch interpolates key 10..15");
    require(near(takeOffPitchOffset(45.0f), -51.25f), "takeoff pitch interpolates key 40..52");
    require(near(fallPitchOffset(0.5f), -16.0f), "fall pitch scales timer by 30 then interpolates");
    require(near(fallPitchOffset(2.0f), 0.0f), "fall pitch only samples four segments (source quirk)");

    // --- updateFallTimer ---
    {
        float timer = 0.0f;
        updateFallTimer(3, timer, 0.5f);
        require(near(timer, 0.5f), "fall timer accumulates with Pikmin stuck");
        updateFallTimer(0, timer, 0.5f);
        require(near(timer, 0.0f), "fall timer resets with no Pikmin stuck");
    }

    // --- getFlyingNextState ---
    require(flyingNextState(parms, 0.0f, false, 0.0f, 0) == FlyingNext::Dead, "death routes to Dead");
    require(flyingNextState(parms, 100.0f, true, 0.0f, 0) == FlyingNext::Fall, "Purple latch routes to Fall");
    require(flyingNextState(parms, 100.0f, false, parms.shakeTime + 1.0f, 2) == FlyingNext::FlyFlick,
            "long shake with few Pikmin flicks");
    require(flyingNextState(parms, 100.0f, false, 0.0f, parms.minFallPiki) == FlyingNext::Fall,
            "reaching the minimum Pikmin count falls");
    require(flyingNextState(parms, 100.0f, false, 0.0f, 3) == FlyingNext::Null, "otherwise keeps flying");

    // --- getSearchedTarget / isSuck geometry ---
    require(inSuctionWindow(100.0f, 10.0f, 80.0f), "candidate inside the vertical window");
    require(!inSuctionWindow(100.0f, 10.0f, 39.0f), "candidate below currY - offset - 50 rejected");
    require(!inSuctionWindow(100.0f, 10.0f, 120.0f), "candidate above Sarai rejected");

    SearchCandidate good; good.y = 80.0f; good.sqrDistXZ = 100.0f * 100.0f; good.angleRad = 0.05f;
    require(searchAdmit(100.0f, 0.0f, 90.0f, 300.0f, good), "legal scan candidate admitted");
    SearchCandidate dead = good; dead.alive = false;
    require(!searchAdmit(100.0f, 0.0f, 90.0f, 300.0f, dead), "dead candidate rejected");
    SearchCandidate stuck = good; stuck.stickerIsSelf = true;
    require(!searchAdmit(100.0f, 0.0f, 90.0f, 300.0f, stuck), "already stuck to this Kurage rejected");
    SearchCandidate far = good; far.sqrDistXZ = 301.0f * 301.0f;
    require(!searchAdmit(100.0f, 0.0f, 90.0f, 300.0f, far), "beyond sight radius rejected");
    SearchCandidate wide = good; wide.angleRad = 10.0f;
    require(!searchAdmit(100.0f, 0.0f, 90.0f, 300.0f, wide), "outside view angle rejected");

    require(inAttackRange(100.0f, 0.0f, 60.0f, 80.0f, 50.0f * 50.0f), "inside max attack range and window");
    require(!inAttackRange(100.0f, 0.0f, 60.0f, 80.0f, 61.0f * 61.0f), "outside max attack range rejected");

    // --- suckPikmin admission ---
    require(suckAdmit(parms, 100.0f, 0.0f, 40.0f, 80.0f, 30.0f * 30.0f, 0, 0.01f), "legal suction admitted below cap");
    require(!suckAdmit(parms, 100.0f, 0.0f, 40.0f, 80.0f, 30.0f * 30.0f, parms.maxSuckPiki, 0.01f),
            "suction refused at the cap");
    require(!suckAdmit(parms, 100.0f, 0.0f, 40.0f, 80.0f, 30.0f * 30.0f, 0, 0.5f),
            "suction refused above the fp12 chance roll");
    require(!suckAdmit(parms, 100.0f, 0.0f, 40.0f, 80.0f, 41.0f * 41.0f, 0, 0.01f),
            "suction refused beyond the attack radius");

    std::printf("p2_kurage_flight_policy_test PASS checks=%d\n", gChecks);
    std::fflush(stdout);
    return 0;
}
