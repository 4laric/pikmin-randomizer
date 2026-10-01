#pragma once
// Engine-free Otakara (Dweevil 59-62, 93) collision-part policy (#884 follow-up, Dweevil family).
//
// Owner playtest 2026-09-30: "i think the p2 ones you can't hurt from the ground. like their
// legs are invincible and you have to throw at its body". Checked against the decomp:
//
//   * The shared Otakara collision tree (disc otakara/enemycoll.txt, staged as
//     <species>/enemycoll.txt) has exactly two spheres, both on joint 11 ("otakara", the body
//     joint, model y 35-39 above the feet in wait1/move1):
//         {none} code {____} radius 15     root / bounding sphere, not stickable, takes no hit
//         {body} code {st__} radius 10     the ONLY stickable, damageable part
//     There is no sphere on any of the eight leg joints (back_leg1L..front_leg2R), so the legs
//     are not targets at all: nothing can stick to them and nothing is damaged through them.
//   * OtakaraBase::Obj::damageCallBack (OtakaraBase.cpp:190-197) damages only `if (collpart)`
//     and returns false for a partless hit. A Pikmin's latched attack carries the part it is
//     stuck to (Pikmin2 ActStickAttack, aiAttack.cpp:88-90); a ground punch carries none.
//   * CollPart::isStickable() is mSpecialID.match('s***') (collinfo.cpp:806-808) and
//     PikiFlyingState::collisionCallback (pikiState.cpp:2336) and ActAttack::collisionCallback
//     (aiAttack.cpp:286-290) latch only onto a stickable part.
//   * The P1 mirror of the two attack forms is src/plugPikiKando/aiAttack.cpp:688/707 (ground
//     punch: InteractAttack(piki, nullptr, ...)) versus :740/762 (latched:
//     InteractAttack(piki, getStickPart(), ...)); Navi::punch uses nullptr too (navi.cpp:1879,
//     naviState.cpp:3252).
//
// Owner claim verdict: CONFIRMED for the legs and for every partless (ground) hit, with one
// precision: the source does not say "from the ground", it says "through a part". A Pikmin
// that jumps or is thrown and latches onto the body sphere damages it exactly like any other
// latched Pikmin; the body sphere's lowest point sits ~27 above the feet, so in practice that
// means thrown Pikmin. Bombs and the Volatile blast reach damageTreasure partless
// (bombCallBack, OtakaraBase.cpp:232-238) and are not gated.
//
// Port mapping: the actor's P1 host CollInfo is swapped for this two-sphere tree (P2FlyerColl,
// the #960 mechanism) and InteractAttack::actTeki refuses the partless Pikmin/Navi forms for a
// registered Otakara (verdict() below), logging P2_OTAKARA_PART either way.
#include "pc_p2_flyer.h"

