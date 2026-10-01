#include "pc_p2_purple_direct_policy.h"

#include <cassert>
#include <sstream>

int main()
{
    using namespace p2purpledirect;
    Config config;
    std::istringstream valid("P2_PURPLE_DIRECT_1 adult_fp36 50 adult_generators 2 7 4294967295");
    assert(parse(valid, config));
    assert(config.adultGenerators.size() == 2);

    std::istringstream dwarfOnly("P2_PURPLE_DIRECT_1 adult_fp36 50 adult_generators 0");
    assert(parse(dwarfOnly, config));
    assert(config.adultGenerators.empty());

    std::istringstream negative("P2_PURPLE_DIRECT_1 adult_fp36 50 adult_generators 1 -1");
    assert(!parse(negative, config));
    std::istringstream duplicate("P2_PURPLE_DIRECT_1 adult_fp36 50 adult_generators 2 9 9");
    assert(!parse(duplicate, config));
    std::istringstream wrongDamage("P2_PURPLE_DIRECT_1 adult_fp36 10 adult_generators 0");
    assert(!parse(wrongDamage, config));
    std::istringstream trailing("P2_PURPLE_DIRECT_1 adult_fp36 50 adult_generators 0 extra");
    assert(!parse(trailing, config));
}
