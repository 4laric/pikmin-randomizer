#include "pc_p2_snagret_fsm.h"

#include <cmath>

P2SnagretFsmParms p2SnagretParmsFor(P2SnagretSpecies species)
{
    P2SnagretFsmParms p;
    p.species = species;
    switch (species) {
    case P2SnagretSpecies::SnakeCrow:
        p.maxHealth = 1500.0f;
        p.wfgHealth = 2500.0f;
        p.buriedMinSeconds = 2.5f;   // fp12 disc
        p.diveNoTargetSeconds = 2.5f; // fp11 disc
        p.canWalk = false;
        break;
    case P2SnagretSpecies::SnakeWhole:
        p.maxHealth = 5000.0f;
        p.wfgHealth = 5000.0f;       // no cave health override
        p.buriedMinSeconds = 0.5f;
        p.diveNoTargetSeconds = 0.5f;
        p.canWalk = true;            // Walk/Home states
        break;
    }
    return p;
}

const char* P2SnagretFsm::stateName(P2SnagretState state)
{
    switch (state) {
    case P2SnagretState::Dead: return "Dead";
    case P2SnagretState::Stay: return "Stay";
    case P2SnagretState::Appear1: return "Appear1";
    case P2SnagretState::Appear2: return "Appear2";
    case P2SnagretState::Disappear: return "Disappear";
    case P2SnagretState::Wait: return "Wait";
    case P2SnagretState::Walk: return "Walk";
    case P2SnagretState::Home: return "Home";
    case P2SnagretState::Attack: return "Attack";
    case P2SnagretState::Eat: return "Eat";
    case P2SnagretState::Struggle: return "Struggle";
    }
    return "?";
}

const char* P2SnagretFsm::peckBoxName(P2SnagretPeckBox box)
{
    switch (box) {
    case P2SnagretPeckBox::None: return "none";
    case P2SnagretPeckBox::Near: return "near";
    case P2SnagretPeckBox::Normal: return "normal";
    case P2SnagretPeckBox::Far: return "far";
    case P2SnagretPeckBox::Right: return "right";
    case P2SnagretPeckBox::Left: return "left";
    }
    return "?";
}

P2SnagretPeckBox P2SnagretFsm::selectPeckBox(P2SnagretSpecies species,
                                             float forward, float lateral)
{
    const float lat = std::fabs(lateral);
    if (species == P2SnagretSpecies::SnakeCrow) {
        if (forward >= 0.0f && forward <= 80.0f && lat <= 30.0f) return P2SnagretPeckBox::Near;
        if (forward > 80.0f && forward <= 160.0f && lat <= 30.0f) return P2SnagretPeckBox::Normal;
        if (forward > 160.0f && forward <= 220.0f && lat <= 30.0f) return P2SnagretPeckBox::Far;
        if (forward >= 50.0f && forward <= 130.0f && lateral >= 50.0f && lateral <= 110.0f)
            return P2SnagretPeckBox::Right;
        if (forward >= 50.0f && forward <= 130.0f && lateral <= -50.0f && lateral >= -110.0f)
            return P2SnagretPeckBox::Left;
        return P2SnagretPeckBox::None;
    }
    // SnakeWhole: forward ranges widen, side boxes shift out by 30.
    if (forward >= 0.0f && forward <= 120.0f && lat <= 30.0f) return P2SnagretPeckBox::Near;
    if (forward > 120.0f && forward <= 180.0f && lat <= 30.0f) return P2SnagretPeckBox::Normal;
    if (forward > 180.0f && forward <= 260.0f && lat <= 30.0f) return P2SnagretPeckBox::Far;
    if (forward >= 80.0f && forward <= 160.0f && lateral >= 50.0f && lateral <= 110.0f)
        return P2SnagretPeckBox::Right;
    if (forward >= 80.0f && forward <= 160.0f && lateral <= -50.0f && lateral >= -110.0f)
        return P2SnagretPeckBox::Left;
    return P2SnagretPeckBox::None;
}

float P2SnagretFsm::strikeForward(P2SnagretSpecies species, P2SnagretPeckBox box)
{
    if (species == P2SnagretSpecies::SnakeCrow) {
        switch (box) {
        case P2SnagretPeckBox::Near: return 40.0f;
        case P2SnagretPeckBox::Normal: return 120.0f;
        case P2SnagretPeckBox::Far: return 190.0f;
        case P2SnagretPeckBox::Right: return 90.0f;
        case P2SnagretPeckBox::Left: return 90.0f;
        default: return 0.0f;
        }
    }
    switch (box) {
    case P2SnagretPeckBox::Near: return 60.0f;
    case P2SnagretPeckBox::Normal: return 150.0f;
    case P2SnagretPeckBox::Far: return 220.0f;
    case P2SnagretPeckBox::Right: return 120.0f;
    case P2SnagretPeckBox::Left: return 120.0f;
    default: return 0.0f;
    }
}

void P2SnagretFsm::reset(const P2SnagretFsmParms& parms)
{
    mParms = parms;
    mState = P2SnagretState::Stay;
    mStateTimer = 0.0f;
    mBuriedTimer = 0.0f;
    mStruggleTimer = 0.0f;
}