namespace p2otakarapart {

constexpr int kSphereCount = 2;

// Pre-order retail tree. Offsets are body-joint local; the body joint is placed by
// bodyHeight() above the actor's feet.
inline const p2flyer::Sphere* spheres() {
    static const p2flyer::Sphere kTree[kSphereCount] = {
        {"none", "____", 15.0f, {0.0f, 0.0f, 0.0f}, -1},
        {"body", "st__", 10.0f, {0.0f, 0.0f, 0.0f}, 0},
    };
    return kTree;
}

constexpr int kBodySphere = 1;

// Joint 11 ("otakara") height above the feet, sampled from the disc bca clips against the disc
// model's joint hierarchy (12 uniform samples per clip over the clip's source frames; linear in
// phase). wait1 35.9-36.9, move1/pivot1 36.6-38.6, attack1 crouches to 22.3 at frame ~40; the
// carrying set sits lower (wait2 8.2-24.1, takeitem bends to 5.7). A stuck Pikmin rides the
// sphere, so the port follows the clip instead of a fixed height.
constexpr int kHeightSamples = 12;
struct HeightClip {
    const char* clip;
    float y[kHeightSamples];
};
inline const HeightClip* heightClips(int* count) {
    static const HeightClip kClips[] = {
        {"wait1", {36.6f, 36.2f, 35.9f, 36.3f, 36.9f, 36.1f, 36.2f, 36.9f, 36.2f, 36.0f, 36.3f, 36.5f}},
        {"move1", {36.6f, 36.6f, 36.6f, 37.0f, 38.3f, 37.0f, 37.1f, 38.6f, 37.1f, 36.6f, 36.6f, 36.6f}},
        {"pivot1", {36.6f, 36.6f, 36.6f, 37.0f, 38.3f, 37.0f, 37.1f, 38.6f, 37.1f, 36.6f, 36.6f, 36.6f}},
        {"attack1", {36.6f, 31.6f, 34.9f, 34.9f, 38.2f, 36.7f, 37.3f, 27.4f, 22.3f, 23.2f, 37.8f, 37.5f}},
        {"takeitem", {36.6f, 27.1f, 18.6f, 10.4f, 5.7f, 11.0f, 18.2f, 30.4f, 36.4f, 29.7f, 28.1f, 24.8f}},
        {"wait2", {24.1f, 18.3f, 11.8f, 8.6f, 8.2f, 8.5f, 8.6f, 8.7f, 8.7f, 11.3f, 18.1f, 23.7f}},
        {"move2", {24.1f, 23.7f, 23.4f, 23.8f, 25.1f, 23.8f, 23.9f, 25.4f, 23.9f, 23.4f, 23.7f, 24.0f}},
        {"pivot2", {24.1f, 23.7f, 23.3f, 23.7f, 25.0f, 23.7f, 23.8f, 25.2f, 23.8f, 23.3f, 23.7f, 24.0f}},
        {"attack2", {24.1f, 31.3f, 39.0f, 39.9f, 43.7f, 39.0f, 40.5f, 30.5f, 24.7f, 24.1f, 33.1f, 29.7f}},
        {"dropitem2", {28.8f, 39.9f, 42.2f, 28.3f, 17.2f, 16.5f, 19.2f, 22.3f, 25.9f, 30.9f, 34.4f, 36.4f}},
        {"carry", {4.8f, 5.1f, 5.3f, 4.8f, 4.8f, 4.8f, 4.8f, 4.8f, 4.8f, 5.1f, 5.3f, 4.9f}},
    };
    *count = int(sizeof(kClips) / sizeof(kClips[0]));
    return kClips;
}

inline bool sameName(const char* a, const char* b) {
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}

// Body-joint height for `clip` at `phase` (0..1). Unknown clips (dead, none) use the standing
// height.
inline float bodyHeight(const char* clip, float phase) {
    int count = 0;
    const HeightClip* clips = heightClips(&count);
    for (int c = 0; c < count; ++c) {
        if (!clip || !sameName(clips[c].clip, clip)) continue;
        float p = phase < 0.0f ? 0.0f : (phase > 1.0f ? 1.0f : phase);
        const float pos = p * float(kHeightSamples - 1);
        int i = int(pos);
        if (i >= kHeightSamples - 1) return clips[c].y[kHeightSamples - 1];
        const float t = pos - float(i);
        return clips[c].y[i] + (clips[c].y[i + 1] - clips[c].y[i]) * t;
    }
    return 36.6f;
}

// CollPart::isStickable(): first code character is 's' (collinfo.cpp:806-808).
inline bool stickable(const char* code) { return code && code[0] == 's'; }
// The second code character 't' marks a part that takes damage (aiAttack.cpp:428 targets
// '*t**').
inline bool damageable(const char* code) { return code && code[1] == 't'; }

enum class Form { GroundPunch, LatchedAttack };

struct Verdict {
    bool accept;
    const char* reason;
};

// OtakaraBase::Obj::damageCallBack (OtakaraBase.cpp:190-197): accepted iff a collision part
// came with the hit. Only Pikmin/Navi InteractAttack comes through here; bombs, fire and
// hipdrop take their own source callbacks.
inline Verdict verdict(bool partPresent) {
    return partPresent ? Verdict{true, "part"} : Verdict{false, "partless_refused"};
}

// Host mapping of the two P1 attack forms (aiAttack.cpp:688/707 vs :740/762).
inline Form formOf(bool partPresent) { return partPresent ? Form::LatchedAttack : Form::GroundPunch; }

// Lowest point a latching Pikmin must reach (the body sphere's bottom): used by logs/tests.
inline float stickBottom(float bodyY) {
    const p2flyer::Sphere* t = spheres();
    return bodyY + t[kBodySphere].offset.y - t[kBodySphere].radius;
}

} // namespace p2otakarapart
