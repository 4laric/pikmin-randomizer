#include "pc_p2_kabuto_cannon.h"

#include <cmath>

namespace {
constexpr float kPi = 3.14159265358979323846f;

bool finite(float value) { return std::isfinite(value); }

bool live(P2KabutoPhase phase)
{
    return phase == P2KabutoPhase::Wait || phase == P2KabutoPhase::Turn
        || phase == P2KabutoPhase::Attack || phase == P2KabutoPhase::FixAttack
        || phase == P2KabutoPhase::Flick || phase == P2KabutoPhase::FixWait
        || phase == P2KabutoPhase::FixTurn || phase == P2KabutoPhase::FixHide
        || phase == P2KabutoPhase::FixStay || phase == P2KabutoPhase::FixAppear;
}
} // namespace

void P2KabutoCannon::reset(const P2KabutoCannonConfig& config, P2KabutoSpecies species)
{
    mConfig = config;
    mSpecies = species;
    mPhase = P2KabutoPhase::Inactive;
    mPendingBirth = false;
}

bool P2KabutoCannon::valid() const
{
    return finite(mConfig.maxAttackAngle) && mConfig.maxAttackAngle >= 0.0f
        && finite(mConfig.health) && mConfig.health > 0.0f;
}

bool P2KabutoCannon::isAlive() const { return live(mPhase); }

bool P2KabutoCannon::start()
{
    if (mPhase != P2KabutoPhase::Inactive || !valid()) {
        return false;
    }
    // onInit (Kabuto.cpp:48-54): Fkabuto starts buried in KABUTO_FixStay;
    // the surfaced species start in KABUTO_Wait.
    mPhase = (mSpecies == P2KabutoSpecies::Fkabuto) ? P2KabutoPhase::FixStay
                                                    : P2KabutoPhase::Wait;
    mPendingBirth = false;
    return true;
}

bool P2KabutoCannon::beginAttack()
{
    if ((mPhase != P2KabutoPhase::Wait && mPhase != P2KabutoPhase::Turn)
        || !valid()) {
        return false;
    }
    mPhase = P2KabutoPhase::Attack;
    mPendingBirth = false;
    return true;
}

bool P2KabutoCannon::beginFixAttack()
{
    const bool fromBuried = mPhase == P2KabutoPhase::Inactive
        || mPhase == P2KabutoPhase::FixWait || mPhase == P2KabutoPhase::FixTurn
        || mPhase == P2KabutoPhase::FixHide || mPhase == P2KabutoPhase::FixAppear;
    if (mPhase == P2KabutoPhase::Dead || mPhase == P2KabutoPhase::Killed || !valid()
        || !(fromBuried || live(mPhase))) {
        return false;
    }
    mPhase = P2KabutoPhase::FixAttack;
    mPendingBirth = false;
    return true;
}

bool P2KabutoCannon::beginFlick()
{
    if (!live(mPhase) || !valid()) {
        return false;
    }
    mPhase = P2KabutoPhase::Flick;
    mPendingBirth = false;
    return true;
}

bool P2KabutoCannon::beginDead()
{
    if (mPhase == P2KabutoPhase::Killed || !valid()) {
        return false;
    }
    mPhase = P2KabutoPhase::Dead;
    mPendingBirth = false;
    return true;
}

