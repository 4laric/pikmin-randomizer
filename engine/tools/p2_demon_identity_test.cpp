// Lane 30 (#242) dedicated captor spawn-identity test (engine-free).
//
// Proves the identity/selection seam the ordinary Demon manager setup now uses
// instead of keying on the Dwarf Bulborb placeholder:
//   * the dedicated identity is the appended PC-only type (or the reserved
//     generator slot), and ordinary Dwarf Bulborb slots do not match it;
//   * the legacy converted-room placeholder is a separate, explicit-only
//     identity that never overlaps the dedicated one.
//
// The constant is static_asserted against TEKI_P2Demon inside the engine build
// (pc_port/pc_p2_demon_host.cpp); this binary only exercises the selection logic
// and the ABI-stable numeric value.
#include "pc_p2_demon_identity.h"

#include <cassert>
#include <cstdio>

int main()
{
    using namespace p2demonid;

    // The dedicated type identity matches regardless of the generator slot, so a
    // generated actor carrying TEKI_P2Demon is always selected.
    assert(isDedicatedCaptorIdentity(0u, kCaptorTekiType));
    assert(isDedicatedCaptorIdentity(123456u, kCaptorTekiType));
    assert(isDedicatedCaptorIdentity(kLegacyPlaceholderGeneratorId, kCaptorTekiType));

    // The reserved generator identity requires the placement-vehicle type.
    assert(isDedicatedCaptorIdentity(kCaptorGeneratorId, kPlacementVehicleTekiType));
    assert(!isDedicatedCaptorIdentity(kCaptorGeneratorId, 4));

    // An ordinary Dwarf Bulborb slot is NOT the dedicated captor identity.
    assert(!isDedicatedCaptorIdentity(kLegacyPlaceholderGeneratorId, kPlacementVehicleTekiType));
    assert(!isDedicatedCaptorIdentity(0u, kPlacementVehicleTekiType));
    assert(!isDedicatedCaptorIdentity(0u, 4));  // Spotty Bulborb
    assert(!isDedicatedCaptorIdentity(0u, -1)); // TEKI_NULL

    // The legacy placeholder is distinct and only matches its exact slot.
    assert(isLegacyPlaceholderIdentity(kLegacyPlaceholderGeneratorId, kLegacyPlaceholderTekiType));
    assert(!isLegacyPlaceholderIdentity(kCaptorGeneratorId, kPlacementVehicleTekiType));
    assert(!isLegacyPlaceholderIdentity(kLegacyPlaceholderGeneratorId, 4));
    assert(!isLegacyPlaceholderIdentity(kLegacyPlaceholderGeneratorId, kCaptorTekiType));

    // Dedicated and legacy identities never overlap, for any probed slot.
    const unsigned slots[] = {0u, kCaptorGeneratorId, kLegacyPlaceholderGeneratorId, 0xffffffffu};
    for (unsigned slot : slots) {
        for (int type = -1; type <= kCaptorTekiType; ++type) {
            const bool dedicated = isDedicatedCaptorIdentity(slot, type);
            const bool legacy = isLegacyPlaceholderIdentity(slot, type);
            assert(!(dedicated && legacy));
            // The dedicated type alone is enough; no legacy slot reaches it.
            if (type == kCaptorTekiType) assert(dedicated && !legacy);
        }
    }

    static_assert(kCaptorTekiType == 35, "lane-30 captor type id is part of the ABI contract");
    static_assert(kLegacyPlaceholderTekiType == kPlacementVehicleTekiType,
                  "the legacy placeholder is the P1 placement vehicle");
    std::puts("PASS P2_DEMON_IDENTITY");
    return 0;
}
