#pragma once
// Engine-free press/landing policy for registered Dweevils (#884): FireOtakara 59,
// WaterOtakara 60, GasOtakara 61, ElecOtakara 62 and BombOtakara 93 on the P1
// TEKI_Chappy (Dwarf Bulborb) host.
//
// The P1 host has two "squash" reactions a Dweevil must not inherit:
//   * ThrownLanding: a Piki in PIKISTATE_Flying touching the host raises a
//     TekiEventType::Entity (BTeki::collisionCallback, tekibteki.cpp:1946) that
//     TaiChappySmashedAction -> TaiSmashedAction::actByEvent
//     (taichappy.cpp:626-633, taireactionactions.cpp:248-259) turns into
//     CHAPPYSTATE_Unk13, whose TaiLifeDamageAction::start subtracts CHAPPYPF_SmashDamage
//     from mHealth with no clamp (taireactionactions.cpp:41-44, taichappy.cpp:357-369).
//     That is the runtime lump "delta=150.0 interaction=unknown" of #884.
//   * HostPress: InteractPress::actTeki (tekiinteraction.cpp) raises
//     TekiEventType::Pressed, which TaiPressedAction (taireactionactions.cpp:276)
//     turns into CHAPPYSTATE_Unk2 (TaiLifeZeroAction + TaiBeingPressedAction,
//     taichappy.cpp:393-407): mHealth=0 and the ALIVE/ATARI options cleared.
//
// P2 source for both: a thrown Piki falling onto an enemy sends InteractPress then
// InteractFlyCollision (pikiState.cpp:2321-2333 in pikmin2-research) and sticks when
// both are refused (pikiState.cpp:2335-2342). InteractPress::actEnemy ->
// pressCallBack (enemyInteractBattle.cpp:37-40); neither OtakaraBase.h nor
// BombOtakara.h / {Fire,Water,Gas,Elec}Otakara.h override pressCallBack or
// flyCollisionCallBack, so EnemyBase::pressCallBack / flyCollisionCallBack return
// false (enemyBase.cpp:2790-2802): no damage, no addDamage (so no mFlickTimer tick),
// no forceBomb for BombOtakara (its overrides are damage/hipdrop/earthquake/bomb
// only, BombOtakara.cpp:42-87), and the Piki latches on and attacks.
// Hipdrop (purple only) is a different interaction and is not routed here.
namespace p2otakarapress {

enum class Path { HostPress, ThrownLanding };

struct Decision {
    bool consume = false;      // skip the P1 host squash reaction
    float damage = 0.0f;       // damage the Dweevil takes from the press itself
    bool countsAsHit = false;  // whether it adds to mFlickTimer (source addDamage)
    bool detonatesBomb = false;
    const char* outcome = "host";
};

inline const char* pathName(Path path) {
    return path == Path::HostPress ? "InteractPress" : "ThrownLanding";
}

// registered: the actor is a bound Otakara actor (59-62 or 93). Unregistered
// actors keep the P1 host reaction untouched.
inline Decision decide(bool registered, Path path) {
    Decision d;
    if (!registered) return d;
    (void)path; // both paths resolve to the same source pressCallBack=false
    d.consume = true;
    d.damage = 0.0f;
    d.countsAsHit = false;
    d.detonatesBomb = false;
    d.outcome = "ignored_source_press";
    return d;
}

// Once-per-press log gate: the same presser keeps overlapping the host for a few
// frames, so only a new presser or a gap longer than the window logs again.
constexpr float LOG_WINDOW = 0.5f;
inline bool shouldLog(const void* lastPresser, float sinceLast, const void* presser) {
    return presser != lastPresser || sinceLast >= LOG_WINDOW;
}

} // namespace p2otakarapress
