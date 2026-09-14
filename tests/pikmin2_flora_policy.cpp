// Standalone P2 Pellet Posy (Pelplant, enemy ID 0) policy test (#171, lane 23).
// Compile with MinGW strict flags:
//   g++ -std=c++17 -Wall -Wextra -Werror -I native-patches/flora tests/pikmin2_flora_policy.cpp -o flora_policy.exe
// Mirrors tests/test_pikmin2_flora_behavior.py against docs/PIKMIN2_FLORA_AUDIT.md.
#include "pc_p2_flora_policy.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace p2flora;

int main()
{
	// StateIDs, Pelplant.h:37-50.
	static_assert(WaitSmall == 0 && WaitMiddle == 1 && WaitFull == 2 && GrowSmallMid == 3 && GrowMidFull == 4 && Damage == 5
	                  && Dead == 6 && WitherFull == 7 && WitherMiddle == 8 && WitherSmall == 9,
	              "state IDs");
	// Growth stage ordering is the P1 Palm strength ordering.
	static_assert(int(Stage::Small) == 0 && int(Stage::Middle) == 1 && int(Stage::Full) == 2, "stage IDs");

	// Audit lines 35-38: sizes 1/5/10/20; 10 and 20 play bgrow1.
	assert(PelletSizes[0] == 1 && PelletSizes[1] == 5 && PelletSizes[2] == 10 && PelletSizes[3] == 20);
	assert(validPelletSize(1) && validPelletSize(5) && validPelletSize(10) && validPelletSize(20));
	assert(!validPelletSize(0) && !validPelletSize(2) && !validPelletSize(50));
	assert(pelletUsesBgrow(10) && pelletUsesBgrow(20));
	assert(!pelletUsesBgrow(1) && !pelletUsesBgrow(5));

	// Only a full posy is vulnerable (Pelplant.h:187-190, audit lines 43-44).
	assert(!vulnerable(Stage::Small) && !vulnerable(Stage::Middle) && vulnerable(Stage::Full));

	// s__0 head instant fell (pelplant.cpp:485,518).
	assert(instantFell("s__0") && instantFell("0") && instantFell("part0") && instantFell("10"));
	assert(!instantFell("") && !instantFell("head") && !instantFell("0x"));

	// Seconds-based growth, fp01 90 disc / fp02 60 disc (pelplantState.cpp).
	assert(growth(Stage::Small, 89.9f, true) == Stage::Small);
	assert(growth(Stage::Small, 90.0f, true) == Stage::Middle);
	assert(growth(Stage::Middle, 59.9f, true) == Stage::Middle);
	assert(growth(Stage::Middle, 60.0f, true) == Stage::Full);
	assert(growth(Stage::Full, 9999.0f, true) == Stage::Full);
	// The Growing flag gates advancement.
	assert(growth(Stage::Small, 1000.0f, false) == Stage::Small);
	assert(growth(Stage::Middle, 1000.0f, false) == Stage::Middle);

	// Dead state releases the captured pellet (pelplantState.cpp:445-451).
	assert(releasedOnDeath(true, Dead));
	assert(!releasedOnDeath(true, Damage) && !releasedOnDeath(false, Dead));

	// Colour cycle is purely time based Blue/Red/Yellow at fp03 1.5 s.
	assert(ColourCycleSeconds == 1.5f && !HasRegrowthTimer);
	assert(colourIndex("blue") == 0 && colourIndex("red") == 1 && colourIndex("yellow") == 2);
	assert(colourIndex("random") == -1);
	assert(cycleStep(0.0f) == 0 && cycleStep(1.49f) == 0 && cycleStep(1.5f) == 1 && cycleStep(3.0f) == 2);
	// Met-colour skipping: only red and yellow met -> cycle red,yellow.
	const unsigned redYellow = (1u << 1) | (1u << 2);
	assert(cycleColour(0, redYellow) == 1 && cycleColour(1, redYellow) == 2 && cycleColour(2, redYellow) == 1);
	assert(cycleColour(0, 0x7u) == 0 && cycleColour(1, 0x7u) == 1 && cycleColour(2, 0x7u) == 2);

	// Names round-trip.
	assert(std::string(stageName(Stage::Small)) == "small" && std::string(stageName(Stage::Middle)) == "middle"
	       && std::string(stageName(Stage::Full)) == "full");
	assert(stageFromName("small") == Stage::Small && stageFromName("middle") == Stage::Middle
	       && stageFromName("full") == Stage::Full);

	// Strict P2_FLORA_PELPLANT_1 parsing.
	auto parse = [](const std::string& text) {
		std::istringstream in(text);
		return readPelplants(in);
	};
	{
		const std::vector<PelplantSpec> good = parse("P2_FLORA_PELPLANT_1 2\n"
		                                             "230020 full 5 blue\n"
		                                             "230021 middle 10 random\n");
		assert(good.size() == 2);
		assert(good[0].generator == 230020 && good[0].stage == Stage::Full && good[0].pellet == 5 && good[0].colour == 0);
		assert(good[1].generator == 230021 && good[1].stage == Stage::Middle && good[1].pellet == 10 && good[1].colour == -1);
	}
	auto reject = [&](const std::string& text) {
		bool threw = false;
		try {
			parse(text);
		} catch (const std::runtime_error&) {
			threw = true;
		}
		assert(threw);
	};
	reject("P2_FLORA_PELPLANT_2 1\n230020 full 5 blue\n"); // wrong version
	reject("P2_FLORA_PELPLANT_1 0\n");                     // empty
	reject("P2_FLORA_PELPLANT_1 2\n230020 full 5 blue\n230020 full 5 blue\n"); // duplicate
	reject("P2_FLORA_PELPLANT_1 1\n230020 huge 5 blue\n");  // unknown stage
	reject("P2_FLORA_PELPLANT_1 1\n230020 full 7 blue\n");  // invalid pellet size
	reject("P2_FLORA_PELPLANT_1 1\n230020 full 5 purple\n"); // unknown colour
	reject("P2_FLORA_PELPLANT_1 1\n4294967296 full 5 blue\n"); // id overflow
	reject("P2_FLORA_PELPLANT_1 1\n230020 full 5 blue\ntrailing\n"); // trailing data
	reject("P2_FLORA_PELPLANT_1 1\n");                              // truncated row

	// Invalid arguments throw.
	auto threw = [](auto&& call) {
		try {
			call();
		} catch (const std::runtime_error&) {
			return true;
		}
		return false;
	};
	assert(threw([] { pelletUsesBgrow(7); }));
	assert(threw([] { growth(Stage::Small, std::nanf(""), true); }));
	assert(threw([] { cycleColour(0, 0u); }));
	assert(threw([] { cycleStep(-1.0f); }));
	assert(threw([] { colourIndex("green"); }));
	assert(threw([] { stageFromName("nope"); }));

	std::puts("pikmin2_flora_policy PASS");
	return 0;
}
