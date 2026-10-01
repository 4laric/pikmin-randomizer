#pragma once
// Engine-free DangoMushi (94, Segmented Crawbster) boss-loop policy (#897).
//
// Pure decisions shared by the native FSM (pc_p2_dangomushi.cpp) and the
// engine-free regression tools/p2_dangomushi_policy_test.cpp. Every rule cites
// the decomp (native/pikmin2-research, src/plugProjectNishimuraU):
//
//   * wallCrash      -- Obj::wallCallback (DangoMushi.cpp:260-274): while
//                       rolling, |rollVel| > 100 and dot(rollVel/|rollVel|, n)
//                       < -0.5 transits to StateTurn. It is the ONLY Turn entry.
//   * rollExit       -- StateAttack::exec (DangoMushiState.cpp:414): 15 s -> Wait.
//                       There is no territory/home-distance exit in the source.
//   * PressCrush     -- Obj::collisionCallback (DangoMushi.cpp:236-256): every
//                       frame while mIsRolling, every touched creature standing
//                       on a floor triangle receives InteractPress(attackDamage).
//   * turnClock      -- StateTurn::exec (DangoMushiState.cpp:510-551) on the
//                       disc turn.bca key stream 10:2,32:0(LOOP_START),
//                       81:1(LOOP_END),108:3,114:4, 117 frames. The clip loops
//                       32..81 until mStateTimer > fp10 FLIP_TIME (7.5 s) calls
//                       finishMotion; the loop then runs out to LOOP_END and the
//                       tail plays 81 -> END. LOOP_START clears EB_Invulnerable
//                       (body stickable), key 3 re-arms it and shakes stickers
//                       (setBodyCollision(true), DangoMushi.cpp:795-834).
//   * shakeReaction / flickReaction -- setBodyCollision(true) and
//                       Obj::flickHandCollision(Creature*) (DangoMushi.cpp:838):
//                       Purple Pikmin get InteractFlick(fp17 shakeKnockback,
//                       fp18 shakeDamage); other Pikmin get InteractHanaChirashi
//                       (blown + wither to Leaf); a Navi hit by the hand gets
//                       the InteractWind::actNavi flick (flat 300 push) with
//                       fp24 attackDamage.
//   * armWindow      -- StateFlick::exec: attack_2 KEYEVENT_2 sets
//                       mIsArmSwinging, KEYEVENT_3 clears it (26:2,32:3,38:2,
//                       50:3,57:2,65:3).
#include <cmath>
#include <cstdint>
#include <cstring>
#include <map>

