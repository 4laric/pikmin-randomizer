#include "pc_p2_groink_lifetime.h"
#include <cassert>
#include <cstdio>
int main() {
    P2GroinkLifetime guard;
    assert(!guard.attach(0).generation);
    auto old=guard.attach(123); assert(guard.accepts(old));
    assert(!guard.attach(456).generation);
    auto ticket=guard.beginRevival(old); assert(ticket&&!guard.accepts(old));
    assert(!guard.beginRevival(old)); assert(!guard.attach(123).generation);
    assert(!guard.finishRevival(ticket+1,123).generation);
    auto replacement=guard.finishRevival(ticket,123);
    assert(replacement.address==old.address&&replacement.generation!=old.generation);
    assert(guard.accepts(replacement)&&!guard.accepts(old));
    assert(!guard.finishRevival(ticket,123).generation&&guard.accepts(replacement));
    assert(!guard.detach(old)&&guard.accepts(replacement));
    ticket=guard.beginRevival(replacement); assert(!guard.finishRevival(ticket,0).generation);
    assert(!guard.accepts(replacement));
    assert(!guard.finishRevival(ticket,456).generation);
    auto fresh=guard.attach(456); assert(guard.accepts(fresh));
    ticket=guard.beginRevival(fresh); guard.reset();
    assert(!guard.finishRevival(ticket,456).generation);
    auto afterReset=guard.attach(456); assert(guard.accepts(afterReset)&&!guard.accepts(fresh));
    assert(guard.detach(afterReset)&&!guard.accepts(afterReset));
    auto same=guard.attach(456); assert(guard.accepts(same)&&!guard.accepts(afterReset));
    guard.reset(); assert(!guard.accepts(same));
    puts("p2_groink_lifetime_test PASS");
}
