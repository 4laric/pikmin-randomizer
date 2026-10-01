#pragma once
// Emperor Bulblax (KingChappy, enemy 53) life-cycle rules for the own-identity
// Chappy family FSM (pc_p2_chappy.cpp, FAMILY_KING): the buried spawn
// (HideWait), proximity Appear with its shake-off, Hide (dive), bomb
// ingestion (Attack -> Eat -> Damage stun), the cross-Emperor manager request
// and the tongue-tip trace. Engine-free so tools/p2_king_life_test.cpp compiles
// the same decisions the runtime uses.
//
// Source of truth (read-only decomp `native/pikmin2-research`):
//   src/plugProjectMorimuraU/kingChappy.cpp        onInit :88-160 (starts in HideWait),
//       eatBomb :1009-1043, getPikminInMouth :1056-1087, getTonguePosVel :1089-1101,
//       forceTransit :1548-1574, checkAttack :1778-1822, bombCallBack :875-880
//   src/plugProjectMorimuraU/kingChappyState.cpp   StateAttack :133-743, StateDamage :1706-1775,
//       StateEat :1839-1875, StateHide :1881-1945, StateHideWait :1954-2015,
//       StateAppear :2032-2121, StateCaution :2124-2157, StateWarCry :1588-1690
//   src/plugProjectMorimuraU/kingChappyMgr.cpp     Mgr::requestState :53-66
//   src/plugProjectYamashitaU/enemyAction.cpp      isThereOlimar / isTherePikmin (3D, strict <)
//   src/plugProjectMorimuraU/bomb.cpp              Obj::canEat (:455, BOMB_Wait only)
// Retail values (disc): see pc_p2_king_policy.h (fp02 60, ip02 0, ip03 180).
//
// Animation key numbering: enemyanimmgr.txt lists `frame type` pairs and the
// source names them KEYEVENT_<type>: damage 15:4 is KEYEVENT_4 (kill the mouth
// contents and apply the bomb damage), 60:6 is KEYEVENT_6 (start the stun
// timer), 65:0/94:1 are the loop bounds. (pc_p2_king_policy.h DamageKillKey = 46
// numbered the list by position and is not used here.)
//
// Determinism: pure functions of their arguments; no clock, no RNG.
#include "pc_p2_king_policy.h"
#include "pc_p2_king_tables.h"

#include <cmath>
#include <cstring>

