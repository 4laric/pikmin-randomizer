// Native flora hookup bridge implementation (#723, issue #723).
//
// Compiled into the guarded fixture via include (same accepted pattern as
// the integrated boot fixtures): no CMake target exists for this bridge yet,
// and registering one needs #186 review. The header stays engine-free; this
// TU only adds <cstdio> marker emission around the policy calls.
#include <cstdio>

#include "pc_p2_flora_hookup.h"

namespace p2florahookup {
namespace {

const char* speciesName(p2flora::Species species)
{
    switch (species) {
    case p2flora::Pelplant: return "Pelplant";
    case p2flora::BluePom: return "BluePom";
    case p2flora::RedPom: return "RedPom";
    case p2flora::YellowPom: return "YellowPom";
    case p2flora::BlackPom: return "BlackPom";
    case p2flora::WhitePom: return "WhitePom";
    case p2flora::RandPom: return "RandPom";
    default: return "Unknown";
    }
}

} // namespace

bool hookupAdmit(const HookupFacts& facts)
{
    if (facts.species < 0 || facts.species >= p2flora::SpeciesCount) return false;
    if (facts.swallowed < 0) return false;
    if (facts.pikiKind < 0 || facts.pikiKind > 6) return false;
    return true;
}

int hookupConvert(const HookupFacts& facts)
{
    if (!hookupAdmit(facts)) {
        std::printf("P2_FLORA_HOOKUP_ADMIT species=%s swallowed=%d ok=0\n",
                    speciesName(p2flora::isCandypop(facts.species) || facts.species == p2flora::Pelplant
                                ? facts.species : p2flora::SpeciesCount),
                    facts.swallowed);
        std::fflush(stdout);
        return -1;
    }
    std::printf("P2_FLORA_HOOKUP_ADMIT species=%s swallowed=%d ok=1\n",
                speciesName(facts.species), facts.swallowed);
    p2flora::ConvertResult got = p2flora::convertSwallow(
        {facts.species, facts.swallowed, facts.ownColour});
    if (!got.ok) {
        std::printf("P2_FLORA_HOOKUP_CONVERT species=%s ok=0\n",
                    speciesName(facts.species));
        std::fflush(stdout);
        return -1;
    }
    std::printf("P2_FLORA_HOOKUP_CONVERT species=%s sprouts=%d slots=%d refund=%d\n",
                speciesName(facts.species), got.sprouts, got.slotsUsed,
                int(got.refund));
    int received = 0;
    for (int i = 0; i < got.sprouts; ++i) {
        std::printf("P2_FLORA_HOOKUP_SPROUT species=%s index=%d received=1\n",
                    speciesName(facts.species), i);
        ++received;
    }
    std::fflush(stdout);
    return received;
}

int hookupBindScenery(p2flora::SceneryRegistry& registry, const char* identity, int slot)
{
    const int at = registry.registerProp(identity, slot);
    std::printf("P2_FLORA_HOOKUP_SCENERY identity=%s slot=%d bound=%d\n",
                identity ? identity : "(null)", slot, at);
    std::fflush(stdout);
    return at;
}

int p2_flora_hookup_suite()
{
    int failures = 0;
    // Fixed live-facts session: BluePom swallow 3, queen swallow 1, Pelplant 5.
    if (hookupConvert({p2flora::BluePom, 3, false, 2}) != 3) ++failures;
    if (hookupConvert({p2flora::RandPom, 1, false, 6}) != 9) ++failures;
    if (hookupConvert({p2flora::Pelplant, 5, false, 0}) != 5) ++failures;
    // Refusals stay silent except for the ADMIT line.
    if (hookupConvert({p2flora::BluePom, -1, false, 2}) != -1) ++failures;
    if (hookupConvert({p2flora::SpeciesCount, 1, false, 0}) != -1) ++failures;
    if (hookupConvert({p2flora::BluePom, 1, false, 9}) != -1) ++failures;
    p2flora::SceneryRegistry registry;
    if (hookupBindScenery(registry, "Clover", 0) != 0) ++failures;
    if (hookupBindScenery(registry, "Clover", 1) != -1) ++failures;
    std::printf("P2_FLORA_HOOKUP_DONE failures=%d\n", failures);
    std::fflush(stdout);
    return failures;
}

} // namespace p2florahookup