namespace p2dango {

// ------------------------------------------------------------ clip per state
// Source AnimID (DangoMushi.h:210-220) each state starts:
//   StateStay    startBlendAnimation(Fly) then stopMotion() with the model
//                hidden (DangoMushiState.cpp:92-105): the fall clip is FROZEN,
//                never looped. The port has no hidden-model step, so Stay shows
//                the idle Wait clip instead of the entrance.
//   StateAppear  Fly, played once to KEYEVENT_END (:153-168, :192).
//   StateWait    Wait   StateMove Move   StateAttack Attack   StateTurn Turn
//   StateRecover Recover  StateFlick Attack2 (attack_2.bca)  StateDead Dead
// Carry (DANGOANIM_Carry, Obj::startCarcassMotion) is the carcass clip.
inline const char* stateClip(const char* state) {
    static const char* const table[][2] = {
        {"stay", "wait"},   {"appear", "fly"},    {"wait", "wait"},
        {"move", "move"},   {"attack", "attack"}, {"turn", "turn"},
        {"recover", "recover"}, {"flick", "attack_2"}, {"dead", "dead"},
    };
    for (const auto& row : table)
        if (state && std::strcmp(row[0], state) == 0) return row[1];
    return nullptr;
}
// Only Wait and Move are free-running loops. Fly (entrance), attack, turn,
// recover, attack_2 and dead are one-shot or state-clocked. Looping Fly made a
// Stay Crawbster fall in from above forever.
inline bool clipLoops(const char* clip) {
    return clip && (std::strcmp(clip, "wait") == 0 || std::strcmp(clip, "move") == 0);
}

constexpr float kWallCrashSpeed = 100.0f;   // DangoMushi.cpp:266
constexpr float kWallCrashDot = -0.5f;      // DangoMushi.cpp:266
constexpr float kAttackTimeout = 15.0f;     // DangoMushiState.cpp:414
constexpr float kFlipTime = 7.5f;           // proper fp10 (DangoMushi.h:49)
constexpr int kTurnLoopStart = 32;          // turn.bca 32:0
constexpr int kTurnLoopEnd = 81;            // turn.bca 81:1
constexpr int kTurnKey3 = 108;              // turn.bca 108:3
constexpr int kTurnClipFrames = 117;        // staged bank row `turn 117`
constexpr int kAttackLoopStart = 50;        // attack.bca 50:0
constexpr int kAttackLoopEnd = 100;         // attack.bca 100:1
constexpr float kAttackDamage = 10.0f;      // general fp24
constexpr float kShakeKnockback = 200.0f;   // general fp17
constexpr float kShakeDamage = 1.0f;        // general fp18
constexpr float kFps = 30.0f;
constexpr float kNaviFlickPush = 300.0f;    // DangoMushi.cpp:845 targetPos *= 300

// ---------------------------------------------------------------- roll/wall
inline bool wallCrash(bool rolling, float vx, float vy, float vz,
                      float nx, float ny, float nz) {
    if (!rolling) return false;
    const float speed = std::sqrt(vx * vx + vy * vy + vz * vz);
    if (!(speed > kWallCrashSpeed)) return false;
    const float dot = (vx * nx + vy * ny + vz * nz) / speed;
    return dot < kWallCrashDot;
}

enum class RollExit { Stay, Turn, Wait };
// The Attack state's per-tick exit. `homeDistance` is accepted only so the
// regression can prove it is ignored (the old port exited at territory 150).
inline RollExit rollExit(float stateTime, bool wallCrashed, float homeDistance) {
    (void)homeDistance;
    if (wallCrashed) return RollExit::Turn;
    if (stateTime > kAttackTimeout) return RollExit::Wait;
    return RollExit::Stay;
}

// ---------------------------------------------------------------- press crush
struct PressCandidate {
    std::uint64_t token = 0;
    float dx = 0.0f, dz = 0.0f;  // offset from the rolling body (XZ)
    bool grounded = false;       // source evt.mCollidingCreature->mFloorTriangle
    float reach = 0.0f;          // target collision size added to the body radius
    bool alive = true;
};

// Per-frame multi-target crush with a per-target cooldown so the log and the
// P1 receivers are not spammed (P1 InteractPress already ignores a Pikmin in
// PIKISTATE_Pressed and a damaged Navi).
class PressCrush {
public:
    explicit PressCrush(float radius = 100.0f, float cooldown = 0.5f)
        : mRadius(radius), mCooldown(cooldown) {}
    void reset() { mLast.clear(); }
    // Returns true when `c` must be pressed this frame.
    bool shouldPress(const PressCandidate& c, float now) {
        if (!c.alive || !c.grounded) return false;
        const float limit = mRadius + c.reach;
        if (c.dx * c.dx + c.dz * c.dz > limit * limit) return false;
        auto it = mLast.find(c.token);
        if (it != mLast.end() && now - it->second < mCooldown) return false;
        mLast[c.token] = now;
        return true;
    }
private:
    float mRadius;
    float mCooldown;
    std::map<std::uint64_t, float> mLast;
};

// ---------------------------------------------------------------- turn clock
struct TurnClock {
    float frame = 0.0f;     // animation frame of turn.bca to draw
    bool looping = false;   // inside the 32..81 loop section
    bool tail = false;      // post-loop tail 81 -> END is playing
    bool stickable = false; // LOOP_START reached and key 3 not yet reached
    bool closed = false;    // key 3 of the tail reached this or an earlier tick
    bool finished = false;  // END reached: transit to Recover
};

// Deterministic clip clock from the Turn state time. The loop finishes on
// the first LOOP_END crossing at or after FLIP_TIME (finishMotion lets the
// running pass complete).
inline TurnClock turnClock(float stateTime, float flipTime = kFlipTime,
                           int clipFrames = kTurnClipFrames) {
    TurnClock c;
    const float f = stateTime * kFps;
    const float L = float(kTurnLoopEnd - kTurnLoopStart);
    const float flipFrame = flipTime * kFps;
    if (clipFrames <= kTurnKey3) clipFrames = kTurnKey3 + 1;
    const float endFrame = float(clipFrames - 1);
    // First wrap point w_k = LOOP_END + k*L that is >= flipFrame.
    float wrap = float(kTurnLoopEnd);
    if (flipFrame > wrap) wrap += std::ceil((flipFrame - wrap) / L) * L;
    if (f < float(kTurnLoopStart)) {
        c.frame = f;
    } else if (f < wrap) {
        c.looping = true;
        c.frame = float(kTurnLoopStart) + std::fmod(f - float(kTurnLoopStart), L);
    } else {
        c.tail = true;
        c.frame = float(kTurnLoopEnd) + (f - wrap);
        if (c.frame >= endFrame) { c.frame = endFrame; c.finished = true; }
    }
    c.closed = c.tail && c.frame >= float(kTurnKey3);
    c.stickable = f >= float(kTurnLoopStart) && !c.closed;
    return c;
}

// Attack (roll) clip: plays 0..LOOP_END once, then loops LOOP_START..LOOP_END
// while the roll lasts (attack.bca 50:0 / 100:1).
inline float attackFrame(float stateTime) {
    const float f = stateTime * kFps;
    if (f < float(kAttackLoopEnd)) return f;
    const float L = float(kAttackLoopEnd - kAttackLoopStart);
    return float(kAttackLoopStart) + std::fmod(f - float(kAttackLoopEnd), L);
}

// StateAttack::exec (DangoMushiState.cpp:414-466): after 15 s finishMotion()
// lets the running loop pass reach LOOP_END, where mIsRolling/mIsBall clear;
// the tail (uncurl) then plays to END and the state transits to Wait.
constexpr int kAttackClipFrames = 140;      // staged bank row `attack 140`
struct AttackClock {
    float frame = 0.0f;
    bool tail = false;      // loop left: rolling stopped, uncurl playing
    bool finished = false;  // END reached: transit to Wait
};
inline AttackClock attackClock(float stateTime, float finishAt,
                               int clipFrames = kAttackClipFrames) {
    AttackClock c;
    const float f = stateTime * kFps;
    if (f < float(kAttackLoopEnd) || finishAt < 0.0f) {
        c.frame = attackFrame(stateTime);
        return c;
    }
    const float L = float(kAttackLoopEnd - kAttackLoopStart);
    const float finishFrame = finishAt * kFps;
    float wrap = float(kAttackLoopEnd);
    if (finishFrame > wrap) wrap += std::ceil((finishFrame - wrap) / L) * L;
    if (f < wrap) {
        c.frame = float(kAttackLoopStart) + std::fmod(f - float(kAttackLoopEnd), L);
        return c;
    }
    c.tail = true;
    c.frame = float(kAttackLoopEnd) + (f - wrap);
    const float endFrame = float(clipFrames - 1);
    if (c.frame >= endFrame) { c.frame = endFrame; c.finished = true; }
    return c;
}

// Roll-crush damage (see rollCrush in pc_p2_dangomushi.cpp): P2 kills every
// pressed Pikmin (PikiPressedState::exec -> kill), so a Pikmin press carries
// lethal damage on the P1 receiver; a Navi takes the source fp24.
inline float pressDamage(bool piki, float health) {
    if (!piki) return kAttackDamage;
    return health > kAttackDamage ? health : kAttackDamage;
}

// ---------------------------------------------------------------- reactions
enum class TargetKind { Pikmin, PurplePikmin, Navi };
enum class Reaction { None, Flick, Wither, NaviFlick };
struct ReactionOut {
    Reaction kind = Reaction::None;
    float knockback = 0.0f;
    float damage = 0.0f;
    bool leaf = false;  // strip bud/flower to Leaf
};

// setBodyCollision(true) sticker shake (only stuck Pikmin are shaken).
inline ReactionOut shakeReaction(TargetKind k) {
    ReactionOut r;
    if (k == TargetKind::PurplePikmin) {
        r.kind = Reaction::Flick; r.knockback = kShakeKnockback; r.damage = kShakeDamage;
    } else if (k == TargetKind::Pikmin) {
        r.kind = Reaction::Wither; r.knockback = kShakeKnockback; r.damage = 0.0f; r.leaf = true;
    }
    return r;
}

// Obj::flickHandCollision(Creature*): the hand hits captains too.
inline ReactionOut flickReaction(TargetKind k) {
    ReactionOut r;
    if (k == TargetKind::Navi) {
        // InteractHanaChirashi has no actNavi, so the P2 Navi receiver is
        // InteractWind::actNavi: NaviFlickState with the flat 300-unit push
        // (DangoMushi.cpp:842-848) and fp24 damage.
        r.kind = Reaction::NaviFlick; r.knockback = kNaviFlickPush; r.damage = kAttackDamage;
    } else {
        r = shakeReaction(k);
    }
    return r;
}

// Flick angle for a victim at (dx, dz) from the crab. Both the P1 and the P2
// flick receivers push along -(sin a, cos a) (P2 InteractFlick::actPiki,
// P1 PikiFlickState/NaviFlickState), so `a` points from the victim to the crab
// (source JMAAtan2Radian(crab - target), DangoMushi.cpp:852).
inline float flickAngle(float dx, float dz) { return std::atan2(-dx, -dz); }

// attack_2 arm-swing windows (KEYEVENT_2 opens, KEYEVENT_3 closes).
inline bool armWindow(float frame) {
    return (frame >= 26.0f && frame < 32.0f) || (frame >= 38.0f && frame < 50.0f)
        || (frame >= 57.0f && frame < 65.0f);
}

// Port arm reach: the right hand sweeps an arc in front of the body. Without
// the P2 hand_R joint matrix the hand path is a sector of `reach` around the
// facing direction, `halfArc` either side.
inline bool inArmArc(float dx, float dz, float heading, float reach = 170.0f,
                     float halfArc = 1.3962634f /* 80 deg */) {
    const float d2 = dx * dx + dz * dz;
    if (d2 > reach * reach) return false;
    if (d2 < 1e-4f) return true;
    float a = std::atan2(dx, dz) - heading;
    while (a > 3.14159265f) a -= 6.2831853f;
    while (a < -3.14159265f) a += 6.2831853f;
    return std::fabs(a) <= halfArc;
}

} // namespace p2dango
