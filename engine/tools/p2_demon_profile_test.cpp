// #215 Demon (Bumbling Snitchbug, 32) species-profile policy test. Engine-free.
// Each check names the retail line it pins (pikmin2-research Demon.cpp,
// Sarai.cpp, SaraiState.cpp, enemyBase.cpp); the numeric fixtures are the
// GPVE01 rev 0 demon/enemyparm.txt values.
#include "pc_p2_demon_profile.h"
#include "pc_p2_sarai_fsm.h"
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <string>

namespace {
int gChecks = 0;
void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_demon_profile_test: %s\n", what);
        std::exit(1);
    }
}
bool near(float a, float b, float eps = 1e-4f) { return a - b < eps && b - a < eps; }

const char* kRetail =
    "P2_DEMON_PARMS_1 b7a2b284bf30699a15a8464bd85dcfc56fa34cddb7e3c30b4d6ce4b949f667b5 26\n"
    "general fp00 1500\ngeneral fp06 80\ngeneral fp08 0.1\ngeneral fp28 10\ngeneral fp09 300\n"
    "general fp10 200\ngeneral fp12 200\ngeneral fp13 90\ngeneral fp16 1\ngeneral fp17 80\n"
    "general fp18 1\ngeneral fp24 10\n"
    "proper fp01 85\nproper fp02 120\nproper fp03 50\nproper fp04 100\nproper fp05 75\nproper fp06 3\n"
    "proper fp11 1.5\nproper fp12 1\nproper fp21 0.3\nproper fp22 0.85\nproper fp23 1\nproper fp31 0.3\n"
    "proper fp32 0.95\nproper fp41 300\n";
} // namespace

