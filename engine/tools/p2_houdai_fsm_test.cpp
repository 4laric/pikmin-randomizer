#include "pc_p2_houdai_fsm.h"

// Release builds pass -DNDEBUG; force assertions on so this gate is not vacuous.
#undef NDEBUG
#include <cassert>
#include <cmath>
#include <cstdio>

// Engine-free source-transition gate for the Man-at-Legs brain (#173). Source:
// HoudaiState.cpp, Houdai.cpp, HoudaiShotGun.cpp, enemyAction.cpp isStartFlick.
// Unit tests are not admission evidence; they pin the transition table only.

namespace {
using S = P2LongLegsState;

P2HoudaiInput base()
{
    P2HoudaiInput in;
    in.health = 2800.0f;
    in.roll[0] = in.roll[1] = in.roll[2] = in.roll[3] = 0.5f;
    return in;
}

int runUntil(P2HoudaiFsm& fsm, P2HoudaiInput in, S target, int limit, P2HoudaiOutput* last = nullptr)
{
    P2HoudaiOutput out;
    for (int i = 1; i <= limit; ++i) {
        fsm.update(in, out);
        if (out.fireShell) {}
        if (fsm.state() == target) {
            if (last) *last = out;
            return i;
        }
    }
    return -1;
}
} // namespace

