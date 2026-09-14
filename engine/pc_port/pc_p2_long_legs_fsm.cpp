#include "pc_p2_long_legs_fsm.h"

P2LongLegsFsmParms p2LongLegsParmsFor(P2LongLegsSpecies species)
{
    P2LongLegsFsmParms p;
    p.species = species;
    switch (species) {
    case P2LongLegsSpecies::Damagumo:
        p.maxHealth = 1300.0f;
        p.speed = 100.0f;
        p.territoryRadius = 400.0f;
        p.pressDamage = 10.0f;
        p.waitMinSeconds = 1.75f; p.waitMaxSeconds = 3.5f;
        p.walkMinSeconds = 3.25f; p.walkMaxSeconds = 6.5f;
        p.hasShotGun = false;
        p.deathChildren = 25; // ShijimiChou when no treasure is held
        break;
    case P2LongLegsSpecies::Houdai:
        p.maxHealth = 2800.0f;
        p.speed = 250.0f;
        p.territoryRadius = 800.0f; // mLastToTerritory becomes 130 in Hole of Heroes
        p.pressDamage = 0.0f;       // no press code at all
        p.waitMinSeconds = 1.5f; p.waitMaxSeconds = 3.0f;
        p.walkMinSeconds = 3.5f; p.walkMaxSeconds = 7.0f;
        p.hasShotGun = true;
        p.deathChildren = 0;
        break;
    case P2LongLegsSpecies::BigFoot:
        p.maxHealth = 10000.0f;
        p.speed = 70.0f;
        p.territoryRadius = 310.0f;
        p.pressDamage = 10.0f;
        p.waitMinSeconds = 5.0f; p.waitMaxSeconds = 5.0f; // fixed 5 s
        p.walkMinSeconds = 10.0f; p.walkMaxSeconds = 10.0f; // mNormalTravelTime fp20
        p.walkPostFlickSeconds = 5.0f; // mPostShakeTravelTime fp21 disc
        p.hasShotGun = false;
        p.deathChildren = 30; // Mitites, ball form, when no treasure is held
        break;
    }
    return p;
}

const char* P2LongLegsFsm::stateName(P2LongLegsState state)
{
    switch (state) {
    case P2LongLegsState::Dead: return "Dead";
    case P2LongLegsState::Stay: return "Stay";
    case P2LongLegsState::Land: return "Land";
    case P2LongLegsState::Wait: return "Wait";
    case P2LongLegsState::Flick: return "Flick";
    case P2LongLegsState::Walk: return "Walk";
    case P2LongLegsState::Shot: return "Shot";
    }
    return "?";
}

const char* P2LongLegsFsm::speciesName(P2LongLegsSpecies species)
{
    switch (species) {
    case P2LongLegsSpecies::Damagumo: return "Damagumo";
    case P2LongLegsSpecies::Houdai: return "Houdai";
    case P2LongLegsSpecies::BigFoot: return "BigFoot";
    }
    return "?";
}

void P2LongLegsFsm::reset(const P2LongLegsFsmParms& parms)
{
    mParms = parms;
    mState = P2LongLegsState::Stay;
    mStateTimer = 0.0f;
    mChosenSeconds = 0.0f;
    mShotCooldown = 0.0f;
    mBurstTimer = 0.0f;
    mBurstOn = false;
    mAimTimer = 0.0f;
    mFeetFired = false;
    mEnraged = false;
}

bool P2LongLegsFsm::crushGate(const P2LongLegsFsmInput& input) const
{
    // Source: a foot presses only while descending or planting with a move
    // ratio above 1 (IKSystemMgr::isCollisionCheck). A resting foot is
    // harmless, and Houdai has no press code.
    return mParms.pressDamage > 0.0f && input.footDescendingOrPlanting
        && input.ikMoveRatio > 1.0f;
}

float P2LongLegsFsm::pickWaitSeconds(const P2LongLegsFsmInput& input) const
{
    const float roll = input.roll < 0.0f ? 0.0f : (input.roll > 1.0f ? 1.0f : input.roll);
    return mParms.waitMinSeconds + roll * (mParms.waitMaxSeconds - mParms.waitMinSeconds);
}

float P2LongLegsFsm::pickWalkSeconds(const P2LongLegsFsmInput& input) const
{
    if (mParms.species == P2LongLegsSpecies::BigFoot && mEnraged
            && mParms.walkPostFlickSeconds > 0.0f)
        return mParms.walkPostFlickSeconds;
    const float roll = input.roll < 0.0f ? 0.0f : (input.roll > 1.0f ? 1.0f : input.roll);
    return mParms.walkMinSeconds + roll * (mParms.walkMaxSeconds - mParms.walkMinSeconds);
}

