#include "pc_p2_purple_direct_policy.h"
#include <sstream>
#include <cassert>
int main() {
    using namespace p2purpledirect;
    Config c;
    std::istringstream valid("P2_PURPLE_DIRECT_2 bindings 2 100 1 200 2");
    assert(parse(valid,c) && c.campaign);
    // Absent-stage rows remain valid. Each later contact must match current
    // seed source; an actor address/host reused for another species cannot match.
    assert(c.source(100,1)==1 && c.source(200,2)==2);
    assert(c.source(100,2)==0 && c.source(200,33)==0 && c.source(300,2)==0);
    assert(c.source(0,1)==0 && c.source(200,0)==0);
    const char* bad[]={"P2_PURPLE_DIRECT_2 bindings -1", "P2_PURPLE_DIRECT_2 bindings 1025",
        "P2_PURPLE_DIRECT_2 bindings 1 0 1", "P2_PURPLE_DIRECT_2 bindings 1 4294967296 1",
        "P2_PURPLE_DIRECT_2 bindings 1 -1 2", "P2_PURPLE_DIRECT_2 bindings 1 100 33",
        "P2_PURPLE_DIRECT_2 bindings 2 100 1 100 2", "P2_PURPLE_DIRECT_2 bindings 1 100",
        "P2_PURPLE_DIRECT_2 bindings 0 extra", "P2_PURPLE_DIRECT_1 adult_fp36 20 adult_generators 0"};
    for (const char* text:bad) { std::istringstream in(text); assert(!parse(in,c)); assert(c.source(200,2)==2); }
    std::istringstream empty("P2_PURPLE_DIRECT_2 bindings 0"); assert(parse(empty,c)&&c.campaign&&c.bindings.empty());
    std::istringstream legacy("P2_PURPLE_DIRECT_1 adult_fp36 50 adult_generators 1 42");
    assert(parse(legacy,c)&&!c.campaign&&c.adultGenerators.count(42));
    assert(c.source(42,2)==0);
}
