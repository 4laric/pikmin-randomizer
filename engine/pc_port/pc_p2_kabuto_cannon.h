#pragma once

#include "pc_p2_cannon_stone.h"

// Isolated Cannon Beetle attack-FSM policy for the Stone birth. It consumes the
// animation-event stream and host target snapshot and decides when to fire the
// Stone, with what mouth position / facing / homing flag, and where the attack
// animation goes next. It has no engine, animation, target-enumeration or
// mouth-matrix dependency: the host drives the motion and supplies the mouth
// joint world position and target state.
//
// Source reference: projectPiki/pikmin2 revision
// 632af93787b9c95b63f0c13be32b161375ce3a96 (US GPVE01 rev 0):
//   src/plugProjectNishimuraU/KabutoState.cpp (StateAttack/StateFixAttack),
//   src/plugProjectNishimuraU/Kabuto.cpp (createStoneAttack, getSearchedTarget,
//   isAttackableTarget),
//   include/Game/Entities/Kabuto.h.
// See docs/PIKMIN2_KABUTO_CANNON.md for the contract.

enum class P2KabutoSpecies { Kabuto, Rkabuto, Fkabuto };

enum class P2KabutoPhase {
    Inactive,
    Wait,
    Turn,
    Attack,
    FixAttack,
    Flick,
    FixWait,
    FixTurn,
    FixHide,
    FixStay,
    FixAppear,
    Dead,
    Killed,
};

// Mirrors EnemyAnimKeyEvent::mType (Game/EnemyAnimKeyEvent.h): KEYEVENT_2 is the
// gameplay fire frame; KEYEVENT_END terminates the motion.
enum class P2KabutoEvent { None, Key2, End };

// The policy's decision for the host. `FireStone` means the host must birth a
// Stone from the pending command; `To*` means the host starts the matching
// motion (Fkabuto uses its K_* variant). The policy has already moved its own
// phase to match.
enum class P2KabutoAction {
    None,
    FireStone,
    ToWait,
    ToTurn,
    ToAttack,
    ToFlick,
    ToDead,
    ToFixAttack,
    ToFixWait,
    ToFixTurn,
    ToFixHide,
    ToFixStay,
    ToFixAppear,
};

struct P2KabutoCannonConfig {
    float maxAttackAngle = 0.0f; // general mMaxAttackAngle (degrees), FixAttack END
    float health = 0.0f;         // general mHealth (must be > 0)
};

// Host snapshot for one event. The host resolves target presence/attackability
// (getSearchedTarget / isAttackableTarget), the signed horizontal angle to the
// target, the flick request (EnemyFunc::isStartFlick) and current health.
struct P2KabutoHostState {
    bool targetPresent = false;
    bool targetAttackable = false;
    bool flickRequested = false;
    float targetAngle = 0.0f; // signed horizontal angle to target (radians)
    float health = 0.0f;
};

// Birth command for the Stone policy (P2CannonStone::birth). `position` already
// includes the source +25 y mouth offset.
struct P2KabutoStoneBirth {
    P2CannonStoneVec3 mouthPosition;
    float faceDir = 0.0f;
    bool homing = false;
    bool valid = false;
};

class P2KabutoCannon {
public:
    void reset(const P2KabutoCannonConfig& config, P2KabutoSpecies species);

    bool start();          // onInit: Fkabuto -> KABUTO_FixStay, else KABUTO_Wait
    bool beginAttack();    // host starts KABUTOANIM_Attack
    bool beginFixAttack(); // host starts KABUTOANIM_FixAttack
    bool beginFlick();     // host starts KABUTOANIM_Flick / K_flick
    bool beginDead();      // host starts KABUTOANIM_Dead / K_dead

    // One animation event / FSM step. Returns the host action (transit state or
    // fire). Invalid input returns None without changing state.
    P2KabutoAction onEvent(P2KabutoEvent event, const P2KabutoHostState& host);

    bool hasPendingBirth() const { return mPendingBirth; }

    // Consumes a pending FireStone decision and fills the Stone birth command.
    // Returns false when no fire is pending or the input is invalid.
    bool takeBirth(const P2CannonStoneVec3& mouthJointWorldPos, float faceDir,
                   P2KabutoStoneBirth& out);

    P2KabutoPhase phase() const { return mPhase; }
    P2KabutoSpecies species() const { return mSpecies; }
    bool isAlive() const;
    bool killRequested() const { return mPhase == P2KabutoPhase::Killed; }

private:
    bool valid() const;

    P2KabutoCannonConfig mConfig;
    P2KabutoSpecies mSpecies = P2KabutoSpecies::Kabuto;
    P2KabutoPhase mPhase = P2KabutoPhase::Inactive;
    bool mPendingBirth = false;
};
