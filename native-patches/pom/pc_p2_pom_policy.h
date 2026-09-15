#pragma once
// Pure P2 Candypop Bud policy for lane 23, family #171 (#448).
//
// Mirrors the Candypop section of experimental/pikmin2_flora_behavior.py and
// docs/PIKMIN2_FLORA_AUDIT.md (#171): one class for the six buds (BluePom 3 ..
// RandPom 8), never the nonspawnable shared base Pom (82); a lifetime slot
// budget ip01 = 5 for colour buds and ip11 = 1 for the Queen (RandPom); an
// own-colour throw refunds the slot on colour buds only; the bud closes fp01 =
// 1.0 s after the last swallow or when the budget is spent; close goes to
// "shot" when Pikmin are inside, else it reopens; each swallowed Pikmin is
// replaced by ip13 = 9 leaf sprouts for the Queen or 1 otherwise; the Queen
// cycles Blue/Red/Yellow deterministically every fp02 = 2.6 s; Violet
// (BlackPom) and Ivory (WhitePom) carry the story-cave spawn cap. No engine
// types, no side effects.
#include <cmath>
#include <cstdint>
#include <istream>
#include <stdexcept>
#include <string>
#include <vector>

namespace p2pom {

// enemyInfo.h:62-67 (BluePom..RandPom = 3-8) and :141 (Pom = 82).
enum class Species {
	BluePom   = 3,
	RedPom    = 4,
	YellowPom = 5,
	BlackPom  = 6,
	WhitePom  = 7,
	RandPom   = 8,
	PomBase   = 82,
};

// POM_PROPER_DISC (enemy/parm/enemyParms.szs pom/enemyparm.txt).
inline constexpr int IpTtlBudget     = 5;    // ip01
inline constexpr int QueenBudget     = 1;    // ip11
inline constexpr int QueenShotMul    = 9;    // ip13
inline constexpr float RemainOpenSec = 1.0f; // fp01
inline constexpr float QueenCycleSec = 2.6f; // fp02
inline constexpr float LaunchVert    = 750.0f; // POM_SPROUT_LAUNCH y
inline constexpr float LaunchHoriz   = 110.0f;

// POM_SLOT (Pom.cpp:154-201): press-only entry, any colour accepted.
inline constexpr float SlotRadius = 30.0f;

// POM_COLOUR_CAP / spawn gating (PomMgr.cpp:38-89).
inline constexpr int VioletIvoryCap          = 20;
inline constexpr int EarlyFloorFirst         = 1;
inline constexpr int EarlyFloorLast          = 2;
inline constexpr const char* WhiteFlowerGarden = "White Flower Garden";

inline bool isBase(Species species)
{
	return species == Species::PomBase;
}

inline int speciesId(Species species)
{
	return static_cast<int>(species);
}

inline const char* speciesName(Species species)
{
	switch (species) {
	case Species::BluePom:
		return "BluePom";
	case Species::RedPom:
		return "RedPom";
	case Species::YellowPom:
		return "YellowPom";
	case Species::BlackPom:
		return "BlackPom";
	case Species::WhitePom:
		return "WhitePom";
	case Species::RandPom:
		return "RandPom";
	case Species::PomBase:
		return "Pom";
	}
	throw std::runtime_error("unknown species");
}

inline Species speciesFromName(const std::string& name)
{
	if (name == "BluePom") {
		return Species::BluePom;
	}
	if (name == "RedPom") {
		return Species::RedPom;
	}
	if (name == "YellowPom") {
		return Species::YellowPom;
	}
	if (name == "BlackPom") {
		return Species::BlackPom;
	}
	if (name == "WhitePom") {
		return Species::WhitePom;
	}
	if (name == "RandPom") {
		return Species::RandPom;
	}
	if (name == "Pom") {
		return Species::PomBase;
	}
	throw std::runtime_error("unknown species");
}

// Module colour-index space: 0 blue, 1 red, 2 yellow, 3 purple, 4 white.
// PikiColor is Blue 0 / Red 1 / Yellow 2 (GlobalGameOptions.h:61-65).
inline int speciesColour(Species species)
{
	switch (species) {
	case Species::BluePom:
		return 0;
	case Species::RedPom:
		return 1;
	case Species::YellowPom:
		return 2;
	case Species::BlackPom:
		return 3;
	case Species::WhitePom:
		return 4;
	case Species::RandPom:
		return -1; // cycles
	case Species::PomBase:
		break;
	}
	throw std::runtime_error("base species has no colour");
}

inline int budget(Species species)
{
	if (isBase(species)) {
		throw std::runtime_error("base species has no budget");
	}
	return species == Species::RandPom ? QueenBudget : IpTtlBudget;
}

inline bool queen(Species species)
{
	return species == Species::RandPom;
}

// P2 source state set (enemy/Entities/Pom.h:153-161). One FSM is shared by the
// six buds: Wait arms to Open at the open clip's key 2; a touch starts Swing;
// Close after fp01 or a spent budget routes to Shot when Pikmin are inside (or
// reopens); Shot spits leaf sprouts; Dead is reached only from an exhausted
// lifetime budget (audit lines 60-73, 79-82). Note: this module has no clip
// playback, so the logged walk collapses the source's transient Swing->Open
// return into open -> swing -> close.
enum class State {
	Wait   = 0,
	Dead   = 1,
	Open   = 2,
	Close  = 3,
	Shot   = 4,
	Swing  = 5,
};

inline const char* stateName(State state)
{
	switch (state) {
	case State::Wait:
		return "wait";
	case State::Dead:
		return "dead";
	case State::Open:
		return "open";
	case State::Close:
		return "close";
	case State::Shot:
		return "shot";
	case State::Swing:
		return "swing";
	}
	throw std::runtime_error("unknown pom state");
}

// candypop_dead: the bud dies only from an exhausted lifetime budget (no
// combat path, no corpse). Death waits on conservation settlement so a
// consumed Pikmin's sprouts can never be silently discarded by the death.
inline bool dead(bool budgetSpent, int owed)
{
	if (owed < 0) {
		throw std::runtime_error("negative owed sprout count");
	}
	return budgetSpent && owed == 0;
}

// candypop_accept: a Pikmin enters through the slot press while armed and under
// the lifetime budget; any colour is accepted.
inline bool accept(Species species, bool slotPressed, bool armed, int usedSlots)
{
	if (isBase(species)) {
		throw std::runtime_error("base species cannot accept");
	}
	if (usedSlots < 0) {
		throw std::runtime_error("negative slot count");
	}
	return slotPressed && armed && usedSlots < budget(species);
}

// candypop_refund: only colour buds refund their own colour; the Queen never.
inline bool refund(Species species, int thrownColour)
{
	if (isBase(species)) {
		throw std::runtime_error("base species cannot refund");
	}
	if (thrownColour < 0 || thrownColour > 4) {
		throw std::runtime_error("unknown pikmin colour");
	}
	return !queen(species) && thrownColour == speciesColour(species);
}

// candypop_close: None while open; "shot" if Pikmin are inside, else "reopen".
enum class CloseOutcome { StillOpen, Shot, Reopen };

inline CloseOutcome closeOutcome(float secondsSinceLastSwallow, float remainOpenSeconds, bool budgetSpent, bool pikminInside)
{
	if (!std::isfinite(secondsSinceLastSwallow) || !std::isfinite(remainOpenSeconds)) {
		throw std::runtime_error("invalid close time");
	}
	if (!(budgetSpent || secondsSinceLastSwallow >= remainOpenSeconds)) {
		return CloseOutcome::StillOpen;
	}
	return pikminInside ? CloseOutcome::Shot : CloseOutcome::Reopen;
}

inline const char* closeOutcomeName(CloseOutcome outcome)
{
	switch (outcome) {
	case CloseOutcome::StillOpen:
		return "open";
	case CloseOutcome::Shot:
		return "shot";
	case CloseOutcome::Reopen:
		return "reopen";
	}
	throw std::runtime_error("unknown close outcome");
}

// candypop_shot_count: ip13 (9) per swallowed Pikmin for the Queen, else 1.
inline int shotCount(Species species, int swallowed)
{
	if (isBase(species)) {
		throw std::runtime_error("base species cannot shoot");
	}
	if (swallowed < 0) {
		throw std::runtime_error("negative swallow count");
	}
	return swallowed * (queen(species) ? QueenShotMul : 1);
}

// candypop_queen_colour: deterministic Blue/Red/Yellow every fp02, skipping
// colours not yet met (Pom.cpp:330-355); returns module colour index.
inline int queenColour(float elapsedSeconds, unsigned metMask, float changeSeconds = QueenCycleSec)
{
	if (!std::isfinite(elapsedSeconds) || elapsedSeconds < 0.0f || !std::isfinite(changeSeconds) || changeSeconds <= 0.0f) {
		throw std::runtime_error("invalid queen cycle time");
	}
	const int cycle[3] = {0, 1, 2};
	int met[3];
	int count = 0;
	for (int i = 0; i < 3; ++i) {
		if (metMask & (1u << i)) {
			met[count++] = cycle[i];
		}
	}
	if (count == 0) {
		throw std::runtime_error("no met colours for the Queen cycle");
	}
	const int step = static_cast<int>(std::floor(elapsedSeconds / changeSeconds + 1e-9f));
	return met[step % count];
}

// candypop_spawn_allowed: Violet/Ivory cap on early floors/caves; Ivory needs
// Whites met except in White Flower Garden; Lapis/Golden need their colour met.
inline bool spawnAllowed(Species species, int floor, const std::string& cave, unsigned metMask, int playerCount)
{
	if (isBase(species)) {
		return false;
	}
	if (floor < 1 || playerCount < 0) {
		throw std::runtime_error("invalid spawn gate");
	}
	const bool early = (floor >= EarlyFloorFirst && floor <= EarlyFloorLast) || cave == "Emergence Cave" || cave == WhiteFlowerGarden;
	if ((species == Species::BlackPom || species == Species::WhitePom) && early && playerCount >= VioletIvoryCap) {
		return false;
	}
	const int required = species == Species::BluePom ? 0 : species == Species::YellowPom ? 2 : species == Species::WhitePom ? 4 : -1;
	if (required >= 0 && !(metMask & (1u << required))) {
		if (!(species == Species::WhitePom && cave == WhiteFlowerGarden)) {
			return false;
		}
	}
	return true;
}

// One sidecar row: the generator identity, the source species and the module
// anchor position (behavior-only slice: no engine Pom FSM is spawned).
struct PomSpec {
	std::uint32_t generator = 0;
	Species species         = Species::RedPom;
	float x                 = 0.0f;
	float y                 = 0.0f;
	float z                 = 0.0f;
};

// Strict P2_POM_1: <count> rows of <generator> <species> <x> <y> <z>.
// Malformed streams throw; a base Pom row parses but is rejected by the module.
inline std::vector<PomSpec> readPoms(std::istream& in)
{
	std::string header;
	int count = 0;
	if (!(in >> header >> count) || header != "P2_POM_1" || count < 1 || count > 64) {
		throw std::runtime_error("invalid P2_POM_1 header");
	}
	std::vector<PomSpec> out;
	out.reserve(static_cast<std::size_t>(count));
	for (int i = 0; i < count; ++i) {
		unsigned long long generator = 0;
		std::string speciesWord;
		float x = 0.0f, y = 0.0f, z = 0.0f;
		if (!(in >> generator >> speciesWord >> x >> y >> z) || generator > 0xffffffffULL || !std::isfinite(x)
		    || !std::isfinite(y) || !std::isfinite(z) || std::fabs(x) > 100000.0f || std::fabs(y) > 100000.0f
		    || std::fabs(z) > 100000.0f) {
			throw std::runtime_error("invalid P2_POM_1 row");
		}
		PomSpec spec;
		spec.generator = static_cast<std::uint32_t>(generator);
		spec.species   = speciesFromName(speciesWord);
		spec.x         = x;
		spec.y         = y;
		spec.z         = z;
		for (const PomSpec& other : out) {
			if (other.generator == spec.generator) {
				throw std::runtime_error("duplicate generator");
			}
		}
		out.push_back(spec);
	}
	std::string trailing;
	if (in >> trailing) {
		throw std::runtime_error("trailing P2_POM_1 data");
	}
	return out;
}

} // namespace p2pom