int main()
{
    const P2HoudaiParms parms;

    // isStartFlick tiers (disc ip01..ip07): fewer than 30 stuck needs >10 blows.
    assert(!P2HoudaiFsm::isStartFlickFor(parms, 5, 10.0f));
    assert(P2HoudaiFsm::isStartFlickFor(parms, 5, 11.0f));
    assert(!P2HoudaiFsm::isStartFlickFor(parms, 30, 15.0f));
    assert(P2HoudaiFsm::isStartFlickFor(parms, 30, 16.0f));
    assert(!P2HoudaiFsm::isStartFlickFor(parms, 40, 25.0f));
    assert(P2HoudaiFsm::isStartFlickFor(parms, 60, 31.0f));

    // Stay -> Land (wake) -> Wait after the 230-frame landing clip; the
    // US damageCallBack takes a stuck hit at 1x in Stay (and wakes it), 0.25x
    // in Land, 1x awake.
    {
        P2HoudaiFsm fsm;
        fsm.reset(parms, P2HoudaiVec{}, 0.0f);
        P2HoudaiInput in = base();
        P2HoudaiOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::Stay && out.drawHidden && out.damageRate == 1.0f);
        in.damageAttempt = true; // damage in Stay wakes the boss into Land
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Land && out.damageRate == 0.25f);
        in.damageAttempt = false;
        int flicks = 0, ticks = 0;
        while (fsm.state() == S::Land && ticks < 400) {
            fsm.update(in, out);
            flicks += out.flickStuck;
            ++ticks;
        }
        assert(fsm.state() == S::Wait);
        assert(ticks >= P2HoudaiFsm::kLandingFrames && ticks <= P2HoudaiFsm::kLandingFrames + 2);
        assert(flicks == 5); // keys 2, 4, 5, 6 and END flick stuck Pikmin
        assert(out.damageRate == 1.0f);
    }

    // Wait -> Walk after its duration (at the wait clip END); Walk translates
    // the body toward a Pikmin and ends at a stride boundary back in Wait.
    {
        P2HoudaiFsm fsm;
        fsm.reset(parms, P2HoudaiVec{}, 0.0f);
        P2HoudaiInput in = base();
        in.wake = true;
        assert(runUntil(fsm, in, S::Wait, 400) > 0);
        in.wake = false;
        in.walkPikiFound = true;
        in.walkPiki = P2HoudaiVec{0.0f, 0.0f, 500.0f};
        assert(runUntil(fsm, in, S::Walk, 200) > 0);
        P2HoudaiOutput out;
        float moved = 0.0f;
        int ticks = 0;
        while (fsm.state() == S::Walk && ticks < 600) {
            fsm.update(in, out);
            if (out.moving) {
                moved = out.bodyPos.z;
                in.pos = out.bodyPos;
            }
            ++ticks;
        }
        assert(fsm.state() == S::Wait);
        assert(moved > 100.0f);
    }

    // Hits past the tier trigger Flick from Wait; Flick key 3 shakes stuck
    // Pikmin with the disc shake parms and always ends in Shot; Shot aims,
    // fires bursts, and ends in Walk (never Wait).
    {
        P2HoudaiFsm fsm;
        fsm.reset(parms, P2HoudaiVec{}, 0.0f);
        P2HoudaiInput in = base();
        in.wake = true;
        assert(runUntil(fsm, in, S::Wait, 400) > 0);
        in.wake = false;
        in.hits = 12;
        in.stuck = 5;
        in.tookDamage = true;
        P2HoudaiOutput out;
        fsm.update(in, out);
        in.hits = 0;
        in.tookDamage = false;
        assert(runUntil(fsm, in, S::Flick, 60) > 0);
        bool shook = false;
        int ticks = 0;
        while (fsm.state() == S::Flick && ticks < 200) {
            fsm.update(in, out);
            if (out.flickStuck) {
                shook = true;
                assert(out.flickKnockback == 500.0f && out.flickChance == 1.0f);
            }
            ++ticks;
        }
        assert(shook && fsm.state() == S::Shot && fsm.flickTimer() == 0.0f);
        in.gunTargetFound = true;
        in.gunTarget = P2HoudaiVec{200.0f, 0.0f, 0.0f};
        int shells = 0, bursts = 0, pauses = 0;
        ticks = 0;
        while (fsm.state() == S::Shot && ticks < 30 * 40) {
            fsm.update(in, out);
            shells += out.fireShell;
            bursts += out.burstOn;
            pauses += out.burstOff;
            if (out.fireShell) {
                const float v = std::sqrt(out.shellVel.x * out.shellVel.x + out.shellVel.y * out.shellVel.y
                                          + out.shellVel.z * out.shellVel.z);
                assert(std::fabs(v - 600.0f) < 1.0f);
            }
            ++ticks;
        }
        assert(fsm.state() == S::Walk);
        assert(shells > 10 && bursts >= 1);
        // Aim ~2 s + firing ~7 s + return and 2 s: the cycle is ~10-15 s, not a 1.3 s clip.
        assert(ticks > 30 * 9 && ticks < 30 * 20);
        std::printf("shot ticks=%d shells=%d bursts=%d pauses=%d\n", ticks, shells, bursts, pauses);
    }

    // Burst cooldown: 40 s undamaged in Wait/Walk opens Shot; damage resets it.
    {
        P2HoudaiFsm fsm;
        fsm.reset(parms, P2HoudaiVec{}, 0.0f);
        P2HoudaiInput in = base();
        in.wake = true;
        assert(runUntil(fsm, in, S::Wait, 400) > 0);
        in.wake = false;
        // Stay+Land already accumulated ~7.7 s; keep cycling Wait/Walk.
        assert(runUntil(fsm, in, S::Shot, 30 * 60) > 0);
        assert(fsm.burstTimer() > parms.burstCooldown);
    }

    // Death: health 0 in Walk transits to Dead immediately; the dead clip
    // (140 frames) ends with exactly one deadEnd.
    {
        P2HoudaiFsm fsm;
        fsm.reset(parms, P2HoudaiVec{}, 0.0f);
        P2HoudaiInput in = base();
        in.wake = true;
        assert(runUntil(fsm, in, S::Wait, 400) > 0);
        in.wake = false;
        assert(runUntil(fsm, in, S::Walk, 200) > 0);
        in.health = 0.0f;
        P2HoudaiOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::Dead && out.damageRate == 0.0f);
        int ends = 0;
        for (int i = 0; i < 300; ++i) {
            fsm.update(in, out);
            ends += out.deadEnd;
        }
        assert(ends == 1);
    }

    // Rig draw contract (#1012): the body pose clip follows the state, Stay shows landing frame 0, Walk
    // holds the last frame of the clip that was playing, and the muzzle starts at the posed gun pivot the
    // host passes in (not the bind-pose height).
    {
        P2HoudaiFsm fsm;
        fsm.reset(parms, P2HoudaiVec{}, 0.0f);
        P2HoudaiInput in = base();
        P2HoudaiOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::Stay && fsm.poseClip() == P2HoudaiFsm::kPoseLanding && fsm.poseFrame() == 0);
        assert(!fsm.poseAdvancing());
        in.wake = true;
        fsm.update(in, out);
        assert(fsm.state() == S::Land && fsm.poseAdvancing());
        in.wake = false;
        int lastFrame = 0;
        while (fsm.state() == S::Land) {
            fsm.update(in, out);
            if (fsm.state() != S::Land) break;  // the Wait entry restarts the pose clock at wait frame 0
            assert(fsm.poseFrame() >= lastFrame && fsm.poseFrame() <= P2HoudaiFsm::kLandingFrames - 1);
            lastFrame = fsm.poseFrame();
        }
        assert(fsm.state() == S::Wait && fsm.poseClip() == P2HoudaiFsm::kPoseWait && fsm.poseFrame() == 0);
        assert(lastFrame >= 228);
        // Wait loops frames 0..39 of the 40-frame clip; Walk then holds the last wait frame.
        in.walkPikiFound = true;
        in.walkPiki = P2HoudaiVec{0.0f, 0.0f, 500.0f};
        int maxWait = 0;
        while (fsm.state() == S::Wait) {
            fsm.update(in, out);
            if (fsm.state() == S::Wait) maxWait = fsm.poseFrame() > maxWait ? fsm.poseFrame() : maxWait;
        }
        assert(fsm.state() == S::Walk && maxWait <= P2HoudaiFsm::kWaitFrames - 1);
        const int heldClip = fsm.poseClip(), heldFrame = fsm.poseFrame();
        for (int i = 0; i < 40; ++i) fsm.update(in, out);
        assert(fsm.state() == S::Walk && fsm.poseClip() == heldClip && fsm.poseFrame() == heldFrame);
        assert(!fsm.poseAdvancing());
        assert(heldClip == P2HoudaiFsm::kPoseWait);
    }
    {
        P2HoudaiFsm fsm;
        fsm.reset(parms, P2HoudaiVec{}, 0.0f);
        P2HoudaiInput in = base();
        in.wake = true;
        assert(runUntil(fsm, in, S::Wait, 400) > 0);
        in.wake = false;
        in.hits = 12;
        in.stuck = 5;
        in.tookDamage = true;
        P2HoudaiOutput out;
        fsm.update(in, out);
        in.hits = 0;
        in.tookDamage = false;
        assert(runUntil(fsm, in, S::Flick, 60) > 0 && fsm.poseClip() == P2HoudaiFsm::kPoseFlick);
        assert(runUntil(fsm, in, S::Shot, 200) > 0 && fsm.poseClip() == P2HoudaiFsm::kPoseAttack);
        in.gunPosValid = true;
        in.gunPos = P2HoudaiVec{10.0f, 90.0f, -5.0f};  // deployed gun pivot (attack clip frame 39: y 90)
        in.gunTargetFound = true;
        in.gunTarget = P2HoudaiVec{400.0f, 0.0f, -5.0f};
        bool fired = false, aimed = false;
        for (int i = 0; i < 30 * 15 && !fired; ++i) {
            fsm.update(in, out);
            aimed = aimed || fsm.gunAiming();
            if (out.fireShell) {
                fired = true;
                // Muzzle = pivot + 45 along the barrel (jitter 0.004): barrel is aimed at the target.
                const P2HoudaiVec d = fsm.gunDirection();
                assert(std::fabs(out.shellPos.x - (10.0f + d.x * 45.0f)) < 1.0f);
                assert(std::fabs(out.shellPos.y - (90.0f + d.y * 45.0f)) < 1.0f);
                assert(std::fabs(out.shellPos.z - (-5.0f + d.z * 45.0f)) < 1.0f);
                assert(d.x > 0.8f && d.y < 0.0f);
            }
        }
        assert(fired && aimed);
    }

    std::printf("p2_houdai_fsm_test: all passed\n");
    return 0;
}
