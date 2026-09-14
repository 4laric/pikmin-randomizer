#pragma once
#include <pc_p2_groink.h>
#include <array>
#include <cstddef>

// Host supplies animation-event edges, never a held event or render frame.
enum class P2GroinkAttackEvent { None, Charge, Smoke, Fire, Return, End };
enum class P2GroinkAttackCommand {
    ResumeMotion, RefreshTarget, FinishMotion, StopMotion, StartAim, StartCharge,
    LargeSmoke, FinishCharge, EmitVolley, ReturnGun, ExitDead, ExitFlick, ResolveNextState
};
struct P2GroinkAttackInput {
    bool activeTick = true;
    bool motionStopped = false;
    bool motionFinishing = false;
    bool gunRotating = false;
    bool gunLocked = false;
    bool flick = false;
    float health = 1;
    P2GroinkAttackEvent event = P2GroinkAttackEvent::None;
};
struct P2GroinkAttackCommands {
    bool valid = false;
    std::array<P2GroinkAttackCommand, 12> items{};
    std::size_t count = 0;
};

// Source StateAttack subset. The host owns motion state/advancement and must
// execute returned commands IN ORDER. begin follows host attack initialization.
class P2GroinkAttack {
public:
    void begin() { mWait = 0; mActive = true; }
    void reset() { mWait = 0; mActive = false; }
    float waitTime() const { return mWait; }
    P2GroinkAttackCommands step(const P2GroinkAttackInput&, float delta);
private:
    float mWait = 0;
    bool mActive = false;
};

// Gun manager rotation state, separate from motion events and projectile pool.
class P2GroinkGunRotation {
public:
    void start() { *this = {}; mRotating = true; }
    void finish() { mLocked = false; mFinished = true; }
    void reset() { *this = {}; }
    bool update(const P2GroinkVec3& muzzle, const P2GroinkVec3& target,
                float search, float radius, float delta);
    static bool returnStep(float angle, float& next, bool& done);
    bool rotating() const { return mRotating; }
    bool locked() const { return mLocked; }
    bool finished() const { return mFinished; }
    float angle() const { return mAngle; }
    float speed() const { return mSpeed; }
private:
    bool mRotating = false, mLocked = false, mFinished = false;
    float mAngle = 0, mSpeed = 0;
};
