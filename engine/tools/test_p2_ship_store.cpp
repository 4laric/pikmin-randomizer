#include "pc_p2_ship_store.h"
#include <cassert>
#include <sstream>
int main() {
    p2ship::Store s;
    for (int species : {3, 4}) for (int maturity : {0, 1, 2}) assert(s.add(species, maturity));
    assert(s.total() == 6);
    assert(!s.add(1, 0) && !s.add(3, 3) && !s.take(3, -1));
    assert(s.take(3, 2) && !s.take(3, 2));
    std::ostringstream out; s.write(out);
    std::istringstream in(out.str()); p2ship::Store copy; assert(copy.read(in));
    assert(copy.total() == 5 && copy.counts[1][2] == 1);
    for (const char* bad : {"-1 0 0 0 0 0", "0 0 0 0 0", "100000 1 0 0 0 0", "2147483648 0 0 0 0 0"}) {
        std::istringstream malformed(bad); assert(!copy.read(malformed)); assert(copy.total() == 5);
    }
    std::istringstream full("100000 0 0 0 0 0"); assert(copy.read(full));
    assert(!copy.add(3, 2) && copy.total() == 100000);
}
