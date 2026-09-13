#include "TAI/Action.h"
#include "teki.h"

#include <cassert>

struct LifecycleAction : TaiAction {
    LifecycleAction() : TaiAction(TAI_NO_TRANSIT) {}
    void start(Teki& teki) override { ++teki.startCount; }
    void finish(Teki& teki) override { ++teki.finishCount; }
};

struct DamageAction : TaiAction {
    DamageAction() : TaiAction(TAI_NO_TRANSIT) {}
    bool act(Teki& teki) override
    {
        ++teki.damageCount;
        teki.mHealth -= teki.mStoredDamage;
        teki.mStoredDamage = 0.0f;
        return true;
    }
};

struct DeathAction : TaiAction {
    explicit DeathAction(int next) : TaiAction(next) {}
    bool act(Teki& teki) override
    {
        if (teki.mHealth > 0.0f) return false;
        ++teki.deathCount;
        return true;
    }
};

struct StunAction : TaiAction {
    StunAction() : TaiAction(TAI_NO_TRANSIT) {}
    bool act(Teki& teki) override { ++teki.stunCount; return false; }
};

int main()
{
    LifecycleAction ordinaryLifecycle;
    LifecycleAction impactLifecycle;
    TaiState ordinary(1);
    ordinary.setAction(0, &ordinaryLifecycle);
    TaiState impact(1);
    impact.setAction(0, &impactLifecycle);
    TaiStrategy strategy(2, 0);
    strategy.setState(0, &ordinary);
    strategy.setState(1, &impact);

    Teki actor;
    strategy.start(actor);
    strategy.act(actor);
    assert(actor.startCount == 1);
    assert(actor.finishCount == 0);
    assert(strategy.transit(actor, 1));
    assert(actor.finishCount == 1);
    assert(actor.mStateID == 1);
    assert(actor.mReturnStateID == 0);
    assert(actor.mIsStateReady);
    strategy.act(actor);
    assert(actor.startCount == 2);

    // A repeated impact cannot replace the original return state with itself
    // or finish/restart the active impact state.
    assert(strategy.transit(actor, 1));
    assert(actor.mReturnStateID == 0);
    assert(actor.finishCount == 1);
    assert(actor.startCount == 2);
    assert(!strategy.transit(actor, -1));
    assert(!strategy.transit(actor, 2));

    DamageAction damage;
    DeathAction death(0);
    StunAction stun;
    TaiState ordered(3);
    ordered.setAction(0, &damage);
    ordered.setAction(1, &death);
    ordered.setAction(2, &stun);
    TaiStrategy orderedStrategy(2, 1);
    orderedStrategy.setState(0, &ordinary);
    orderedStrategy.setState(1, &ordered);
    Teki lethal;
    lethal.mHealth = 5.0f;
    lethal.mStoredDamage = 5.0f;
    orderedStrategy.start(lethal);
    orderedStrategy.act(lethal);
    assert(lethal.damageCount == 1);
    assert(lethal.deathCount == 1);
    assert(lethal.stunCount == 0);
    assert(lethal.mStateID == 0);
    assert(lethal.mReturnStateID == 1);
    assert(lethal.mIsStateReady);
}
