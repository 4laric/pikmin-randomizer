#include "pc_p2_sokkuri_flick.h"
#include <cassert>
#include <cstdio>
#include <cstring>

using namespace p2sokkuriflick;

int main() {
    // A fresh Skitter Leaf never shakes; the owner-reported "flicks whenever a
    // Pikmin is near" is not a source trigger, so zero hits must never start it.
    assert(!isStartFlick(0.0f, 0));
    assert(!isStartFlick(0.0f, 20));
    // Retail parms: the third damaging hit arms the shake, not the first two.
    assert(!isStartFlick(1.0f, 0));
    assert(!isStartFlick(2.0f, 0));
    assert(isStartFlick(3.0f, 0));
    assert(hitsToShake() == 3);
    // The rounding term is +0.5 before truncation: 2.49 still below, 2.5 arms.
    assert(!isStartFlick(2.49f, 0));
    assert(isStartFlick(2.5f, 0));
    // Every stuck-count tier shares blow threshold 2, so stuck Pikmin do not
    // change the trigger.
    for (int stuck = 0; stuck <= 20; ++stuck) {
        assert(!isStartFlick(2.0f, stuck));
        assert(isStartFlick(3.0f, stuck));
    }
    // After the shake the timer is zeroed: three more hits are needed.
    float timer = 3.0f;
    assert(isStartFlick(timer, 0));
    timer = 0.0f;
    timer += FlickPerHit; assert(!isStartFlick(timer, 0));
    timer += FlickPerHit; assert(!isStartFlick(timer, 0));
    timer += FlickPerHit; assert(isStartFlick(timer, 0));
    // A Pikmin is never damaged by the shake (source ignores the argument).
    assert(PikiDamage == 0.0f);
    assert(ShakeRange == 40.0f && ShakeKnockback == 50.0f && ShakeChance == 1.0f);
    // Carcass uses the Carry clip, looping.
    assert(std::strcmp(carcassClip(), "type5") == 0);
    assert(carcassPhase(0.0, 40.0f / 30.0f) == 0.0f);
    const float half = carcassPhase(20.0 / 30.0, 40.0f / 30.0f);
    assert(half > 0.49f && half < 0.51f);
    const float wrapped = carcassPhase(60.0 / 30.0, 40.0f / 30.0f);
    assert(wrapped > 0.49f && wrapped < 0.51f);
    std::puts("p2_sokkuri_flick_test PASS");
    return 0;
}
