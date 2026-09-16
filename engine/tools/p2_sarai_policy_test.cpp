// Isolated fixtures for pc_p2_sarai_policy.h (Swooping Snitchbug, #230/#166).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_sarai_policy_test.cpp -o p2_sarai_policy_test.exe
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include "pc_p2_sarai_policy.h"

using namespace p2sarai;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_sarai_policy_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}
static bool near(float a, float b, float eps = 1e-4f) { return std::fabs(a - b) <= eps; }

int main()
{
    Parms parms;

    // --- climbingFactor / heightVelocity (source setHeightVelocity) ---
    require(near(climbingFactor(parms, 0), parms.climbingFactor0), "zero weight uses climbingFactor0");
    require(near(climbingFactor(parms, kMaxWeightFactor), parms.climbingFactor5), "full weight uses climbingFactor5");
    require(near(climbingFactor(parms, 7), parms.climbingFactor5), "over-cap weight clamps to factor5");
    require(near(climbingFactor(parms, -3), parms.climbingFactor0), "negative weight clamps to factor0");
    require(near(climbingFactor(parms, 1), 1.4f), "weight 1 lerps to 1.4");

    require(near(heightVelocity(parms, 0, false, 0.0f, 90.0f), 1.5f * (parms.normalFlightHeight - 90.0f)),
            "normal flight height used when not carrying");
    require(near(heightVelocity(parms, 0, true, 0.0f, 90.0f), 1.5f * (parms.grabFlightHeight - 90.0f)),
            "grab flight height used while carrying");
    require(heightVelocity(parms, 0, false, 0.0f, 10.0f) > 0.0f, "rises when below target height");
    require(heightVelocity(parms, 0, false, 0.0f, 200.0f) < 0.0f, "descends when above target height");
    require(near(altitude(0.0f, 42.0f), 42.0f), "altitude is position minus map");

    // --- getStickPikminNum ---
    require(stickPikminNum(3, 1) == 2, "body-latched excludes mouth-carried");
    require(stickPikminNum(2, 2) == 0, "all mouth slots occupied -> no body attackers");

    // --- getNextStateOnHeight ---
    require(nextStateOnHeight(parms, 0.0f, 0, 2, false, 0.5f) == HeightDecision::Fall, "death routes to Fall");
    require(nextStateOnHeight(parms, 100.0f, 0, 2, true, 0.5f) == HeightDecision::Fall, "Purple latch routes to Fall");
    require(nextStateOnHeight(parms, 100.0f, 2, 2, false, 0.0f) == HeightDecision::None, "no body attackers -> None");
    // stuckPiki 1 -> fallChance = payoffProbability1 = 0.1
    require(nextStateOnHeight(parms, 100.0f, 0, 1, false, 0.05f) == HeightDecision::Flick, "below chance flicks");
    require(nextStateOnHeight(parms, 100.0f, 0, 1, false, 0.20f) == HeightDecision::Fall, "at/above chance falls");
    // stuckPiki 5 -> fallChance = payoffProbability5 = 0.7
    require(nextStateOnHeight(parms, 100.0f, 0, 5, false, 0.69f) == HeightDecision::Flick, "five attackers flicks below fp22");
    require(nextStateOnHeight(parms, 100.0f, 0, 5, false, 0.71f) == HeightDecision::Fall, "five attackers falls above fp22");
    // monotonic: the escape threshold probability never decreases with more attackers
    for (int n = 2; n <= 5; ++n) {
        bool mono = nextStateOnHeight(parms, 100.0f, 0, n, false, 0.15f) != HeightDecision::Fall
                 || nextStateOnHeight(parms, 100.0f, 0, n - 1, false, 0.15f) == HeightDecision::Fall;
        require(mono, "escape probability is non-decreasing with attacker count");
    }

    // --- setRandTarget radius ---
    require(near(randTargetRadius(parms, 200.0f, 400.0f, true, false, 0.5f), 100.0f), "carrying uses home radius");
    require(near(randTargetRadius(parms, 200.0f, 400.0f, false, true, 0.5f), 75.0f), "cave uses 50 + rand(50)");
    require(near(randTargetRadius(parms, 200.0f, 400.0f, false, false, 0.5f), 300.0f), "surface uses home..territory");
    require(near(randTargetRadius(parms, 200.0f, 400.0f, false, false, 0.0f), 200.0f), "surface floor is home radius");

    // --- fallMeckGround ---
    require(near(fallMeckVelocity(parms), -parms.fallMeckSpeed), "fallmeck downward speed");

    // --- Attack timing / transitions ---
    require(!attackMayCatch(16.0f), "catch starts strictly after frame 16");
    require(attackMayCatch(16.1f), "catch available past frame 16");
    require(attackExit(true, false, false) == AttackExit::Fail, "fail event without catch");
    require(attackExit(false, true, true) == AttackExit::CatchFly, "END with catch enters CatchFly");
    require(attackExit(false, true, false) == AttackExit::Move, "END without catch returns to Move");
    require(attackExit(false, false, true) == AttackExit::None, "no transition mid-motion");

    // --- CatchFly height decision trigger ---
    require(catchFlyReadyForHeightDecision(60.0f, 0.0f, parms, false), "above transition height decides");
    require(catchFlyReadyForHeightDecision(10.0f, 3.5f, parms, false), "long timer decides");
    require(catchFlyReadyForHeightDecision(10.0f, 0.0f, parms, true), "motion END decides");
    require(!catchFlyReadyForHeightDecision(10.0f, 1.0f, parms, false), "below thresholds keeps flying");

    // --- getAttackableTarget geometry ---
    {
        TargetQuery query;
        query.sqrDistToHome = 100.0f * 100.0f;
        query.territoryRadius = 400.0f;
        query.sightRadius = 300.0f;
        query.viewAngleDeg = 180.0f;

        TargetCandidate good;
        good.sqrDistXZ = 150.0f * 150.0f;
        require(targetable(query, good), "in-territory valid Pikmin is targetable");

        TargetCandidate far = good; far.sqrDistXZ = 301.0f * 301.0f;
        require(!targetable(query, far), "beyond sight radius is rejected");

        TargetCandidate dead = good; dead.alive = false;
        require(!targetable(query, dead), "dead candidate rejected");
        TargetCandidate flower = good; flower.isPikmin = false;
        require(!targetable(query, flower), "non-Pikmin rejected");
        TargetCandidate mouth = good; mouth.stickToMouth = true;
        require(!targetable(query, mouth), "mouth-stuck rejected");
        TargetCandidate self = good; self.stickerIsSelf = true;
        require(!targetable(query, self), "already stuck to this Sarai rejected");
        TargetCandidate air = good; air.floorTriangle = false;
        require(!targetable(query, air), "airborne (no floor triangle) rejected");

        TargetQuery outside = query; outside.sqrDistToHome = 400.0f * 400.0f;
        require(!targetable(outside, good), "outside territory is not scanned");

        TargetQuery narrow = query; narrow.viewAngleDeg = 1.0f;
        TargetCandidate onAxis = good; onAxis.angleRad = 0.01f;
        TargetCandidate offAxis = good; offAxis.angleRad = 0.10f;
        require(targetable(narrow, onAxis), "candidate inside the view half-angle accepted");
        require(!targetable(narrow, offAxis), "candidate outside the view half-angle rejected");
        require(near(viewHalfAngle(180.0f), kPi * kPi), "view half-angle transcribes PI*(DEG2RAD*angle)");
    }

    std::printf("p2_sarai_policy_test PASS checks=%d\n", gChecks);
    std::fflush(stdout);
    return 0;
}
