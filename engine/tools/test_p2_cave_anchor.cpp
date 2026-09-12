#include "pc_p2_cave_anchor.h"
#include <cassert>
#include <sstream>
#include <limits>
int main(){
    P2CaveAnchor anchor;
    std::istringstream input("P2_CAVE_TRANSITION_1 hole 10 5 -30 50\n");
    assert(p2_cave_read_anchor(input,1,anchor));
    assert(anchor.contains(10,5,-30));
    assert(anchor.contains(60,45,-30));
    assert(!anchor.contains(60.01f,5,-30));
    assert(!anchor.contains(10,45.01f,-30));
    assert(!anchor.contains(std::numeric_limits<float>::quiet_NaN(),5,-30));
    for(const char* text:{"P2_CAVE_TRANSITION_1 geyser 0 0 0 50", "P2_CAVE_TRANSITION_1 hole 0 0 0 19",
        "P2_CAVE_TRANSITION_1 hole 0 0 0 151", "P2_CAVE_TRANSITION_1 hole 0 0 0 50 extra",
        "P2_CAVE_TRANSITION_1 hole nan 0 0 50", "P2_CAVE_TRANSITION_1 hole 100001 0 0 50",
        "P2_CAVE_TRANSITION_1 hole 0 0 0"}){
        std::istringstream bad(text);assert(!p2_cave_read_anchor(bad,1,anchor));
        assert(anchor.x==10); // A rejected candidate never partially mutates live geometry.
    }
    std::istringstream exit("P2_CAVE_TRANSITION_1 geyser 0 0 0 75");
    assert(p2_cave_read_anchor(exit,2,anchor));
    return 0;
}
