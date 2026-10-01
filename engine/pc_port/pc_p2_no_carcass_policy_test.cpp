// #1088 engine-free contract for the P2 species that leave no carcass.
#include "pc_p2_no_carcass_policy.h"
#include <cassert>
#include <cstdio>
#include <initializer_list>

int main() {
    using namespace p2nocarcass;
    // Exactly the five sources the owner ruled on (2026-10-01).
    for (unsigned s : {31u, 57u, 66u, 69u, 72u}) assert(leavesNoCarcass(s));
    int count = 0;
    for (unsigned s = 0; s < 256; ++s) count += leavesNoCarcass(s) ? 1 : 0;
    assert(count == 5);
    // Their vehicle corpse is suppressed; every other source keeps the vehicle value.
    for (unsigned s : {31u, 57u, 66u, 69u, 72u}) { assert(corpseType(s, 1) == 0); assert(corpseType(s, 0) == 0); }
    for (unsigned s : {0u, 2u, 30u, 32u, 56u, 73u}) { assert(corpseType(s, 1) == 1); assert(corpseType(s, 0) == 0); }
    // Only a killed actor earns the receipt; a teardown that is not a death does not,
    // and an unbound actor (source 0) or a corpse-leaving source never does here.
    for (unsigned s : {31u, 57u, 66u, 69u, 72u}) {
        assert(killEarnsReceipt(s, false));
        assert(!killEarnsReceipt(s, true));
    }
    assert(!killEarnsReceipt(0, false));
    assert(!killEarnsReceipt(30, false));
    std::puts("p2_no_carcass_policy_test ok");
    return 0;
}
