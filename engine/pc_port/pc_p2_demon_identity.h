#pragma once

// Lane 30 (#242, parent #166) dedicated captor spawn identity.
//
// The private P2DemonHost binds to whichever actor the converted room generator
// spawns. Historically that was any single Dwarf Bulborb (`TEKI_Chappy`), so the
// "ordinary spawned captor" identity was a placeholder. This header names the
// opt-in, PC-only identity the ordinary manager setup selects instead.
//
// Two additive PC-only identities exist:
//   * a dedicated appended teki type, `TEKI_P2Demon` (see include/teki.h). The
//     spawned actor carries the distinct type id, so the binding no longer keys
//     on the Dwarf Bulborb type at all.
//   * a reserved generator identity (`Generator::_70`) for a stager that tags the
//     lane-30 slot while keeping the P1 placement-vehicle type.
//
// The type id is repeated here as a plain integer so this header stays
// engine-free and unit-testable; `pc_p2_demon_host.cpp` static_asserts that it
// equals `TEKI_P2Demon`. Default behavior is unchanged: nothing selects this
// identity unless the ordinary opt-in path is enabled.
namespace p2demonid {

// PC-only appended captor type (`include/teki.h`). Retail types 0-34 are
// untouched and `TEKI_TypeCount` remains 35 on non-PC builds.
constexpr int kCaptorTekiType = 35;

// P1 placement-vehicle type the converted private room currently uses
// (`TEKI_Chappy`).
constexpr int kPlacementVehicleTekiType = 3;

// Reserved generator identity (`Generator::_70`, four-character readID 'dmn0')
// for the lane-30 captor slot.
constexpr unsigned kCaptorGeneratorId = 0x646D6E30u;

// Legacy converted private room's Dwarf Bulborb generator id. Kept only as an
// explicitly opt-in fallback so existing fixtures stay reproducible.
constexpr unsigned kLegacyPlaceholderGeneratorId = 385875968u;
constexpr int kLegacyPlaceholderTekiType = 3;

// True when a spawned actor carries the dedicated lane-30 captor identity: the
// appended PC-only type, or the reserved generator slot with the placement
// vehicle. Ordinary Dwarf Bulborb slots do not match.
inline bool isDedicatedCaptorIdentity(unsigned generatorId, int tekiType)
{
    if (tekiType == kCaptorTekiType) {
        return true;
    }
    return generatorId == kCaptorGeneratorId && tekiType == kPlacementVehicleTekiType;
}

// The legacy Dwarf Bulborb placeholder identity. Accepted only behind an
// explicit opt-in; it is never part of the dedicated captor identity.
inline bool isLegacyPlaceholderIdentity(unsigned generatorId, int tekiType)
{
    return generatorId == kLegacyPlaceholderGeneratorId && tekiType == kLegacyPlaceholderTekiType;
}

} // namespace p2demonid
