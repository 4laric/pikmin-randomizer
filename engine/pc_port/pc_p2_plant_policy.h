#pragma once
// Pure P2 plant-scenery policy for lane 23, family #171 (#448).
//
// Mirrors the plant section of experimental/pikmin2_flora_behavior.py and
// docs/PIKMIN2_FLORA_AUDIT.md (#171): one Plants::Obj base with an empty
// subclass per species and no FSM; general parameters are repurposed as LOD
// volumes (territory lifts the sphere; private/home radius define cylinders;
// fp01 on Clover and the brown figworts is the general floor offset); a
// generator carrying the Spectralid pellet sentinel spawns five yellow
// Spectralids on the plant's first touch, but only Tanpopo/Ooinu_l/Magaret
// declare the child and reserve slots. No engine types, no side effects.
//
// The audit's floor-offset reading of Clover (25) conflicts with the asset
// contract (#353): the general fp01 is 40.0 and 25.0 is an inert trailing
// block. Both are recorded; the runtime uses the asset-contract value and flags
// it reconstructed, as the Python model does.
#include <cmath>
#include <cstdint>
#include <istream>
#include <stdexcept>
#include <string>
#include <vector>

namespace p2plant {

// enemyInfo.h:105-111 (Tanpopo..Wakame_l) and :139-151 (Tukushi..KareOoinu_l).
enum class Species {
	Tanpopo,
	Clover,
	HikariKinoko,
	Ooinu_s,
	Ooinu_l,
	Wakame_s,
	Wakame_l,
	Tukushi,
	Watage,
	DaiodoRed,
	DaiodoGreen,
	Magaret,
	Nekojarashi,
	Chiyogami,
	Zenmai,
	KareOoinu_s,
	KareOoinu_l,
};

// Repurposed general parameters (PLANT_LOD_ROLES).
enum class Volume { Territory, PrivateRadius, HomeRadius, Fp01 };

// Geometric role of a repurposed general parameter (audit lines 99-102).
enum class LodRole { LiftedSphere, Cylinder, FloorOffset, None };

inline const char* speciesName(Species species)
{
	switch (species) {
	case Species::Tanpopo:
		return "Tanpopo";
	case Species::Clover:
		return "Clover";
	case Species::HikariKinoko:
		return "HikariKinoko";
	case Species::Ooinu_s:
		return "Ooinu_s";
	case Species::Ooinu_l:
		return "Ooinu_l";
	case Species::Wakame_s:
		return "Wakame_s";
	case Species::Wakame_l:
		return "Wakame_l";
	case Species::Tukushi:
		return "Tukushi";
	case Species::Watage:
		return "Watage";
	case Species::DaiodoRed:
		return "DaiodoRed";
	case Species::DaiodoGreen:
		return "DaiodoGreen";
	case Species::Magaret:
		return "Magaret";
	case Species::Nekojarashi:
		return "Nekojarashi";
	case Species::Chiyogami:
		return "Chiyogami";
	case Species::Zenmai:
		return "Zenmai";
	case Species::KareOoinu_s:
		return "KareOoinu_s";
	case Species::KareOoinu_l:
		return "KareOoinu_l";
	}
	throw std::runtime_error("unknown plant species");
}

inline Species speciesFromName(const std::string& name)
{
	if (name == "Tanpopo") {
		return Species::Tanpopo;
	}
	if (name == "Clover") {
		return Species::Clover;
	}
	if (name == "HikariKinoko") {
		return Species::HikariKinoko;
	}
	if (name == "Ooinu_s") {
		return Species::Ooinu_s;
	}
	if (name == "Ooinu_l") {
		return Species::Ooinu_l;
	}
	if (name == "Wakame_s") {
		return Species::Wakame_s;
	}
	if (name == "Wakame_l") {
		return Species::Wakame_l;
	}
	if (name == "Tukushi") {
		return Species::Tukushi;
	}
	if (name == "Watage") {
		return Species::Watage;
	}
	if (name == "DaiodoRed") {
		return Species::DaiodoRed;
	}
	if (name == "DaiodoGreen") {
		return Species::DaiodoGreen;
	}
	if (name == "Magaret") {
		return Species::Magaret;
	}
	if (name == "Nekojarashi") {
		return Species::Nekojarashi;
	}
	if (name == "Chiyogami") {
		return Species::Chiyogami;
	}
	if (name == "Zenmai") {
		return Species::Zenmai;
	}
	if (name == "KareOoinu_s") {
		return Species::KareOoinu_s;
	}
	if (name == "KareOoinu_l") {
		return Species::KareOoinu_l;
	}
	throw std::runtime_error("unknown plant species");
}

inline LodRole lodRole(Species species, Volume volume)
{
	(void)species;
	switch (volume) {
	case Volume::Territory:
		return LodRole::LiftedSphere;
	case Volume::PrivateRadius:
	case Volume::HomeRadius:
		return LodRole::Cylinder;
	case Volume::Fp01:
		// Only Clover and the brown figworts carry the general floor offset.
		if (species == Species::Clover || species == Species::KareOoinu_s || species == Species::KareOoinu_l) {
			return LodRole::FloorOffset;
		}
		return LodRole::None;
	}
	throw std::runtime_error("unknown LOD volume");
}

inline const char* lodRoleName(LodRole role)
{
	switch (role) {
	case LodRole::LiftedSphere:
		return "lifted_sphere";
	case LodRole::Cylinder:
		return "cylinder";
	case LodRole::FloorOffset:
		return "floor_offset";
	case LodRole::None:
		return "none";
	}
	throw std::runtime_error("unknown LOD role");
}

// General floor offset on disc. Clover uses the asset-contract general fp01
// 40.0 (reconstructed relative to the audit's inert 25.0); KareOoinu_s/l keep
// their recorded 45/20. Species without the floor role return 0.
inline float floorOffset(Species species)
{
	switch (species) {
	case Species::Clover:
		return 40.0f;
	case Species::KareOoinu_s:
		return 45.0f;
	case Species::KareOoinu_l:
		return 20.0f;
	default:
		return 0.0f;
	}
}

inline bool floorOffsetReconstructed(Species species)
{
	// The audit's "floor offset" reading conflicts with the asset contract for
	// Clover; the brown-figwort small/large assignment is unstated.
	return species == Species::Clover || species == Species::KareOoinu_s || species == Species::KareOoinu_l;
}

// Spectralid sentinel (plants.cpp:187-201): five yellow Spectralids on first
// touch when the generator carries the sentinel.
inline constexpr int SpectralidPerTouch = 5;

inline bool spectralidReserved(Species species)
{
	return species == Species::Tanpopo || species == Species::Ooinu_l || species == Species::Magaret;
}

// Sentinel decision for a plant. Spawn is the source path (the native module
// cannot reach the lane-15 Qurione module's spawn interface and reports that as
// BLOCKED); SuppressedNoSlot is the slot rule; None means no sentinel.
enum class SentinelDecision { None, Spawn, SuppressedNoSlot };

inline SentinelDecision spectralidDecision(Species species, bool hasSentinel, bool firstTouch)
{
	if (!hasSentinel || !firstTouch) {
		return SentinelDecision::None;
	}
	return spectralidReserved(species) ? SentinelDecision::Spawn : SentinelDecision::SuppressedNoSlot;
}

inline const char* sentinelDecisionName(SentinelDecision decision)
{
	switch (decision) {
	case SentinelDecision::None:
		return "none";
	case SentinelDecision::Spawn:
		return "spawn";
	case SentinelDecision::SuppressedNoSlot:
		return "suppressed_no_slot";
	}
	throw std::runtime_error("unknown sentinel decision");
}

// Sway-on-touch: a captain or Pikmin moving faster than 1 unit past the
// collision volume restarts the single clip; only captains trigger the sound.
inline constexpr float SwayMinSpeed = 1.0f;

inline bool sways(const std::string& mover, float speed, bool pastVolume)
{
	if (!std::isfinite(speed)) {
		throw std::runtime_error("invalid sway speed");
	}
	if (mover == "purple_quake") {
		return true;
	}
	if (mover == "enemy") {
		return false;
	}
	if (mover != "captain" && mover != "pikmin") {
		throw std::runtime_error("unknown mover kind");
	}
	return pastVolume && std::fabs(speed) > SwayMinSpeed;
}

inline bool touchSound(const std::string& mover)
{
	if (mover != "captain" && mover != "pikmin" && mover != "purple_quake" && mover != "enemy") {
		throw std::runtime_error("unknown mover kind");
	}
	return mover == "captain";
}

// Scale clamp for the native sizing step (bounded, finite).
inline float clampScale(float value)
{
	if (!std::isfinite(value)) {
		throw std::runtime_error("invalid plant scale");
	}
	if (value < 0.25f) {
		return 0.25f;
	}
	if (value > 4.0f) {
		return 4.0f;
	}
	return value;
}

inline float clampFloorOffset(float value)
{
	if (!std::isfinite(value)) {
		throw std::runtime_error("invalid floor offset");
	}
	if (value < 0.0f) {
		return 0.0f;
	}
	if (value > 100.0f) {
		return 100.0f;
	}
	return value;
}

// One sidecar row.
struct PlantSpec {
	std::uint32_t generator = 0;
	Species species         = Species::Clover;
	float lodScale          = 1.0f;
	float floorOffset       = 0.0f;
	bool sentinel           = false;
};

// Strict P2_PLANT_1: <count> rows of
// <generator> <species> <lod_scale> <floor_offset> <sentinel 0|1>.
inline std::vector<PlantSpec> readPlants(std::istream& in)
{
	std::string header;
	int count = 0;
	if (!(in >> header >> count) || header != "P2_PLANT_1" || count < 1 || count > 64) {
		throw std::runtime_error("invalid P2_PLANT_1 header");
	}
	std::vector<PlantSpec> out;
	out.reserve(static_cast<std::size_t>(count));
	for (int i = 0; i < count; ++i) {
		unsigned long long generator = 0;
		std::string speciesWord;
		float scale = 0.0f, floor = 0.0f;
		int sentinel = 0;
		if (!(in >> generator >> speciesWord >> scale >> floor >> sentinel) || generator > 0xffffffffULL
		    || !std::isfinite(scale) || !std::isfinite(floor) || (sentinel != 0 && sentinel != 1)) {
			throw std::runtime_error("invalid P2_PLANT_1 row");
		}
		PlantSpec spec;
		spec.generator   = static_cast<std::uint32_t>(generator);
		spec.species     = speciesFromName(speciesWord);
		spec.lodScale    = scale;
		spec.floorOffset = floor;
		spec.sentinel    = sentinel != 0;
		for (const PlantSpec& other : out) {
			if (other.generator == spec.generator) {
				throw std::runtime_error("duplicate generator");
			}
		}
		out.push_back(spec);
	}
	std::string trailing;
	if (in >> trailing) {
		throw std::runtime_error("trailing P2_PLANT_1 data");
	}
	return out;
}

} // namespace p2plant
