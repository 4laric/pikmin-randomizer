#pragma once
#include <cstdint>
#include <cstring>

// GPVE01 OlimarData::ItemIndex, item_config order and Treasure Hoard numbers.
// Ownership is a projection of authenticated treasury receipts, never assets.
namespace p2equipment {
enum Item { BruteKnuckles, DreamMaterial, AmplifiedAmplifier, ProfessionalNoisemaker,
    StellarOrb, JusticeAlloy, ForgedCourage, RepugnantAppendage, PrototypeDetector,
    FiveManNapsack, SphericalAtlas, GeographicProjection, TheKey, Count };
struct Source { const char* id; int dictionary; };
constexpr Source Sources[Count] = {{"fue_a",188},{"fue_b",192},{"fue_wide",194},
    {"fue_pullout",195},{"light_a",190},{"suit_powerup",193},{"suit_fire",191},
    {"dashboots",189},{"radar_a",186},{"radar_b",187},{"map01",184},{"map02",185},{"key",196}};
inline int item(const char* id) {
    if (id) for (int i=0;i<Count;++i) if (!std::strcmp(id,Sources[i].id)) return i;
    return -1;
}
struct Kit {
    std::uint16_t bits = 0;
    bool has(int index) const {
        // TheKey never occupies an OlimarData bit (source exclusive bound 12).
        return index >= 0 && index < TheKey && (bits & (1u << index));
    }
    unsigned courses() const {
        return 1u | (has(SphericalAtlas)?2u:0u) | (has(GeographicProjection)?4u:0u);
    }
    float damage(float original) const { return has(JusticeAlloy)?original*0.5f:original; }
    float whistle(float original) const { return has(AmplifiedAmplifier)?200.0f:original; }
    float speed(float original) const { return has(RepugnantAppendage)?240.0f:original; }
};
template<class Seen> Kit project(Seen seen) {
    Kit kit;
    for (int i=0;i<TheKey;++i) if (seen(Sources[i].id)) kit.bits |= 1u << i;
    return kit;
}
}
