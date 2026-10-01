#include "pc_p2_bombsarai_joint.h"

// Release builds pass -DNDEBUG; force assertions on so this engine-free gate
// is not vacuous under ctest.
#undef NDEBUG
#include <cassert>
#include <cmath>
#include <limits>

namespace {
constexpr float kDelta = P2BombSaraiBomb::kSourceDelta;
constexpr float kPi = 3.14159265358979323846f;
constexpr float kEps = 0.0001f;

bool near(float actual, float expected)
{
    return std::fabs(actual - expected) <= kEps;
}

P2BombSaraiBombConfig config()
{
    P2BombSaraiBombConfig c;
    c.gravityPerTick = 6.0f;
    c.fuseHealth = 1.0f;
    c.armLoopTicks = 20;
    c.bombRadius = 5.0f;
    c.blastRadius = 75.0f;
    c.blastHalfHeight = 50.0f;
    c.tekiDamage = 250.0f;
    c.naviPikiDamage = 10.0f;
    return c;
}
}

int main()
{
    // Joint world transform (kamu_jnt1 stand-in): zero yaw is a pure offset.
    {
        const P2BombSaraiVec3 body{ 1.0f, 120.0f, 2.0f };
        const P2BombSaraiVec3 offset{ 0.0f, -40.0f, 0.0f };
        P2BombSaraiVec3 j = P2BombSaraiJoint::compute(body, 0.0f, offset);
        assert(near(j.x, 1.0f) && near(j.y, 80.0f) && near(j.z, 2.0f));
    }

    // Yaw rotates a forward (+z local) offset into (sin, cos) world, matching
    // the source Release lob decomposition (50*sin(face), ·, 50*cos(face)).
    {
        const P2BombSaraiVec3 body{ 0.0f, 70.0f, 0.0f };
        const P2BombSaraiVec3 forward{ 0.0f, 0.0f, 10.0f };
        P2BombSaraiVec3 j = P2BombSaraiJoint::compute(body, 0.0f, forward);
        assert(near(j.x, 0.0f) && near(j.z, 10.0f)); // yaw 0 faces +z
        j = P2BombSaraiJoint::compute(body, kPi / 2.0f, forward);
        assert(near(j.x, 10.0f) && near(j.z, 0.0f)); // yaw 90 faces +x
        j = P2BombSaraiJoint::compute(body, kPi, forward);
        assert(near(j.x, 0.0f) && near(j.z, -10.0f)); // yaw 180 faces -z
    }

    // A lateral (+x local) offset also rotates with the carrier facing.
    {
        const P2BombSaraiVec3 body{ 0.0f, 0.0f, 0.0f };
        const P2BombSaraiVec3 right{ 5.0f, 0.0f, 0.0f };
        P2BombSaraiVec3 j = P2BombSaraiJoint::compute(body, 0.0f, right);
        assert(near(j.x, 5.0f) && near(j.z, 0.0f));
        j = P2BombSaraiJoint::compute(body, kPi / 2.0f, right);
        assert(near(j.x, 0.0f) && near(j.z, -5.0f));
    }

    // followJoint: rides a spawned carrier through its hover bob.
    {
        P2BombSaraiBomb bomb;
        bomb.reset(config());
        assert(bomb.capture(7, { 0.0f, 80.0f, 0.0f }));
        assert(near(bomb.position().y, 80.0f));
        // Carrier hovers down; the host re-attaches the joint each tick.
        const P2BombSaraiVec3 bodies[] = {
            { 0.0f, 78.0f, 0.0f }, { 0.0f, 75.0f, 0.0f }, { 0.0f, 72.0f, 0.0f }
        };
        for (const P2BombSaraiVec3& body : bodies) {
            const P2BombSaraiVec3 offset{ 0.0f, -40.0f, 0.0f };
            P2BombSaraiVec3 joint = P2BombSaraiJoint::compute(body, 0.0f, offset);
            assert(bomb.followJoint(joint));
            assert(bomb.phase() == P2BombSaraiBombPhase::Captured);
        }
        assert(near(bomb.position().y, 72.0f - 40.0f));
    }

    // followJoint is a no-op once the bomb is thrown (InFlight), and before
    // capture; a non-finite joint is rejected.
    {
        P2BombSaraiBomb bomb;
        bomb.reset(config());
        assert(!bomb.followJoint({ 0.0f, 40.0f, 0.0f })); // not captured yet
        assert(bomb.capture(7, { 0.0f, 80.0f, 0.0f }));
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
        assert(!bomb.followJoint({ 0.0f, 5.0f, 0.0f })); // thrown: no longer rides
        assert(near(bomb.position().y, 80.0f));          // position unchanged by the no-op

        P2BombSaraiBomb b2;
        b2.reset(config());
        assert(b2.capture(3, { 0.0f, 80.0f, 0.0f }));
        assert(!b2.followJoint({ std::numeric_limits<float>::quiet_NaN(), 0.0f, 0.0f }));
        assert(near(b2.position().y, 80.0f));
    }

    return 0;
}