P2KabutoAction P2KabutoCannon::onEvent(P2KabutoEvent event, const P2KabutoHostState& host)
{
    if (!valid() || mPhase == P2KabutoPhase::Inactive
        || mPhase == P2KabutoPhase::Killed) {
        return P2KabutoAction::None;
    }
    if (!finite(host.health) || !finite(host.targetAngle)) {
        return P2KabutoAction::None;
    }

    // Death gate at the start of every live exec (KabutoState.cpp:92-95,
    // :142-145, :350-353, :715-718).
    // FixStay is invulnerable/hidden (StateFixStay), so it has no death gate.
    if (mPhase != P2KabutoPhase::Dead && mPhase != P2KabutoPhase::FixStay
        && host.health <= 0.0f) {
        mPhase = P2KabutoPhase::Dead;
        mPendingBirth = false;
        return P2KabutoAction::ToDead;
    }

    switch (mPhase) {
    case P2KabutoPhase::Wait:
        // StateWait::exec (KabutoState.cpp:89-110): flick request wins, else a
        // searched target, on the wait motion's END.
        if (event == P2KabutoEvent::End) {
            if (host.flickRequested) {
                mPhase = P2KabutoPhase::Flick;
                return P2KabutoAction::ToFlick;
            }
            if (host.targetPresent) {
                mPhase = P2KabutoPhase::Turn;
                return P2KabutoAction::ToTurn;
            }
        }
        return P2KabutoAction::None;

    case P2KabutoPhase::Turn:
        // StateTurn::exec (KabutoState.cpp:139-174): on END, flick or an
        // attackable target; otherwise keep turning.
        if (event == P2KabutoEvent::End) {
            if (host.flickRequested) {
                mPhase = P2KabutoPhase::Flick;
                return P2KabutoAction::ToFlick;
            }
            if (host.targetPresent && host.targetAttackable) {
                mPhase = P2KabutoPhase::Attack;
                return P2KabutoAction::ToAttack;
            }
        }
        return P2KabutoAction::None;

    case P2KabutoPhase::Attack:
        // StateAttack::exec (KabutoState.cpp:347-374). KEYEVENT_2 births the
        // Stone exactly once per animation; END picks Flick/Turn/Wait.
        if (event == P2KabutoEvent::Key2) {
            mPendingBirth = true;
            return P2KabutoAction::FireStone;
        }
        if (event == P2KabutoEvent::End) {
            if (host.flickRequested) {
                mPhase = P2KabutoPhase::Flick;
                return P2KabutoAction::ToFlick;
            }
            if (host.targetPresent) {
                mPhase = P2KabutoPhase::Turn;
                return P2KabutoAction::ToTurn;
            }
            mPhase = P2KabutoPhase::Wait;
            return P2KabutoAction::ToWait;
        }
        return P2KabutoAction::None;

    case P2KabutoPhase::FixAttack:
        // StateFixAttack::exec (KabutoState.cpp:712-750). Same single KEYEVENT_2
        // fire; END picks FixFlick/FixAttack/FixWait/FixTurn/FixHide.
        if (event == P2KabutoEvent::Key2) {
            mPendingBirth = true;
            return P2KabutoAction::FireStone;
        }
        if (event == P2KabutoEvent::End) {
            if (host.flickRequested) {
                mPhase = P2KabutoPhase::Flick;
                return P2KabutoAction::ToFlick;
            }
            if (host.targetAttackable) {
                mPhase = P2KabutoPhase::FixAttack;
                return P2KabutoAction::ToFixAttack;
            }
            if (host.targetPresent) {
                const float limit = mConfig.maxAttackAngle * kPi / 180.0f; // DEG2RAD
                if (std::fabs(host.targetAngle) <= limit) {
                    mPhase = P2KabutoPhase::FixWait;
                    return P2KabutoAction::ToFixWait;
                }
                mPhase = P2KabutoPhase::FixTurn;
                return P2KabutoAction::ToFixTurn;
            }
            mPhase = P2KabutoPhase::FixHide;
            return P2KabutoAction::ToFixHide;
        }
        return P2KabutoAction::None;

    case P2KabutoPhase::FixStay:
        // StateFixStay::exec (KabutoState.cpp:411-421): invulnerable, hidden
        // buried wait; a searched target emerges. It consumes no anim events.
        if (host.targetPresent) {
            mPhase = P2KabutoPhase::FixAppear;
            return P2KabutoAction::ToFixAppear;
        }
        return P2KabutoAction::None;

    case P2KabutoPhase::FixAppear:
        // StateFixAppear::exec (KabutoState.cpp:473-506) on END.
        if (event == P2KabutoEvent::End) {
            if (host.flickRequested) {
                mPhase = P2KabutoPhase::Flick;
                return P2KabutoAction::ToFlick;
            }
            if (host.targetAttackable) {
                mPhase = P2KabutoPhase::FixAttack;
                return P2KabutoAction::ToFixAttack;
            }
            if (host.targetPresent) {
                const float limit = mConfig.maxAttackAngle * kPi / 180.0f; // DEG2RAD
                if (std::fabs(host.targetAngle) <= limit) {
                    mPhase = P2KabutoPhase::FixWait;
                    return P2KabutoAction::ToFixWait;
                }
                mPhase = P2KabutoPhase::FixTurn;
                return P2KabutoAction::ToFixTurn;
            }
            mPhase = P2KabutoPhase::FixHide;
            return P2KabutoAction::ToFixHide;
        }
        return P2KabutoAction::None;

    case P2KabutoPhase::FixHide:
        // StateFixHide::exec (KabutoState.cpp:545-553): END -> FixStay.
        if (event == P2KabutoEvent::End) {
            mPhase = P2KabutoPhase::FixStay;
            return P2KabutoAction::ToFixStay;
        }
        return P2KabutoAction::None;

    case P2KabutoPhase::FixWait:
        // StateFixWait::exec (KabutoState.cpp:584-616) on END.
        if (event == P2KabutoEvent::End) {
            if (host.flickRequested) {
                mPhase = P2KabutoPhase::Flick;
                return P2KabutoAction::ToFlick;
            }
            if (host.targetAttackable) {
                mPhase = P2KabutoPhase::FixAttack;
                return P2KabutoAction::ToFixAttack;
            }
            if (host.targetPresent) {
                const float limit = mConfig.maxAttackAngle * kPi / 180.0f;
                if (std::fabs(host.targetAngle) <= limit) {
                    mPhase = P2KabutoPhase::FixWait; // keep waiting
                    return P2KabutoAction::ToFixWait;
                }
                mPhase = P2KabutoPhase::FixTurn;
                return P2KabutoAction::ToFixTurn;
            }
            mPhase = P2KabutoPhase::FixHide;
            return P2KabutoAction::ToFixHide;
        }
        return P2KabutoAction::None;

    case P2KabutoPhase::FixTurn:
        // StateFixTurn::exec (KabutoState.cpp:644-681) on END.
        if (event == P2KabutoEvent::End) {
            if (host.flickRequested) {
                mPhase = P2KabutoPhase::Flick;
                return P2KabutoAction::ToFlick;
            }
            if (!host.targetPresent) {
                mPhase = P2KabutoPhase::FixHide;
                return P2KabutoAction::ToFixHide;
            }
            if (host.targetAttackable) {
                mPhase = P2KabutoPhase::FixAttack;
                return P2KabutoAction::ToFixAttack;
            }
            const float limit = mConfig.maxAttackAngle * kPi / 180.0f;
            if (std::fabs(host.targetAngle) <= limit) {
                mPhase = P2KabutoPhase::FixWait;
                return P2KabutoAction::ToFixWait;
            }
            return P2KabutoAction::None; // keep turning
        }
        return P2KabutoAction::None;

    case P2KabutoPhase::Flick:
        // StateFlick END returns to the search loop; the exact target branch is
        // host-owned. This policy folds it to Turn/Wait.
        if (event == P2KabutoEvent::End) {
            if (host.targetPresent) {
                mPhase = P2KabutoPhase::Turn;
                return P2KabutoAction::ToTurn;
            }
            mPhase = P2KabutoPhase::Wait;
            return P2KabutoAction::ToWait;
        }
        return P2KabutoAction::None;

    case P2KabutoPhase::Dead:
        // StateDead::exec (KabutoState.cpp:55-59): END -> kill(nullptr).
        if (event == P2KabutoEvent::End) {
            mPhase = P2KabutoPhase::Killed;
        }
        return P2KabutoAction::None;

    default:
        return P2KabutoAction::None;
    }
}

bool P2KabutoCannon::takeBirth(const P2CannonStoneVec3& mouthJointWorldPos, float faceDir,
                               P2KabutoStoneBirth& out)
{
    out = P2KabutoStoneBirth{};
    if (!mPendingBirth || !std::isfinite(faceDir) || !std::isfinite(mouthJointWorldPos.x)
        || !std::isfinite(mouthJointWorldPos.y) || !std::isfinite(mouthJointWorldPos.z)) {
        return false;
    }
    // createStoneAttack (Kabuto.cpp:268-290): mouth joint world matrix with the
    // +25 y offset; homing only for Rkabuto (getEnemyTypeID()==EnemyID_Rkabuto).
    out.mouthPosition = P2CannonStone::mouthBirthPosition(mouthJointWorldPos);
    out.faceDir = faceDir;
    out.homing = (mSpecies == P2KabutoSpecies::Rkabuto);
    out.valid = true;
    mPendingBirth = false;
    return true;
}
