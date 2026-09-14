#pragma once

#include <cmath>

// Isolated MiniHoudai (Groink) shell policy.  It deliberately has no actor,
// map, damage, sound, or effect dependency; a future host integration owns
// those concerns and supplies the world trace.
struct P2GroinkVec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

struct P2GroinkMuzzle {
    // `kuti` world-matrix columns: source emits along column 0 from column 3.
    P2GroinkVec3 column0;
    P2GroinkVec3 column1;
    P2GroinkVec3 column2;
    P2GroinkVec3 column3;
};

struct P2GroinkAim {
    bool valid = false;
    bool locked = false;
    float angle = 0.0f;
    float targetAngle = 0.0f;
    float shellSpeed = 0.0f;
};

struct P2GroinkShell {
    bool active = false;
    bool primary = true; // Source marks the first of its spread as the primary shell.
    P2GroinkVec3 position;
    P2GroinkVec3 velocity;
};

struct P2GroinkTraceResult {
    P2GroinkVec3 position;
    P2GroinkVec3 velocity;
    bool floor = false;
    bool wall = false;
    // Source calls getMinY after either collision, then raises a shell that is
    // below ground+20 to ground+10. A collision result must provide this.
    float groundY = 0.0f;
    bool hasGroundY = false;
};

enum class P2GroinkTerminalReason { None, Floor, Wall, OutOfRange, Invalid };

// Stored before recycling so a later host can feed the source-compatible
// y-10 sweep to damage receivers without changing this movement milestone.
struct P2GroinkTerminalStep {
    bool valid = false;
    P2GroinkTerminalReason reason = P2GroinkTerminalReason::None;
    P2GroinkVec3 start;
    P2GroinkVec3 end;
};

// Mirrors MiniHoudaiShotGunMgr::rotateVertical: normalize the local head basis,
// right-concatenate local Rz(angle), then restore each original axis scale.
// Hosts should pass this rotated `kuti` basis to emit rather than substituting
// a guessed world-space pitch. All three basis columns must be supplied.
P2GroinkMuzzle p2_groink_rotate_vertical(const P2GroinkMuzzle& muzzle, float angle,
                                          bool& valid);

// Called once per 30 Hz source update with the radius-10 move sphere. Return
// true only after filling position and velocity, mirroring traceMove's mutable
// MoveInfo velocity. On floor/wall it must also set finite groundY/hasGroundY
// for the source getMinY then ground+10 correction. Return false only when no
// trace was performed; straight integration then has no invented collision.
typedef bool (*P2GroinkTraceFn)(void* context, const P2GroinkVec3& position,
                                const P2GroinkVec3& velocity, float delta,
                                float radius, P2GroinkTraceResult& result);

class P2GroinkPolicy {
public:
    static constexpr float kSourceDelta = 1.0f / 30.0f;
    static constexpr float kShellRadius = 10.0f;

    // Mirrors MiniHoudaiShotGunMgr::searchShotGunRotation. `angle` is the
    // current vertical rotation in radians and is advanced by at most 0.1.
    static P2GroinkAim aim(const P2GroinkVec3& muzzlePosition,
                            const P2GroinkVec3& targetPosition,
                            float searchDistance, float attackRadius,
                            float delta, float angle);

    // One-shell policy: an active shell blocks another emission. Spread values
    // are source randWeightFloat(0.2) inputs in [0, 1], one per world axis.
    bool emit(const P2GroinkMuzzle& muzzle, float shellSpeed,
              const P2GroinkVec3& spreadUnit);

    // Mirrors MiniHoudaiShotGunNode::update: trace radius 10, then subtract 20
    // velocity-y per source update. Recycles on traced floor/wall or an owner
    // axis separation above 1000. Damage receivers are intentionally deferred.
    bool update(const P2GroinkVec3& ownerPosition, float delta,
                P2GroinkTraceFn trace, void* traceContext);

    const P2GroinkShell& shell() const { return mShell; }
    const P2GroinkTerminalStep& lastTerminalStep() const { return mLastTerminalStep; }
    void clearTerminalStep() { mLastTerminalStep = P2GroinkTerminalStep{}; }
    void recycle() { mShell = P2GroinkShell{}; }

private:
    P2GroinkShell mShell;
    P2GroinkTerminalStep mLastTerminalStep;
};
