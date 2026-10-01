// Retail data for the campaign OWN Lesser Spotted Jellyfloat (Kurage, ID 57)
// (wave 3 flyers, #960). Engine-free.
//
// Numbers are the disc's enemy/parm/enemyParms.szs Kurage entry (staged root
// side as Kurage/kurage.json + enemyparm.txt) and Kurage/enemycoll.txt /
// enemyanimmgr.txt / the ANF1 clip lengths of the converted .bca files.
#pragma once

#include "pc_p2_flyer.h"
#include "pc_p2_kurage_fsm.h"
#include "pc_p2_motion_events.h"

namespace p2kurageown {

// EnemyParmsBase (general) values of the retail Kurage entry.
struct General {
    float life = 2500.0f;         // fp00
    float moveSpeed = 50.0f;      // fp06
    float turnSpeed = 0.1f;       // fp08 (fraction of the remaining angle per tick)
    float maxTurnAngle = 5.0f;    // fp28 (degrees per tick)
    float territoryRadius = 300.0f; // fp09
    float homeRadius = 100.0f;    // fp10
    float sightRadius = 300.0f;   // fp12
    float viewAngle = 180.0f;     // fp13 (degrees)
    float shakeChance = 1.0f;     // fp16
    float shakeKnockback = 120.0f;// fp17
    float shakeDamage = 1.0f;     // fp18
    float shakeRange = 25.0f;     // fp19
    float maxAttackRange = 40.0f; // fp20 (isSuck / getSearchedTarget attack range)
    float attackRadius = 40.0f;   // fp22 (suckPikmin radius)
    float attackDamage = 10.0f;   // fp24 (OniKurage flickStickNavi InteractBomb damage)
};

inline General general() { return General{}; }

// Greater Spotted Jellyfloat (OniKurage, ID 72): the retail enemyParms.szs
// onikurage/ entry. Same FSM shape (Variant::Greater), bigger and tougher.
inline General generalGreater()
{
    General g;
    g.life = 4500.0f;
    g.moveSpeed = 75.0f;
    g.territoryRadius = 500.0f;
    g.homeRadius = 100.0f;
    g.sightRadius = 500.0f;
    g.maxAttackRange = 60.0f;
    g.attackRadius = 60.0f;
    return g;
}
inline General general(p2kurage::Variant v)
{
    return v == p2kurage::Variant::Greater ? generalGreater() : general();
}

// Kurage::ProperParms of the retail entry (Kurage.h defaults differ: 90 / 3 /
// 5 / 0.025 / 3 / 10).
inline p2kurage::Parms flightParms()
{
    p2kurage::Parms p;
    p.flightHeight = 70.0f; // fp01
    p.riseFactor = 1.0f;    // fp02
    p.groundTime = 0.5f;    // fp10
    p.suckTime = 2.0f;      // fp11
    p.suckChance = 0.1f;    // fp12
    p.shakeTime = 1.0f;     // fp04
    p.minFallPiki = 6;      // ip01
    p.maxSuckPiki = 10;     // ip11
    return p;
}

// OniKurage ProperParms of the retail entry: flight 75, rise factor 5.0 (the
// Lesser is 1.0), ground 0.5, suck 2.0 @ 0.1, shake 1.0, min fall 6, max suck 20.
inline p2kurage::Parms flightParmsGreater()
{
    p2kurage::Parms p = flightParms();
    p.flightHeight = 75.0f; // fp01
    p.riseFactor = 5.0f;    // fp02
    p.maxSuckPiki = 20;     // ip11
    return p;
}
inline p2kurage::Parms flightParms(p2kurage::Variant v)
{
    return v == p2kurage::Variant::Greater ? flightParmsGreater() : flightParms();
}

// enemy/data/Kurage enemycoll.txt (pre-order). The retail tree is a radius-40
// bounding sphere on joint 3 with three children: two stickable body spheres
// (joint 3 and joint 6) and the 'suck' mouth part (joint 4, attribute 1). Joint
// world matrices are not available for a sampled pose, so the host places the
// tree around the rest-mesh centroid (body offset), like the Demon anchor.
constexpr int kSphereCount = 3;
inline const p2flyer::Sphere* spheres()
{
    static const p2flyer::Sphere kSpheres[kSphereCount] = {
        {"root", "____", 40.0f, {10.0f, 0.0f, 0.0f}, -1},
        {"bod1", "st__", 10.0f, {0.0f, 0.0f, 0.0f}, 0},
        {"bod2", "st__", 25.0f, {-7.5f, 0.0f, 0.0f}, 0},
    };
    return kSpheres;
}

// enemy/data/OniKurage enemycoll.txt: radius-55 bounding sphere @ (20,0,0), two
// stickable bodies (40 @ (-10,0,0) on joint 6, 25 on joint 3) and the radius-25
// 'suck' mouth part (receiver mouth here).
inline const p2flyer::Sphere* spheresGreater()
{
    static const p2flyer::Sphere kSpheres[kSphereCount] = {
        {"root", "____", 55.0f, {20.0f, 0.0f, 0.0f}, -1},
        {"bod1", "st__", 40.0f, {-10.0f, 0.0f, 0.0f}, 0},
        {"bod2", "st__", 25.0f, {0.0f, 0.0f, 0.0f}, 0},
    };
    return kSpheres;
}
inline const p2flyer::Sphere* spheres(p2kurage::Variant v)
{
    return v == p2kurage::Variant::Greater ? spheresGreater() : spheres();
}
// The mouth ('suck') collision part radius: 15 (Kurage), 25 (OniKurage).
inline float mouthRadius(p2kurage::Variant v) { return v == p2kurage::Variant::Greater ? 25.0f : 15.0f; }
// Native pose-file prefix under assets/dataDir/courses/pikmin2room/.
inline const char* posePrefix(p2kurage::Variant v) { return v == p2kurage::Variant::Greater ? "onikurage_" : "kurage_"; }

// Fallback body offset (root -> body joint). Root sits at the bell underside
// (model bounds y -1.5..50.9), the body joints near the middle of the bell.
inline p2flyer::Vec3 defaultBodyOffset() { return p2flyer::Vec3{0.0f, 22.0f, 0.0f}; }
inline p2flyer::Vec3 defaultBodyOffset(p2kurage::Variant v)
{
    return v == p2kurage::Variant::Greater ? p2flyer::Vec3{0.0f, 30.0f, 0.0f} : defaultBodyOffset();
}

// Converted clip name for a source motion (KurageAnimID comments in Kurage.h:
// Land = move2, TakeOff = type1, Fall = type2).
inline const char* poseFor(p2kurage::Motion m)
{
    switch (m) {
    case p2kurage::Motion::DeadFly: return "dead1";
    case p2kurage::Motion::DeadGround: return "dead2";
    case p2kurage::Motion::FlickFly: return "flick1";
    case p2kurage::Motion::FlickGround: return "flick2";
    case p2kurage::Motion::Wait: return "wait";
    case p2kurage::Motion::Move: return "move1";
    case p2kurage::Motion::Land: return "move2";
    case p2kurage::Motion::TakeOff: return "type1";
    case p2kurage::Motion::Fall: return "type2";
    case p2kurage::Motion::Attack: return "attack";
    default: return nullptr;
    }
}

// Source clip: ANF1 length plus the enemyanimmgr.txt keys (type 0 = loop begin,
// 1 = loop end / suck end, 2 and 3 = KEYEVENT_2 / KEYEVENT_3).
inline p2retail::Motion clipFor(p2kurage::Motion m)
{
    using p2retail::Event;
    const int loop = 2; // ANF1 loop attribute of every Kurage clip
    switch (m) {
    case p2kurage::Motion::DeadFly: return {"dead1.bca", "", 96, loop, {Event{33, 2}, Event{93, 3}}};
    case p2kurage::Motion::DeadGround: return {"dead2.bca", "", 96, loop, {Event{33, 2}, Event{93, 3}}};
    case p2kurage::Motion::FlickFly: return {"flick1.bca", "", 60, loop, {Event{16, 2}}};
    case p2kurage::Motion::FlickGround: return {"flick2.bca", "", 60, loop, {Event{20, 2}, Event{30, 3}}};
    case p2kurage::Motion::Wait: return {"wait.bca", "", 35, loop, {Event{0, 0}, Event{34, 1}}};
    case p2kurage::Motion::Move: return {"move1.bca", "", 60, loop, {Event{0, 0}, Event{59, 1}}};
    case p2kurage::Motion::Land: return {"move2.bca", "", 30, loop, {}};
    case p2kurage::Motion::TakeOff: return {"type1.bca", "", 75, loop, {Event{32, 2}}};
    case p2kurage::Motion::Fall: return {"type2.bca", "", 20, loop, {Event{0, 0}, Event{19, 1}}};
    case p2kurage::Motion::Attack: return {"attack.bca", "", 120, loop, {Event{37, 2}, Event{60, 0}, Event{67, 1}}};
    default: return {"wait.bca", "", 35, loop, {Event{0, 0}, Event{34, 1}}};
    }
}

// Retail keys -> FSM key events.
inline p2kurage::KeyEvent keyFor(int type)
{
    switch (type) {
    case 1: return p2kurage::KeyEvent::Key1;
    case 2: return p2kurage::KeyEvent::Key2;
    case 3: return p2kurage::KeyEvent::Key3;
    default: return p2kurage::KeyEvent::None;
    }
}

// Kurage::getSearchedTarget(offset) gate: the actor must be inside its
// territory (XZ distance to home < fp09) before it scans at all.
inline bool insideTerritory(float dx, float dz, const General& g)
{
    return dx * dx + dz * dz < g.territoryRadius * g.territoryRadius;
}

// Kurage::setRandTarget: a point on a ring of radius
// homeRadius + rand * (territory - homeRadius) around home, at an angle
// pi/2 + rand*pi + atan2(pos - home) from the current bearing.
inline void randTarget(float u1, float u2, float posX, float posZ, float homeX, float homeZ,
                       const General& g, float& outX, float& outZ)
{
    const float radius = u1 * (g.territoryRadius - g.homeRadius) + g.homeRadius;
    const float ang = std::atan2(posX - homeX, posZ - homeZ);
    const float theta = 0.5f * p2flyer::kPi + (u2 * p2flyer::kPi + ang);
    outX = radius * std::sin(theta) + homeX;
    outZ = radius * std::cos(theta) + homeZ;
}

} // namespace p2kurageown
