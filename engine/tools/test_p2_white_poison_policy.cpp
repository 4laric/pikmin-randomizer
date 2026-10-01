#include "pc_p2_white_poison_policy.h"
#include <cassert>

int main() {
    P2WhitePoisonEvents events;
    int predator = 0, first = 0, second = 0;
    assert(!events.prepare(nullptr, &first));
    assert(events.prepare(&predator, &first));
    assert(!events.prepare(&predator, &first));
    // A failed kill cancels its prepared event; a later attempt can retry.
    assert(events.commit(&predator, &first));
    assert(events.prepare(&predator, &first));
    assert(events.prepare(&predator, &second));
    assert(events.commit(&predator, &first));
    assert(!events.commit(&predator, &first));
    assert(events.commit(&predator, &second));
    // A later actor lifecycle may reuse the same pool address.
    assert(events.prepare(&predator, &first));
    assert(events.commit(&predator, &first));
    assert(events.prepare(&predator, &first));
    events.forgetPredator(&predator);
    assert(!events.commit(&predator, &first));
    events.reset();
    assert(!events.commit(&predator, &first));
}