int main()
{
    // Parms: retail values land in the right fields; incomplete/duplicate/unknown rows fail closed.
    p2demon::Parms parms;
    {
        std::istringstream in(kRetail);
        require(p2demon::loadParms(in, parms), "retail parms load");
    }
    require(parms.retail, "retail flag set");
    require(near(parms.general.life, 1500.0f), "fp00 life 1500");
    require(near(parms.general.territoryRadius, 300.0f) && near(parms.general.homeRadius, 200.0f), "fp09/fp10");
    require(near(parms.general.viewAngle, 90.0f) && near(parms.general.sightRadius, 200.0f), "fp13/fp12");
    require(near(parms.general.attackDamage, 10.0f), "fp24 attack damage (InteractFallMeck)");
    require(near(parms.proper.normalFlightHeight, 85.0f) && near(parms.proper.grabFlightHeight, 120.0f),
            "fp01/fp02 flight heights (Demon grabs higher than it patrols)");
    require(near(parms.proper.fallMeckSpeed, 300.0f) && near(parms.proper.strugglingTime, 1.0f), "fp41/fp23");
    require(near(parms.proper.payoffProbability5, 0.85f), "fp22 payoff (5)");
    {
        std::string missing(kRetail);
        missing.replace(missing.find("26\n"), 3, "25\n");
        missing.erase(missing.find("proper fp41 300\n"));
        std::istringstream in(missing);
        p2demon::Parms p;
        require(!p2demon::loadParms(in, p) && !p.retail, "missing fp41 row fails closed");
    }
    {
        std::string dup(kRetail);
        dup.replace(dup.find("proper fp41 300"), 15, "proper fp01 300");
        std::istringstream in(dup);
        p2demon::Parms p;
        require(!p2demon::loadParms(in, p), "duplicate row fails closed");
    }
    {
        std::string bad(kRetail);
        bad.replace(bad.find("general fp24"), 12, "general fp99");
        std::istringstream in(bad);
        p2demon::Parms p;
        require(!p2demon::loadParms(in, p), "unknown key fails closed");
    }

    // Demon::mAttackTimer: Sarai::onInit resetAttackableTimer(12800) -> the
    // first query passes; FallMeck::cleanup resetAttackableTimer(0) -> the next
    // query passes only after > 3 s of accumulated queries.
    p2demon::AttackTimer timer;
    require(timer.query(1.0f / 30.0f), "initial 12800 timer passes immediately");
    timer.reset(0.0f);
    int queries = 0;
    while (!timer.query(1.0f / 30.0f)) ++queries;
    require(queries >= 89 && queries <= 91, "post-drop gate holds ~3 s of queries (90 at 30 fps)");
    timer.reset(0.0f);
    require(!timer.query(2.9f), "2.9 s is still gated");
    require(timer.query(0.2f), "3.1 s passes");

    // Demon::getAttackableTarget geometry: full TORADIANS(fp13) view, territory, sight.
    const auto& g = parms.general;
    require(p2demon::captainTargetable(g, 0.0f, true, false, 80.0f * p2sarai::kDeg2Rad, 100.0f * 100.0f),
            "captain at 80 deg inside the 90 deg view");
    require(!p2demon::captainTargetable(g, 0.0f, true, false, 100.0f * p2sarai::kDeg2Rad, 100.0f * 100.0f),
            "captain at 100 deg outside TORADIANS(90) (Sarai's PI*DEG2RAD form would accept it)");
    require(p2sarai::viewHalfAngle(90.0f) > 100.0f * p2sarai::kDeg2Rad,
            "mutant guard: the Sarai view expression is wider, so the Demon test above is discriminating");
    require(!p2demon::captainTargetable(g, 301.0f * 301.0f, true, false, 0.0f, 10.0f), "outside territory 300");
    require(!p2demon::captainTargetable(g, 0.0f, true, false, 0.0f, 201.0f * 201.0f), "outside sight 200");
    require(!p2demon::captainTargetable(g, 0.0f, true, true, 0.0f, 10.0f), "mouth-stuck captain skipped");
    require(!p2demon::captainTargetable(g, 0.0f, false, false, 0.0f, 10.0f), "dead captain skipped");

    // turnToTarget clamp (fp08 0.1, fp28 10 deg).
    require(near(p2demon::turnStep(1.0f, g.turnSpeed, g.maxTurnAngle), 0.1f), "small turn is angle*fp08");
    require(near(p2demon::turnStep(3.0f, g.turnSpeed, g.maxTurnAngle), 10.0f * p2sarai::kDeg2Rad),
            "large turn clamps to fp28");

    // Attack hunt descent: ((targetY + 17.5 - y)/dt) * fp31 clamped to [-2500, 1000].
    require(near(p2demon::huntDescentVelocity(parms.proper, 0.0f, 85.0f, 1.0f / 30.0f), -607.5f, 0.05f),
            "85 above the captain: (17.5 - 85) * 30 * fp31");
    require(near(p2demon::huntDescentVelocity(parms.proper, 0.0f, 400.0f, 1.0f / 30.0f), -2500.0f),
            "far above the captain clamps at -2500");
    require(near(p2demon::huntDescentVelocity(parms.proper, 0.0f, 17.5f, 1.0f / 30.0f), 0.0f),
            "17.5 above the captain holds");

    // setHeightVelocity climb: fp11/fp12 lerp by stuck Pikmin, grab height when carrying.
    require(near(p2sarai::heightVelocity(parms.proper, 0, false, 0.0f, 0.0f), 1.5f * 85.0f),
            "no stickers: fp11 * (mapY + fp01 - y)");
    require(near(p2sarai::heightVelocity(parms.proper, 5, true, 0.0f, 0.0f), 1.0f * 120.0f),
            "5 stickers while carrying: fp12 * fp02");

    // Pikmin weight -> Fall/Flick: getNextStateOnHeight with Demon fp21/fp22.
    p2sarai::Fsm fsm(parms.proper);
    fsm.forceState(p2sarai::State::Move, 0.5f);
    p2sarai::In in;
    in.health = 1500.0f;
    in.mapY = 0.0f;
    in.positionY = 85.0f;
    in.bodyStuckCount = 3; // three Pikmin on the body, nothing in the mouth
    in.randomUnit = 0.99f; // above every payoff probability -> Fall
    const p2sarai::Out out = fsm.tick(in);
    require(fsm.state() == p2sarai::State::Fall && out.flickAttackers, "stuck Pikmin at altitude -> Fall + flickStickTarget");
    in.bodyStuckCount = 0;
    in.health = 0.0f;
    in.positionY = 5.0f;
    in.motionFinished = true;
    fsm.tick(in);
    require(fsm.state() == p2sarai::State::Dead, "Fall END with health <= 0 -> Dead");

    // EnemyBase simulation: flying pulls all axes; ground adds gravity.
    p2demon::Velocity v{0, 100, 0}, t{30, 0, 0};
    const auto fly = p2demon::simulate(v, t, true, 1.0f / 30.0f, 0.1f, 1000.0f);
    require(near(fly.x, 10.0f) && near(fly.y, 100.0f - 100.0f / 3.0f, 1e-3f), "flying accel scale dt/s003");
    const auto ground = p2demon::simulate(v, t, false, 1.0f / 30.0f, 0.1f, 1000.0f);
    require(near(ground.y, 100.0f - 1000.0f / 30.0f, 1e-3f), "ground state falls under gravity");

    std::printf("p2_demon_profile_test PASS checks=%d\n", gChecks);
    return 0;
}