namespace p2kinglife {

// Port state ids are the source StateID order (p2king::State).
using p2king::Appear;
using p2king::Attack;
using p2king::Caution;
using p2king::Damage;
using p2king::Dead;
using p2king::Eat;
using p2king::Flick;
using p2king::Hide;
using p2king::HideWait;
using p2king::Swallow;
using p2king::Turn;
using p2king::Walk;
using p2king::WarCry;

// ---- clips ------------------------------------------------------------------
// KingChappy AnimID -> bank clip stem (KingChappy.h:319-333).
inline const char* clipStem(int state)
{
    switch (state) {
    case Walk: return "move1";
    case Attack: return "attack";
    case Dead: return "dead";
    case Flick: return "flick";
    case WarCry: return "cry";
    case Damage: return "damage";
    case Turn: return "waitact1";
    case Eat: return "type2";
    case Hide: return "dive";
    case HideWait: return "wait2";
    case Appear: return "type3";
    case Caution: return "waitact2";
    case Swallow: return "type1";
    default: return "wait2";
    }
}

struct Loop {
    int start, end; // enemyanimmgr.txt loop-start (type 0) / loop-end (type 1)
};
// Clip loop bounds: 0 == no loop. The animator wraps end -> start until
// finishMotion; a clip without bounds plays once.
inline Loop loopFor(const char* stem)
{
    if (!std::strcmp(stem, "move1")) return {15, 54};
    if (!std::strcmp(stem, "wait2")) return {0, 39};
    if (!std::strcmp(stem, "waitact1")) return {10, 33};
    if (!std::strcmp(stem, "damage")) return {65, 94};
    return {0, 0};
}

// Frame shown after `frames` elapsed source frames on a clip of `duration`
// frames. `finish` is true once finishMotion() was requested: the loop then
// plays through to the clip end.
inline float clipFrame(const char* stem, float frames, int duration, bool finish)
{
    const Loop l = loopFor(stem);
    if (l.end > l.start && !finish && frames >= float(l.end)) {
        const float span = float(l.end - l.start);
        return float(l.start) + std::fmod(frames - float(l.start), span);
    }
    const float last = float(duration > 1 ? duration - 1 : 1);
    return frames < last ? frames : last;
}

// ---- burrow ---------------------------------------------------------------
// Hide.init hardConstraintOn .. Appear END hardConstraintOff: isUnderground()
// == isConstrained(), so nothing targets or damages the Emperor meanwhile.
inline bool underground(int state) { return state == Hide || state == HideWait || state == Appear; }
// EB_LifegaugeVisible is disabled by HideWait.init and re-enabled by Appear END.
inline bool lifeGaugeHidden(int state) { return state == HideWait || state == Appear; }

constexpr float WakeRange = p2king::DistanceToSpawn; // fp02 disc 60 (header 150)
constexpr int WakeDelayFrames = p2king::TimeToAppearance; // ip02 disc 0 (header 200)

struct WakeInputs {
    bool doCheckAppear = true;  // Obj::mDoCheckAppear (true at onInit, false after the first Appear)
    int framesInState = 0;      // StateHideWait::mCanCheckAppearTimer (incremented before the test)
    bool naviInRange = false;   // isThereOlimar(range): any captain, 3D distance < range
    bool pikminInRange = false; // isTherePikmin(range): any searchable Pikmin, 3D distance < range
};
// StateHideWait::exec: the proximity test only runs while mDoCheckAppear is set
// or the timer passed mTimeToAppearance.
inline bool wakeCheckRuns(const WakeInputs& in) { return in.doCheckAppear || in.framesInState > WakeDelayFrames; }
inline bool hideWaitWakes(const WakeInputs& in)
{
    return wakeCheckRuns(in) && (in.naviInRange || in.pikminInRange);
}
// Wake radius: fp02 * mScaleModifier; `override` > 0 replaces it (dev/smoke).
inline float wakeRadius(float scale, float override = 0.0f) { return override > 0.0f ? override : WakeRange * scale; }
// Strict squared-distance test used by isThereOlimar / isTherePikmin.
inline bool within(float dx, float dy, float dz, float radius) { return dx * dx + dy * dy + dz * dz < radius * radius; }

// Clip event frames used by the burrow cycle (enemyanimmgr.txt type3 / dive).
constexpr int AppearShakeFrame = p2king::AppearShakeOffKey; // type3 55:3
constexpr int AppearBounceFrame = 58;                        // type3 58:4
constexpr int DiveEffectFrame = 58;                          // dive 58:2 (effect + PSSE_EN_KING_APPEAR)
constexpr int DiveFadeFrame = 90;                            // dive 90:4
constexpr int WarCryRequestFrame = p2king::CryCrossEmperorKey; // cry 38:3

// True when the event at `key` was crossed advancing the clip from `prev` to `now`.
inline bool crossed(float prev, float now, int key) { return prev < float(key) && now >= float(key); }

// ---- cross-Emperor manager request ---------------------------------------
struct Peer {
    int state = Dead;
    bool alive = false;
    float flickTimer = 0.0f;
};
// Obj::forceTransit: Appear only from HideWait; WarCry only from Walk with a
// running flick timer.
inline bool forceAccepts(const Peer& p, int stateId)
{
    if (stateId == Appear) return p.state == HideWait;
    if (stateId == WarCry) return p.state == Walk && p.flickTimer > 0.0f;
    return false;
}
// Mgr::requestState: the first other live, non-Dead Emperor whose state differs
// and that accepts the forced transit; -1 if none. `peers` must be in a stable
// (manager) order.
inline int requestState(const Peer* peers, int count, int self, int stateId)
{
    for (int i = 0; i < count; ++i) {
        const Peer& p = peers[i];
        if (i == self || !p.alive || p.state == stateId || p.state == Dead) continue;
        if (forceAccepts(p, stateId)) return i;
    }
    return -1;
}

// ---- bombs ------------------------------------------------------------------
// P2 BOMB_Wait is a bomb that has not gone off yet (dormant, or already ticking
// its fuse). The P1 bomb rock states that match are BombAI::BOMB_Unk0 (dormant,
// lying on the ground) and BOMB_Set (fuse lit, on the ground); BOMB_Unk1 is the
// throw in flight, BOMB_Bomb the blast, BOMB_Mizu/BOMB_Die the end. A bomb a
// Pikmin holds is never eaten. pc_p2_chappy.cpp static_asserts both values
// against BombAI.
constexpr int BombDormantState = 0;
constexpr int BombLitState = 2;
inline bool bombEatable(int aiState, bool grabbed)
{
    return (aiState == BombDormantState || aiState == BombLitState) && !grabbed;
}
// External blast (Obj::bombCallBack): EnemyBase::bombCallBack(.., 0.25f * damage).
inline float externalBlastDamage(float damage) { return p2king::ExternalBlastFactor * damage; }

// Attack.exec runs eatBomb() then eatPikmin() every frame from KEYEVENT_3.
constexpr int EatWindowStart = p2king::AttackArmKey;

// ---- damage (bomb stun) ---------------------------------------------------
constexpr int DamageDuration = 135;
constexpr int DamageKillFrame = 15;   // damage 15:4
constexpr int DamageStunFrame = 60;   // damage 60:6
constexpr int DamageLoopStart = 65;   // damage 65:0
constexpr int DamageLoopEnd = 94;     // damage 94:1
enum DamageEvent : int { DEvNone = 0, DEvKill = 1, DEvStun = 2, DEvEnd = 4 };

struct DamageClock {
    int frame = 0;         // animator frame (integer source frames)
    int stun = 0;          // StateDamage::mStunTimer
    bool finished = false; // finishMotion() requested
    bool killed = false;
};
// One source frame of StateDamage. Returns the DamageEvent bits crossed.
inline int damageStep(DamageClock& c, int stunFrames = p2king::BombDamageTime)
{
    int ev = DEvNone;
    if (c.stun > 0) {
        ++c.stun;
        if (c.stun > stunFrames) c.finished = true;
    }
    ++c.frame;
    if (!c.finished && c.frame >= DamageLoopEnd) c.frame = DamageLoopStart + (c.frame - DamageLoopEnd);
    if (!c.killed && c.frame >= DamageKillFrame) {
        c.killed = true;
        ev |= DEvKill;
    }
    if (c.stun == 0 && c.frame >= DamageStunFrame) {
        c.stun = 1;
        ev |= DEvStun;
    }
    if (c.frame >= DamageDuration - 1) ev |= DEvEnd;
    return ev;
}
// Damage applied at KEYEVENT_4: bombs in the mouth times fp05.
inline float mouthBombDamage(int bombsInMouth) { return p2king::bombDamage(bombsInMouth); }

// ---- tongue trace -----------------------------------------------------------
struct Tongue {
    float tip[3];  // bero6, model space
    float dir[3];  // normalise(bero6 - bero5)
};
inline Tongue tongueAt(int frame)
{
    if (frame < 0) frame = 0;
    if (frame >= p2kingtables::kTongueFrames) frame = p2kingtables::kTongueFrames - 1;
    const float* r = p2kingtables::kTongue[frame];
    Tongue t{{r[0], r[1], r[2]}, {r[0] - r[3], r[1] - r[4], r[2] - r[5]}};
    const float len = std::sqrt(t.dir[0] * t.dir[0] + t.dir[1] * t.dir[1] + t.dir[2] * t.dir[2]);
    if (len > 1e-6f) {
        t.dir[0] /= len;
        t.dir[1] /= len;
        t.dir[2] /= len;
    }
    return t;
}
constexpr float TongueSphereRadius = p2king::TongueTipRadius; // Sys::Sphere(tonguePos + (0,5,0), 5)
constexpr float TongueSphereLift = 5.0f;

// StateAttack routing after the lick ends (window end or terrain contact):
// bombs eaten -> Eat with stun; Pikmin eaten -> Swallow; else Walk.
inline int attackExit(int eatenBombs, int eatenPikmin) { return p2king::attackEnd(eatenBombs, eatenPikmin); }
// StateEat.exec at END: stun after a bomb meal, else Swallow.
inline int eatExit(bool doStunAfter) { return doStunAfter ? int(Damage) : int(Swallow); }

// ---- boss-scale collision -----------------------------------------------------
// The retail kingchappy/enemycoll.txt tree posed through each clip
// (scripts/p2_king_tables.py): root 'none' r80 plus back/ketu/asiL/asiR (touch),
// head/hana/kuti (stickable). Only the stickable parts take Pikmin: damageCallBack
// wants a stuck attacker with a collision part (kingChappy.cpp:824-848).
constexpr int CollNodeCount = p2kingtables::kCollNodeCount;
constexpr int CollSamples = p2kingtables::kCollSamples;

inline int collClipIndex(const char* stem)
{
    for (int i = 0; i < p2kingtables::kCollClipCount; ++i)
        if (!std::strcmp(p2kingtables::kCollClips[i].stem, stem)) return i;
    return -1;
}

// Sample position along a clip: samples sit at i * (frames - 1) / (CollSamples - 1).
inline void collLocate(int clip, float frame, int& i0, float& f)
{
    const float last = float(p2kingtables::kCollClips[clip].frames > 1 ? p2kingtables::kCollClips[clip].frames - 1 : 1);
    float u = frame <= 0.0f ? 0.0f : (frame >= last ? 1.0f : frame / last);
    const float t = u * float(CollSamples - 1);
    i0 = int(t);
    if (i0 >= CollSamples - 1) i0 = CollSamples - 2;
    f = t - float(i0);
}

// Model-space centre of collision node `node` (retail node order) at clip frame `frame`.
inline bool collCentre(int clip, float frame, int node, float out[3])
{
    if (clip < 0 || clip >= p2kingtables::kCollClipCount || node < 0 || node >= CollNodeCount) return false;
    int i0 = 0;
    float f = 0.0f;
    collLocate(clip, frame, i0, f);
    const float* a = p2kingtables::kCollClips[clip].centre[i0][node];
    const float* b = p2kingtables::kCollClips[clip].centre[i0 + 1][node];
    for (int k = 0; k < 3; ++k) out[k] = a[k] + (b[k] - a[k]) * f;
    return true;
}

// Model-space kuti joint (the mouth) at clip frame `frame`: where the swallow slots sit outside
// the attack window (inside it the exact kamu1..9 rows of pc_p2_chappy_mouth.h apply).
inline bool collMouth(int clip, float frame, float out[3])
{
    if (clip < 0 || clip >= p2kingtables::kCollClipCount) return false;
    int i0 = 0;
    float f = 0.0f;
    collLocate(clip, frame, i0, f);
    const float* a = p2kingtables::kCollClips[clip].mouth[i0];
    const float* b = p2kingtables::kCollClips[clip].mouth[i0 + 1];
    for (int k = 0; k < 3; ++k) out[k] = a[k] + (b[k] - a[k]) * f;
    return true;
}

} // namespace p2kinglife
