#pragma once
// Pure P2 Pellet Posy (Pelplant) source policy for lane 23, family #171.
//
// Mirrors the already-delivered experimental/pikmin2_flora_behavior.py and the
// source audit docs/PIKMIN2_FLORA_AUDIT.md (#171). No engine types, no side
// effects; the native actor (pc_p2_flora_actor.cpp) and the standalone strict
// test (tests/pikmin2_flora_policy.cpp) share this header. Values are the
// source/audit facts, not reconstructed guesses:
//   * full-only vulnerability (Pelplant.h:187-190),
//   * instant fell on a collision part whose special code ends in '0', the
//     s__0 head (pelplant.cpp:485,518),
//   * the dead state releases the captured pellet (pelplantState.cpp:445-451),
//   * the purely time-based Blue/Red/Yellow colour cycle fp03 = 1.5 s
//     (pelplant.cpp:407-450),
//   * no regrowth timer (a new posy is a generator respawn).
#include <cmath>
#include <cstdint>
#include <istream>
#include <stdexcept>
#include <string>
#include <vector>

namespace p2flora {

// Pelplant.h:37-50.
enum State {
	WaitSmall    = 0,
	WaitMiddle   = 1,
	WaitFull     = 2,
	GrowSmallMid = 3,
	GrowMidFull  = 4,
	Damage       = 5,
	Dead         = 6,
	WitherFull   = 7,
	WitherMiddle = 8,
	WitherSmall  = 9,
};

// Growth stages; the P1 Palm strength field uses the same 0/1/2 ordering.
enum class Stage { Small = 0, Middle = 1, Full = 2 };

// Generator pellet sizes (audit lines 35-38). 10 and 20 play bgrow1.
inline constexpr int PelletSizes[4] = {1, 5, 10, 20};

// PALMPF_ChangingColorPeriod fp03 is 1.5 s on disc (Pelplant.h:286).
inline constexpr float ColourCycleSeconds = 1.5f;

// The dead state releases its captured pellet instead of destroying it.
// There is no regrowth timer; a replacement posy is a generator respawn.
inline constexpr bool HasRegrowthTimer = false;

inline bool validPelletSize(int size)
{
	return size == PelletSizes[0] || size == PelletSizes[1] || size == PelletSizes[2] || size == PelletSizes[3];
}

inline bool pelletUsesBgrow(int size)
{
	if (!validPelletSize(size)) {
		throw std::runtime_error("invalid pellet size");
	}
	return size == 10 || size == 20;
}

// Only a full posy takes damage; small and growing posies are invulnerable.
inline bool vulnerable(Stage stage)
{
	return stage == Stage::Full;
}

// A collision part whose special code ends in '0' (the s__0 head) fells the
// posy instantly when a Pikmin latches it.
inline bool instantFell(const std::string& specialCode)
{
	return !specialCode.empty() && specialCode.back() == '0';
}

// Seconds-based growth: small -> middle after fp01, middle -> full after fp02,
// advancing only while the Growing flag is set. Full is terminal.
inline Stage growth(Stage stage, float elapsedSeconds, bool growing, float fp01 = 90.0f, float fp02 = 60.0f)
{
	if (!std::isfinite(elapsedSeconds) || !std::isfinite(fp01) || !std::isfinite(fp02) || fp01 < 0.0f || fp02 < 0.0f) {
		throw std::runtime_error("invalid growth time");
	}
	if (!growing) {
		return stage;
	}
	if (stage == Stage::Small) {
		return elapsedSeconds >= fp01 ? Stage::Middle : Stage::Small;
	}
	if (stage == Stage::Middle) {
		return elapsedSeconds >= fp02 ? Stage::Full : Stage::Middle;
	}
	return Stage::Full;
}

// True only in the dead state while a pellet is still captured.
inline bool releasedOnDeath(bool captured, State state)
{
	return captured && state == Dead;
}

// Colour names map to the P1 PELCOLOR_* indices; "random" is the time cycle.
inline int colourIndex(const std::string& name)
{
	if (name == "blue") {
		return 0;
	}
	if (name == "red") {
		return 1;
	}
	if (name == "yellow") {
		return 2;
	}
	if (name == "random") {
		return -1;
	}
	throw std::runtime_error("unknown colour");
}

// Advance the time-based cycle through Blue/Red/Yellow, skipping colours not
// yet met. metMask bit i means colour index i has been met.
inline int cycleColour(int step, unsigned metMask)
{
	if (step < 0) {
		throw std::runtime_error("negative cycle step");
	}
	int cycle[3];
	int count = 0;
	for (int i = 0; i < 3; ++i) {
		if (metMask & (1u << i)) {
			cycle[count++] = i;
		}
	}
	if (count == 0) {
		throw std::runtime_error("no met colours");
	}
	return cycle[step % count];
}

inline int cycleStep(float elapsedSeconds, float changeSeconds = ColourCycleSeconds)
{
	if (!std::isfinite(elapsedSeconds) || elapsedSeconds < 0.0f || !std::isfinite(changeSeconds) || changeSeconds <= 0.0f) {
		throw std::runtime_error("invalid cycle time");
	}
	return static_cast<int>(std::floor(elapsedSeconds / changeSeconds + 1e-9f));
}

inline const char* stageName(Stage stage)
{
	switch (stage) {
	case Stage::Small:
		return "small";
	case Stage::Middle:
		return "middle";
	case Stage::Full:
		return "full";
	}
	throw std::runtime_error("unknown stage");
}

inline Stage stageFromName(const std::string& name)
{
	if (name == "small") {
		return Stage::Small;
	}
	if (name == "middle") {
		return Stage::Middle;
	}
	if (name == "full") {
		return Stage::Full;
	}
	throw std::runtime_error("unknown stage");
}

// One sidecar row: which live P1 Palm proxy carries which source stage and
// which pellet it must release on the fell path.
struct PelplantSpec {
	std::uint32_t generator = 0;
	Stage stage             = Stage::Small;
	int pellet              = 1;
	int colour              = -1; // -1 == the time-based random cycle
};

// Strict P2_FLORA_PELPLANT_1: <count> rows of <generator> <stage> <pellet>
// <colour>. Any malformed stream throws; the native side treats a throw as a
// fail-closed abort, never a silent fallback to P1 behaviour.
inline std::vector<PelplantSpec> readPelplants(std::istream& in)
{
	std::string header;
	int count = 0;
	if (!(in >> header >> count) || header != "P2_FLORA_PELPLANT_1" || count < 1 || count > 64) {
		throw std::runtime_error("invalid P2_FLORA_PELPLANT_1 header");
	}
	std::vector<PelplantSpec> out;
	out.reserve(static_cast<std::size_t>(count));
	for (int i = 0; i < count; ++i) {
		unsigned long long generator = 0;
		std::string stageWord, colourWord;
		int pellet = 0;
		if (!(in >> generator >> stageWord >> pellet >> colourWord) || generator > 0xffffffffULL || !validPelletSize(pellet)) {
			throw std::runtime_error("invalid P2_FLORA_PELPLANT_1 row");
		}
		PelplantSpec spec;
		spec.generator = static_cast<std::uint32_t>(generator);
		spec.stage     = stageFromName(stageWord);
		spec.pellet    = pellet;
		spec.colour    = colourIndex(colourWord);
		for (const PelplantSpec& other : out) {
			if (other.generator == spec.generator) {
				throw std::runtime_error("duplicate generator");
			}
		}
		out.push_back(spec);
	}
	std::string trailing;
	if (in >> trailing) {
		throw std::runtime_error("trailing P2_FLORA_PELPLANT_1 data");
	}
	return out;
}

} // namespace p2flora
