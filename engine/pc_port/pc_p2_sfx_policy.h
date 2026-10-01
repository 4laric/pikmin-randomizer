// Pikmin 2 own-FSM species -> Pikmin 1 sound-effect approximation policy.
//
// Engine-free (no engine headers; unit-tested by tools/p2_sfx_policy_test.cpp).
// The ported P2 species run their own FSM on a P1 host with the P1 AI and its
// animation KEY_PlaySound keys suppressed, so nothing ever asked JAudio for a
// sound. Owner-approved "option 1": approximate each P2 event with the closest
// existing P1 SE id from the global pikise bank. This is NOT parity: P2 sound
// ids belong to a different bank and are never sent into P1 JAudio
// (pc_p2_purple_feedback.cpp precedent).
//
// Sound is output-only. Nothing here touches sim state or the sim RNG; the
// rate-limit clock is whatever the caller supplies (wall time in the engine
// glue), so netplay lockstep is unaffected.
#ifndef PC_P2_SFX_POLICY_H
#define PC_P2_SFX_POLICY_H

#include <cmath>
#include <cstddef>
#include <cstdio>

namespace p2sfx {

// P1 SE ids mirrored from include/SoundID.h (PikiSoundID). pc_p2_sfx.cpp
// static_asserts every one of them against the engine enum, so a drift in
// SoundID.h fails the build rather than playing the wrong sound.
enum Se : int {
    kNone                = -1,
    kChappySwing         = 0x03,
    kChappyFootDamage    = 0x08,
    kFlogJump            = 0x0E,
    kFlogLand            = 0x10,
    kBomb                = 0x1F,
    kMinicDie            = 0x22,
    kMinicAlert          = 0x27,
    kSpiderWalk          = 0x29,
    kSpiderSwing         = 0x2B,
    kSpiderBomb          = 0x2D,
    kSpiderDead          = 0x2C,
    kTankFire            = 0x3C,
    kTankBreath          = 0x3D,
    kTankWalk            = 0x3E,
    kTankSwing           = 0x3F,
    kTankDamage          = 0x40,
    kTankDead1           = 0x41,
    kMushSpore           = 0x49,
    kKabutoShot          = 0x5E,
    kKabutoFlip          = 0x5F,
    kKabutoWalk          = 0x60,
    kKabutoDead          = 0x63,
    kRockRoll            = 0x64,
    kRockBreak           = 0x65,
    kCollecPull          = 0x6F,
    kCollecWalk          = 0x70,
    kCollecDead          = 0x72,
    kCollecDown          = 0x73,
    kCollecCry           = 0x74,
    kCollecDamage        = 0x75,
    kKoganeWalk          = 0x76,
    kKoganeDamage        = 0x77,
    kSaraiHover          = 0x78,
    kSaraiDamage         = 0x79,
    kSaraiAttack         = 0x7A,
    kSaraiDead           = 0x7B,
    kMarDead1            = 0x84,
    kKurioneWater        = 0x8B,
    // The P1 Emperor Bulblax boss bank (SE_KING_*): the closest existing sounds
    // for the P2 Emperor (53).
    kKingWalk            = 0x4D,
    kKingReady           = 0x4E,
    kKingBero1           = 0x4F,
    kKingBero2           = 0x50,   // Empress (30) shake-off swing
    kKingEat             = 0x53,
    kKingCheek           = 0x54,
    kKingHip             = 0x56,
    kKingDead1           = 0x57,
    kKingAppear          = 0x59,
    kKingSink            = 0x5A,
};

// P2 source ids (pc_p2_species) covered by the table.
enum Source : unsigned {
    kBreadbug     = 38,
    kGiantBreadbug= 40,   // OoPanModoki: same TEKI_Collec bank as the Breadbug
    kSnitchbug    = 32,
    kDirigibug    = 58,
    kCrawbster    = 94,
    kAntennaBeetle= 41,
    kTitanDweevil = 73,
    kGroink       = 78,
    kGroinkArmored= 97,   // fminihoudai variant, same host module
    kCannonLarva  = 75,
    kCatfish      = 26,   // Water Dumple (wave 3 mechanics, #964)
    kTadpole      = 27,   // Wogpole
    kHana         = 84,   // Creeping Chrysanthemum
    kBombOtakara  = 93,   // Volatile Dweevil
    kKurage       = 57,   // Lesser Spotted Jellyfloat (wave 3 flyers, #960)
    kOniKurage    = 72,   // Greater Spotted Jellyfloat
    kEmpress      = 30,
    kEmperor      = 53,   // KingChappy, Emperor Bulblax
};

enum class Event : int {
    Step = 0,     // footstep (stride helper) / ground movement
    Hover,        // airborne loop pulse (flyers), ~1 s period
    Attack,       // generic attack / throw / whistle-less lunge
    Damage,       // damage cry on health drop (rate limited)
    Dead,         // death cry
    Flick,        // shake-off
    Pull,         // Breadbug tug of war
    Land,         // landing after jump / fall
    Jump,         // jump start
    Burst,        // bomb burst (Dirigibug bomb-rock)
    Whistle,      // Antenna Beetle whistle
    Roll,         // Crawbster roll start
    Crash,        // Crawbster wall crash / slam
    Expose,       // Crawbster flipped (Turn window opens)
    Fire,         // Titan Dweevil fire weapon
    Water,        // Titan Dweevil water weapon
    Gas,          // Titan Dweevil gas weapon
    Elec,         // Titan Dweevil electric weapon
    Shot,         // Groink volley / Cannon Larva stone
    Appear,       // Emperor erupts from the ground
    Dive,         // Emperor burrows again
    Roar,         // Emperor war cry
    Eat,          // Emperor swallows what its tongue caught
    Fuse,         // Volatile Dweevil lit-bomb tick/crackle (P1 spider spark SE)
    Count
};

inline const char* eventName(Event e) {
    switch (e) {
    case Event::Step: return "step";
    case Event::Hover: return "hover";
    case Event::Attack: return "attack";
    case Event::Damage: return "damage";
    case Event::Dead: return "dead";
    case Event::Flick: return "flick";
    case Event::Pull: return "pull";
    case Event::Land: return "land";
    case Event::Jump: return "jump";
    case Event::Burst: return "burst";
    case Event::Whistle: return "whistle";
    case Event::Roll: return "roll";
    case Event::Crash: return "crash";
    case Event::Expose: return "expose";
    case Event::Fire: return "fire";
    case Event::Water: return "water";
    case Event::Gas: return "gas";
    case Event::Elec: return "elec";
    case Event::Shot: return "shot";
    case Event::Appear: return "appear";
    case Event::Dive: return "dive";
    case Event::Roar: return "roar";
    case Event::Eat: return "eat";
    case Event::Fuse: return "fuse";
    default: return "?";
    }
}

// (source_id, event) -> P1 SE id, or kNone when the event has no
// approximation for that species (the caller then plays nothing).
inline int seFor(unsigned sourceId, Event e) {
    switch (sourceId) {
    case kBreadbug: // P1 has the Breadbug itself (TEKI_Collec): use its bank.
    case kGiantBreadbug:
        switch (e) {
        case Event::Step: return kCollecWalk;
        case Event::Pull: return kCollecPull;
        case Event::Attack: return kCollecCry;
        case Event::Damage: return kCollecDamage;
        case Event::Dead: return kCollecDead;
        case Event::Land: return kCollecDown;
        default: return kNone;
        }
    case kSnitchbug: // P1 has the Swooping Snitchbug (TEKI_Sarai).
        switch (e) {
        case Event::Hover: return kSaraiHover;
        case Event::Attack: return kSaraiAttack;
        case Event::Damage: return kSaraiDamage;
        case Event::Dead: return kSaraiDead;
        case Event::Flick: return kChappySwing;
        case Event::Land: return kFlogLand;
        default: return kNone;
        }
    case kKurage:
    case kOniKurage: // Jellyfloat: P1 has no floater; the Snitchbug flyer bank approximates it.
        switch (e) {
        case Event::Hover: return kSaraiHover;
        case Event::Attack: return kSaraiAttack;   // suction pull-in
        case Event::Damage: return kSaraiDamage;
        case Event::Dead: return kSaraiDead;
        case Event::Flick: return kChappySwing;
        case Event::Land: return kFlogLand;
        default: return kNone;
        }
    case kDirigibug: // Flyer with a bomb: Snitchbug hover, P1 bomb-rock burst.
        switch (e) {
        case Event::Hover: return kSaraiHover;
        case Event::Attack: return kSaraiAttack;   // bomb release / throw
        case Event::Burst: return kBomb;
        case Event::Fuse: return kSpiderBomb;      // lit-bomb tick, as the Volatile Dweevil bomb (#1066)
        case Event::Damage: return kSaraiDamage;
        case Event::Dead: return kMarDead1;
        case Event::Flick: return kChappySwing;
        case Event::Land: return kFlogLand;
        default: return kNone;
        }
    case kCrawbster: // Heavy armoured crab: Cannon Beetle body, rolling boulder.
        switch (e) {
        case Event::Step: return kKabutoWalk;
        case Event::Roll: return kRockRoll;
        case Event::Crash: return kRockBreak;
        case Event::Expose: return kKabutoFlip;
        case Event::Attack: return kTankSwing;     // claw sweep
        case Event::Flick: return kTankSwing;
        case Event::Damage: return kTankDamage;
        case Event::Dead: return kKabutoDead;
        default: return kNone;
        }
    case kAntennaBeetle: // Small hopping beetle: Flint Beetle bank + frog hops.
        switch (e) {
        case Event::Step: return kKoganeWalk;
        case Event::Jump: return kFlogJump;
        case Event::Land: return kFlogLand;
        case Event::Whistle: return kMinicAlert;
        case Event::Flick: return kChappySwing;
        case Event::Damage: return kKoganeDamage;
        case Event::Dead: return kMinicDie;
        default: return kNone;
        }
    case kTitanDweevil: // Giant arachnid: Beady Long Legs feet, elemental weapons.
        switch (e) {
        case Event::Step: return kSpiderWalk;
        case Event::Fire: return kTankFire;
        case Event::Water: return kKurioneWater;
        case Event::Gas: return kMushSpore;
        case Event::Elec: return kTankBreath;
        case Event::Flick: return kSpiderSwing;
        case Event::Damage: return kTankDamage;
        case Event::Dead: return kSpiderDead;
        default: return kNone;
        }
    case kGroink:
    case kGroinkArmored: // Walking cannon: Fiery Blowhog body, Cannon Beetle shot.
        switch (e) {
        case Event::Step: return kTankWalk;
        case Event::Shot: return kKabutoShot;
        case Event::Flick: return kTankSwing;
        case Event::Damage: return kTankDamage;
        case Event::Dead: return kTankDead1;
        default: return kNone;
        }
    case kCannonLarva: // Runs on the Armored Cannon Beetle host: its own bank.
        switch (e) {
        case Event::Step: return kKabutoWalk;
        case Event::Shot: return kKabutoShot;
        case Event::Flick: return kKabutoFlip;
        case Event::Damage: return kTankDamage;
        case Event::Dead: return kKabutoDead;
        default: return kNone;
        }
    case kCatfish: // Water Dumple: Fiery Blowhog-style lunge bank, Wollywog splash.
        switch (e) {
        case Event::Step: return kFlogLand;
        case Event::Attack: return kChappySwing;   // bite
        case Event::Flick: return kTankSwing;
        case Event::Damage: return kTankDamage;
        case Event::Dead: return kTankDead1;
        default: return kNone;
        }
    case kTadpole: // Wogpole: tiny hopper (P1 Wollywog hop), harmless.
        switch (e) {
        case Event::Jump: return kFlogJump;
        case Event::Land: return kFlogLand;
        case Event::Damage: return kMinicAlert;
        case Event::Dead: return kMinicDie;
        default: return kNone;
        }
    case kHana: // Creeping Chrysanthemum: Dwarf Bulborb host sounds.
        switch (e) {
        case Event::Step: return kCollecWalk;
        case Event::Attack: return kChappySwing;   // bite
        case Event::Flick: return kChappySwing;
        case Event::Damage: return kChappyFootDamage;
        case Event::Dead: return kCollecDead;
        default: return kNone;
        }
    case kBombOtakara: // Volatile Dweevil: Kogane-like scuttle + P1 bomb burst.
        switch (e) {
        case Event::Step: return kKoganeWalk;
        case Event::Burst: return kBomb;
        case Event::Fuse: return kSpiderBomb;
        case Event::Flick: return kChappySwing;
        case Event::Damage: return kKoganeDamage;
        case Event::Dead: return kMinicDie;
        default: return kNone;
        }
    case kEmpress: // Empress Bulblax: P1's Emperor Bulblax (KingChappy) bank.
        switch (e) {
        case Event::Roll: return kKingReady;    // roll wind-up
        case Event::Crash: return kKingHip;     // territory-edge slam
        case Event::Flick: return kKingBero2;   // tongue-like shake-off swing
        case Event::Damage: return kKingCheek;
        case Event::Dead: return kKingDead1;
        default: return kNone;
        }
    case kEmperor: // Emperor Bulblax: the P1 Emperor Bulblax boss bank.
        switch (e) {
        case Event::Step: return kKingWalk;
        case Event::Appear: return kKingAppear;
        case Event::Dive: return kKingSink;
        case Event::Roar: return kKingReady;
        case Event::Attack: return kKingBero1;     // tongue lash
        case Event::Eat: return kKingEat;
        case Event::Flick: return kKingHip;        // trample / shake-off
        case Event::Damage: return kKingCheek;
        case Event::Dead: return kKingDead1;
        default: return kNone;
        }
    default:
        return kNone;
    }
}

// Minimum seconds between two plays of the same event on one actor.
inline float minInterval(Event e) {
    switch (e) {
    case Event::Step: return 0.2f;
    case Event::Hover: return 1.0f;
    case Event::Damage: return 0.3f;
    case Event::Dead: return 5.0f;      // one death cry
    case Event::Attack: return 0.25f;
    case Event::Pull: return 0.6f;
    case Event::Burst: return 0.05f;    // per bomb; several bombs may chain
    case Event::Whistle: return 1.0f;
    case Event::Roll: return 1.0f;
    case Event::Crash: return 0.5f;
    case Event::Expose: return 1.0f;
    case Event::Fire: case Event::Water: case Event::Gas: case Event::Elec: return 0.5f;
    case Event::Shot: return 0.15f;
    case Event::Appear: case Event::Dive: case Event::Roar: return 1.0f;
    case Event::Eat: return 0.5f;
    case Event::Fuse: return 0.05f;     // paced by the telegraph (<= 0.07 s at the end)
    default: return 0.25f;
    }
}

// Number of P2_SFX log lines allowed per actor for a noisy event. Periodic
// events (steps, hover pulses) are logged a few times so the evidence can
// pair them with the [PC Audio] trace; every other event is logged always.
inline int markerBudget(Event e) {
    switch (e) {
    case Event::Step: return 4;
    case Event::Hover: return 3;
    default: return 1 << 30;
    }
}

// Per-actor rate-limit + marker-budget state. Callers keep one per actor.
struct ActorGate {
    float lastAt[int(Event::Count)];
    int logged[int(Event::Count)];
    bool primed[int(Event::Count)];