void P2SnagretFsm::emitPeck(const P2SnagretFsmInput& input, P2SnagretFsmOutput& output)
{
    const P2SnagretPeckBox box = selectPeckBox(mParms.species,
                                               input.targetForward, input.targetLateral);
    output.peckBox = box;
    output.strikeForward = strikeForward(mParms.species, box);
}

void P2SnagretFsm::enter(P2SnagretState next, const P2SnagretFsmInput& input,
                         P2SnagretFsmOutput& output)
{
    mState = next;
    mStateTimer = 0.0f;
    output.entered = true;
    switch (next) {
    case P2SnagretState::Stay:
        mBuriedTimer = 0.0f;
        break;
    case P2SnagretState::Appear1:
    case P2SnagretState::Appear2:
        output.surfaced = true; // each surfacing heals lifeIncrement (10)
        break;
    case P2SnagretState::Disappear:
        output.diveFlick = true; // dive key 2 flicks nearby creatures
        break;
    case P2SnagretState::Struggle:
        mStruggleTimer = 0.0f;
        break;
    case P2SnagretState::Dead:
        if (input.holdingTreasure)
            output.dropTreasure = true; // thrown from kutijnt1 at the death key
        output.leaveCorpse = true;
        break;
    default:
        break;
    }
}

void P2SnagretFsm::update(const P2SnagretFsmInput& input, P2SnagretFsmOutput& output)
{
    output = P2SnagretFsmOutput();
    output.state = mState;

    if (mState == P2SnagretState::Dead)
        return;

    if (input.killed) {
        enter(P2SnagretState::Dead, input, output);
        output.state = mState;
        return;
    }

    mStateTimer += kSourceDelta;

    switch (mState) {
    case P2SnagretState::Stay:
        mBuriedTimer += kSourceDelta;
        if (mBuriedTimer >= mParms.buriedMinSeconds && input.targetInTerritory) {
            const bool fast = input.roll < mParms.appear1Chance; // fp01 disc
            enter(fast ? P2SnagretState::Appear1 : P2SnagretState::Appear2, input, output);
        }
        break;

    case P2SnagretState::Appear1:
    case P2SnagretState::Appear2:
        if (input.animEnd)
            enter(P2SnagretState::Wait, input, output);
        break;

    case P2SnagretState::Wait:
        if (input.stuckPikmin && input.shakeThreshold) {
            enter(P2SnagretState::Disappear, input, output);
        } else if (input.latchedPikmin) {
            enter(P2SnagretState::Struggle, input, output);
        } else if (input.targetInPeckBox) {
            emitPeck(input, output);
            enter(P2SnagretState::Attack, input, output);
            emitPeck(input, output); // entering Attack pecks at the strike point
        } else if (mParms.canWalk && !input.targetInTerritory) {
            enter(P2SnagretState::Home, input, output);
        } else if (mParms.canWalk && input.targetInTerritory && input.facingTargetWithin30) {
            enter(P2SnagretState::Walk, input, output);
        }
        // SnakeCrow (or an unaligned SnakeWhole) keeps waiting and turning in place.
        break;

    case P2SnagretState::Walk:
        if (input.runKey2)
            output.hopRequested = true; // run1 key 2 launches the hop
        if (input.latchedPikmin) {
            enter(P2SnagretState::Struggle, input, output);
        } else if (input.targetInPeckBox) {
            emitPeck(input, output);
            enter(P2SnagretState::Attack, input, output);
            emitPeck(input, output);
        } else if (!input.targetInTerritory) {
            enter(P2SnagretState::Home, input, output);
        } else if (input.animEnd) {
            enter(P2SnagretState::Wait, input, output);
        }
        break;

    case P2SnagretState::Home:
        if (input.runKey2) {
            output.hopRequested = true;
            output.hopHome = true;
        }
        if (input.targetInPeckBox) {
            emitPeck(input, output);
            enter(P2SnagretState::Attack, input, output);
            emitPeck(input, output);
        } else if (input.targetInHome) {
            enter(P2SnagretState::Wait, input, output);
        } else if (input.animEnd) {
            enter(P2SnagretState::Wait, input, output);
        }
        break;

    case P2SnagretState::Attack:
        if (input.attackKey4) {
            if (input.latchedPikmin) {
                enter(P2SnagretState::Struggle, input, output);
            } else if (input.mouthSlotFree && input.targetInPeckBox) {
                emitPeck(input, output); // re-peck if a mouth slot is free
            } else {
                enter(P2SnagretState::Wait, input, output);
            }
        } else if (input.animEnd && !input.targetInPeckBox) {
            enter(P2SnagretState::Wait, input, output);
        }
        break;

    case P2SnagretState::Eat:
        // Assembly-retained in the decomp; not modelled in this slice.
        if (input.animEnd)
            enter(P2SnagretState::Wait, input, output);
        break;

    case P2SnagretState::Struggle:
        output.struggle = true;
        mStruggleTimer += kSourceDelta;
        if (mStruggleTimer >= mParms.struggleSeconds)
            enter(P2SnagretState::Wait, input, output);
        break;

    case P2SnagretState::Disappear:
        if (input.animEnd)
            enter(P2SnagretState::Stay, input, output);
        break;

    default:
        break;
    }

    output.bitterImmune = mState == P2SnagretState::Stay;
    output.state = mState;
}