void P2LongLegsFsm::enter(P2LongLegsState next, const P2LongLegsFsmInput& input,
                          P2LongLegsFsmOutput& output)
{
    mState = next;
    mStateTimer = 0.0f;
    mBurstTimer = 0.0f;
    output.entered = true;
    switch (next) {
    case P2LongLegsState::Wait:
        mChosenSeconds = pickWaitSeconds(input);
        output.chosenSeconds = mChosenSeconds;
        break;
    case P2LongLegsState::Walk:
        mChosenSeconds = pickWalkSeconds(input);
        output.chosenSeconds = mChosenSeconds;
        output.enragedWalk = mParms.species == P2LongLegsSpecies::BigFoot && mEnraged;
        break;
    case P2LongLegsState::Shot:
        mBurstOn = true;
        mAimTimer = 0.0f;
        mShotCooldown = 0.0f;
        break;
    case P2LongLegsState::Dead:
        if (input.holdingTreasure) {
            output.dropTreasure = true; // thrown straight down from kosi
        } else {
            output.birthChildren = mParms.deathChildren;
        }
        break;
    default:
        break;
    }
}

void P2LongLegsFsm::update(const P2LongLegsFsmInput& input, P2LongLegsFsmOutput& output)
{
    output = P2LongLegsFsmOutput();
    output.state = mState;

    if (mState == P2LongLegsState::Dead)
        return;

    // Death is terminal and bypasses the normal state machine; the held
    // treasure is dropped, otherwise the no-treasure child burst is requested.
    if (input.killed) {
        enter(P2LongLegsState::Dead, input, output);
        output.state = mState;
        return;
    }

    if (input.damageTaken) {
        mShotCooldown = 0.0f; // taking damage postpones the gun (Houdai.cpp)
    } else if (mState != P2LongLegsState::Shot) {
        mShotCooldown += kSourceDelta;
    }

    mStateTimer += kSourceDelta;
    mBurstTimer += kSourceDelta;

    switch (mState) {
    case P2LongLegsState::Stay:
        if (input.wakeTargetNearby)
            enter(P2LongLegsState::Land, input, output);
        break;

    case P2LongLegsState::Land:
        if (input.landingKey2 && !mFeetFired) {
            mFeetFired = true;
            output.feetFired = true;
            output.footCrush = mParms.pressDamage > 0.0f; // key 2 fires all four feet
        }
        if (input.animEnd)
            enter(P2LongLegsState::Wait, input, output);
        break;

    case P2LongLegsState::Wait:
        if (input.pikminAccumulating) {
            enter(P2LongLegsState::Flick, input, output);
        } else if (mParms.hasShotGun && mShotCooldown >= mParms.burstCooldownSeconds) {
            enter(P2LongLegsState::Shot, input, output);
        } else if (mStateTimer >= mChosenSeconds) {
            enter(P2LongLegsState::Walk, input, output);
        }
        break;

    case P2LongLegsState::Flick:
        if (input.flickKey2)
            output.shake = true;
        if (input.animEnd) {
            if (mParms.hasShotGun) {
                enter(P2LongLegsState::Shot, input, output); // always after a Flick
            } else {
                if (mParms.species == P2LongLegsSpecies::BigFoot)
                    mEnraged = true; // set when Flick ends
                enter(P2LongLegsState::Wait, input, output);
            }
        }
        break;

    case P2LongLegsState::Walk:
        output.footCrush = crushGate(input);
        if (input.pikminAccumulating) {
            enter(P2LongLegsState::Flick, input, output);
        } else if (mStateTimer >= mChosenSeconds) {
            if (mParms.species == P2LongLegsSpecies::BigFoot)
                mEnraged = false; // cleared when the next Walk ends
            enter(P2LongLegsState::Wait, input, output);
        }
        break;

    case P2LongLegsState::Shot: {
        mAimTimer += kSourceDelta;
        if (mBurstOn) {
            if (mBurstTimer >= mParms.burstOnSeconds) {
                mBurstOn = false;
                mBurstTimer = 0.0f;
            } else if (input.shotLoop) {
                output.fireShell = true; // one shell per attack loop, from the muzzle
            }
        } else if (mBurstTimer >= mParms.burstOffSeconds) {
            mBurstOn = true;
            mBurstTimer = 0.0f;
        }
        if (input.animEnd || mAimTimer >= mParms.maxAimSeconds)
            enter(P2LongLegsState::Wait, input, output);
        break;
    }

    default:
        break;
    }

    // Derived after the transition so a landing-key-2 tick reports the new
    // damage window immediately.
    output.bitterImmune = mState == P2LongLegsState::Stay
        || (mState == P2LongLegsState::Land && !mFeetFired);
    output.damageable = (mState == P2LongLegsState::Wait || mState == P2LongLegsState::Flick
                         || mState == P2LongLegsState::Walk || mState == P2LongLegsState::Shot)
        || (mState == P2LongLegsState::Land && mFeetFired);
    output.enragedWalk = mParms.species == P2LongLegsSpecies::BigFoot && mEnraged
        && mState == P2LongLegsState::Walk;
    output.state = mState;
}