    ActorGate() { reset(); }
    void reset() {
        for (int i = 0; i < int(Event::Count); ++i) {
            lastAt[i] = 0.0f;
            logged[i] = 0;
            primed[i] = false;
        }
    }

    // Decides whether an event may play at time `now` (seconds, any monotonic
    // clock). Returns the SE id to play, or kNone when rate limited or
    // unmapped. `logIt` is set when a P2_SFX marker should be printed.
    int admit(unsigned sourceId, Event e, float now, bool* logIt) {
        if (logIt) *logIt = false;
        const int se = seFor(sourceId, e);
        if (se == kNone) return kNone;
        const int i = int(e);
        if (primed[i] && now - lastAt[i] < minInterval(e)) return kNone;
        primed[i] = true;
        lastAt[i] = now;
        if (logged[i] < markerBudget(e)) {
            ++logged[i];
            if (logIt) *logIt = true;
        }
        return se;
    }
};

// Footstep stride helper: accumulates horizontal distance and fires once per
// `strideLength` units travelled. Distance-based so a slow shuffle and a
// sprint both sound right; the caller still passes Step through ActorGate.
struct Stride {
    float travelled = 0.0f;
    float lastX = 0.0f, lastZ = 0.0f;
    bool primed = false;

    void reset() { travelled = 0.0f; primed = false; }

    // Feed the actor's current XZ position. Returns true when a step fires.
    bool advance(float x, float z, float strideLength) {
        if (!primed) {
            primed = true;
            lastX = x;
            lastZ = z;
            return false;
        }
        const float dx = x - lastX, dz = z - lastZ;
        lastX = x;
        lastZ = z;
        const float d2 = dx * dx + dz * dz;
        if (d2 <= 0.0f || strideLength <= 0.0f) return false;
        // Teleports (resetPosition) must not fire a burst of steps.
        if (d2 > strideLength * strideLength * 100.0f) return false;
        const float d = std::sqrt(d2);
        travelled += d;
        if (travelled >= strideLength) {
            travelled -= strideLength;
            if (travelled >= strideLength) travelled = 0.0f;
            return true;
        }
        return false;
    }
};

// Formats the evidence marker. Returns the number of characters written.
inline int formatMarker(char* buf, std::size_t size, unsigned sourceId, unsigned token, Event e, int se) {
    return std::snprintf(buf, size, "P2_SFX source_id=%u generator=%u event=%s se=0x%02X", sourceId, token,
                         eventName(e), se);
}

} // namespace p2sfx

#endif // PC_P2_SFX_POLICY_H
