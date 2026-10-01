#include "pc_p2_species_unit.h"
#include <cassert>
int main() {
    std::map<unsigned, int> t;
    assert(p2unit::parse("P2_SPECIES_UNITS_1\n28 2\n", t) && t.size() == 1 && t[28] == 2);
    std::map<unsigned, int> bad;
    assert(!p2unit::parse("P2_SPECIES_UNITS_2\n28 2\n", bad));
    assert(!p2unit::parse("P2_SPECIES_UNITS_1\n28 0\n", bad));
    assert(!p2unit::parse("P2_SPECIES_UNITS_1\n28 9\n", bad));
    assert(!p2unit::parse("P2_SPECIES_UNITS_1\n28\n", bad));
    std::map<unsigned, int> empty;
    assert(p2unit::parse("P2_SPECIES_UNITS_1\n", empty) && empty.empty());
    // A bulborb slot (count 1) becomes a pair; a grub trio (3) stays 3; unit 1 never shrinks.
    assert(p2unit::effectiveCount(1, 2) == 2);
    assert(p2unit::effectiveCount(3, 2) == 3);
    assert(p2unit::effectiveCount(2, 1) == 2);
    assert(p2unit::kSpacing < 300.0f);
    std::puts("p2_species_unit_test PASS");
    return 0;
}
