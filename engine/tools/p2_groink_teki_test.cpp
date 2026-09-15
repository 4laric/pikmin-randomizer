// Lane 21 slice 2: the Groink carcass sidecar binding descriptor reader and the
// carcass config handoff it feeds. Keeps the ordinary actor binding contract in
// lock-step with the parked P2GroinkCarcass policy (no engine dependency).
#include "pc_p2_groink_carcass.h"
#include "pc_p2_groink_teki_policy.h"
#include <cassert>
#include <cstdio>
#include <sstream>
#include <string>

static p2groink::Binding parse(const std::string& text) {
    std::stringstream in(text);
    p2groink::Binding out;
    if (!p2groink::read(in, out)) out.generator = 0;
    return out;
}

int main() {
    {
        const p2groink::Binding b = parse("P2_GROINK_TEKI_1\n1\n123 0 30 10 1200\n");
        assert(b.generator == 123 && b.type == 0);
        assert(b.carcass.gaugeDelay == 30.0f && b.carcass.recoverySeconds == 10.0f && b.carcass.maxHealth == 1200.0f);
        P2GroinkCarcass cargo;
        assert(cargo.become(b.carcass));
    }
    // A zero generator cannot name a real actor.
    assert(parse("P2_GROINK_TEKI_1\n1\n0 0 30 10 1200\n").generator == 0);
    // Wrong magic, wrong count and trailing garbage are rejected.
    assert(parse("P2_GROINK_TEKI_2\n1\n123 0 30 10 1200\n").generator == 0);
    assert(parse("P2_GROINK_TEKI_1\n2\n123 0 30 10 1200\n").generator == 0);
    assert(parse("P2_GROINK_TEKI_1\n1\n123 0 30 10 1200 extra\n").generator == 0);
    // A descriptor that names a dead recovery rate must be refused by the policy
    // even though the reader itself accepts the tokens.
    {
        p2groink::Binding b = parse("P2_GROINK_TEKI_1\n1\n123 0 30 0 1200\n");
        assert(b.generator == 123);
        P2GroinkCarcass cargo;
        assert(!cargo.become(b.carcass));
    }
    std::puts("PASS p2_groink_teki_test");
    return 0;
}
