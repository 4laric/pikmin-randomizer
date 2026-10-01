#pragma once
// Skitter Leaf (Sokkuri, EnemyID 79) shake-off policy. Pure functions so the
// trigger is unit-testable without the engine (#996).
//
// Source: SokkuriState.cpp (Appear/Wait/MoveGround/MoveWater all start Flick on
// EnemyFunc::isStartFlick(sokkuri, false)); EnemyFunc::isStartFlick
// (enemyAction.cpp:1209); EnemyBase::addDamage (enemyBase.cpp:2762, every
// accepted damage callback adds flickSpeed 1.0 to mFlickTimer); StateFlick::exec
// KEYEVENT_3 zeroes mFlickTimer after the shake.
//
// Retail parms (enemyparm.txt, GPVE01 rev 0): ip01..ip07 = 2,0,2,0,2,0,2, i.e.
// every stuck-count tier threshold is 0 and every blow threshold is 2. No stuck
// count is below 0, so the last tier always decides: the shake starts once
// (int)(flickTimer + 0.5) > 2, which is the third damaging hit. Nothing else
// starts it: no proximity test, no timer, no stuck-count floor.
namespace p2sokkuriflick {

constexpr int ShakeOffBlowA = 2;     // ip01
constexpr int ShakeOffSticking1 = 0; // ip02
constexpr int ShakeOffBlowB = 2;     // ip03
constexpr int ShakeOffSticking2 = 0; // ip04
constexpr int ShakeOffBlowC = 2;     // ip05
constexpr int ShakeOffSticking3 = 0; // ip06
constexpr int ShakeOffBlowD = 2;     // ip07
constexpr float FlickPerHit = 1.0f;  // EnemyBase::damageCallBack addDamage(damage, 1.0f)

// Shake parms (fp16..fp19): chance for stuck Pikmin, knockback, damage, range.
constexpr float ShakeChance = 1.0f;     // fp16
constexpr float ShakeKnockback = 50.0f; // fp17
constexpr float ShakeDamage = 1.0f;     // fp18 (captains only; see PikiDamage)
constexpr float ShakeRange = 40.0f;     // fp19
// InteractFlick::actPiki (interactPiki.cpp:610) never reads the damage argument:
// a flicked Pikmin is only blown away. The Skitter Leaf has no attack state
// (fp20..fp24 attack parms are all 0), so it cannot kill a Pikmin.
constexpr float PikiDamage = 0.0f;

// EnemyFunc::isStartFlick without the reset side effect (Sokkuri passes false;
// the timer is cleared by the shake itself at KEYEVENT_3).
inline bool isStartFlick(float flickTimer, int stuckPikmin) {
    const float v = flickTimer >= 0.0f ? flickTimer + 0.5f : flickTimer - 0.5f;
    const int flickInt = static_cast<unsigned char>(static_cast<int>(v));
    if (stuckPikmin < ShakeOffSticking1) return flickInt > ShakeOffBlowA;
    if (stuckPikmin < ShakeOffSticking2) return flickInt > ShakeOffBlowB;
    if (stuckPikmin < ShakeOffSticking3) return flickInt > ShakeOffBlowC;
    return flickInt > ShakeOffBlowD;
}

// Number of accepted hits that arm the shake from a zeroed timer.
inline int hitsToShake() {
    int hits = 0;
    float t = 0.0f;
    while (!isStartFlick(t, 0) && hits < 255) {
        t += FlickPerHit;
        ++hits;
    }
    return hits;
}

// Carcass visual: Obj::startCarcassMotion plays SOKKURIANIM_Carry ('type5',
// 40 frames, looping) for the whole time the corpse exists, lying or carried.
inline const char* carcassClip() { return "type5"; }
inline float carcassPhase(double elapsedSeconds, float clipSeconds) {
    if (!(clipSeconds > 0.0f) || elapsedSeconds < 0.0) return 0.0f;
    const double cycles = elapsedSeconds / clipSeconds;
    return static_cast<float>(cycles - static_cast<long long>(cycles));
}

} // namespace p2sokkuriflick
