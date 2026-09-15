// Standalone P2 Candypop Bud policy test (#171/#448, lane 23).
// Compile with MinGW strict flags:
//   g++ -std=c++17 -Wall -Wextra -Werror -I native-patches/pom tests/pikmin2_pom_policy.cpp -o pom_policy.exe
// Mirrors tests/test_pikmin2_flora_behavior.py Candypop functions against the
// #171 audit and experimental/pikmin2_flora_behavior.py.
#include "pc_p2_pom_policy.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace p2pom;

int main()
{
	// Identity: enemyInfo.h:62-67 / :141.
	static_assert(int(Species::BluePom) == 3 && int(Species::RedPom) == 4 && int(Species::YellowPom) == 5
	                  && int(Species::BlackPom) == 6 && int(Species::WhitePom) == 7 && int(Species::RandPom) == 8
	                  && int(Species::PomBase) == 82,
	              "species ids");
	assert(!isBase(Species::BluePom) && !isBase(Species::RandPom) && isBase(Species::PomBase));

	// Budgets (ip01 5 / ip11 1) and colours.
	assert(budget(Species::BluePom) == 5 && budget(Species::RedPom) == 5 && budget(Species::YellowPom) == 5
	       && budget(Species::BlackPom) == 5 && budget(Species::WhitePom) == 5 && budget(Species::RandPom) == 1);
	assert(speciesColour(Species::BluePom) == 0 && speciesColour(Species::RedPom) == 1 && speciesColour(Species::YellowPom) == 2
	       && speciesColour(Species::BlackPom) == 3 && speciesColour(Species::WhitePom) == 4 && speciesColour(Species::RandPom) == -1);
	assert(queen(Species::RandPom) && !queen(Species::RedPom));

	// candypop_accept: any colour, slot press while armed under budget.
	assert(accept(Species::RedPom, true, true, 0) && accept(Species::RedPom, true, true, 4));
	assert(!accept(Species::RedPom, false, true, 0) && !accept(Species::RedPom, true, false, 0) && !accept(Species::RedPom, true, true, 5));
	assert(accept(Species::RandPom, true, true, 0) && !accept(Species::RandPom, true, true, 1));

	// candypop_refund: own colour only, colour buds only.
	assert(refund(Species::RedPom, 1) && !refund(Species::RedPom, 0));
	assert(refund(Species::BluePom, 0) && refund(Species::YellowPom, 2));
	assert(!refund(Species::RandPom, 0) && !refund(Species::RandPom, 1));

	// candypop_close: fp01 1.0 s or spent budget; shot when Pikmin inside.
	assert(RemainOpenSec == 1.0f);
	assert(closeOutcome(0.5f, 1.0f, false, true) == CloseOutcome::StillOpen);
	assert(closeOutcome(1.0f, 1.0f, false, true) == CloseOutcome::Shot);
	assert(closeOutcome(1.0f, 1.0f, false, false) == CloseOutcome::Reopen);
	assert(closeOutcome(0.0f, 1.0f, true, true) == CloseOutcome::Shot);

	// ip13 leaf sprouts: Queen 9 per Pikmin, colour buds 1.
	assert(QueenShotMul == 9 && shotCount(Species::RandPom, 2) == 18 && shotCount(Species::RedPom, 2) == 2
	       && shotCount(Species::RandPom, 0) == 0);

	// Queen colour cycle: deterministic Blue/Red/Yellow every fp02 2.6 s.
	assert(QueenCycleSec == 2.6f);
	assert(queenColour(0.0f, 0x7u) == 0 && queenColour(2.6f, 0x7u) == 1 && queenColour(5.2f, 0x7u) == 2 && queenColour(7.8f, 0x7u) == 0);
	const unsigned redYellow = (1u << 1) | (1u << 2);
	assert(queenColour(0.0f, redYellow) == 1 && queenColour(2.6f, redYellow) == 2 && queenColour(5.2f, redYellow) == 1);

	// Violet/Ivory story-cave gating (PomMgr.cpp:38-89).
	assert(!spawnAllowed(Species::BlackPom, 1, "Emergence Cave", 0x7u, 20));
	assert(spawnAllowed(Species::BlackPom, 1, "Emergence Cave", 0x7u, 19));
	assert(spawnAllowed(Species::BlackPom, 3, "Any Cave", 0x7u, 20));
	assert(!spawnAllowed(Species::WhitePom, 3, "Any Cave", 0u, 0));
	assert(spawnAllowed(Species::WhitePom, 3, WhiteFlowerGarden, 0u, 0));
	assert(!spawnAllowed(Species::BluePom, 3, "Any Cave", 0u, 0));
	assert(spawnAllowed(Species::BluePom, 3, "Any Cave", 0x1u, 0));

	// Strict P2_POM_1 parsing.
	auto parse = [](const std::string& text) {
		std::istringstream in(text);
		return readPoms(in);
	};
	{
		const std::vector<PomSpec> good = parse("P2_POM_1 3\n"
		                                        "240011 RedPom 10 30 1890\n"
		                                        "240012 RandPom 40 30 1890\n"
		                                        "240013 Pom 60 30 1890\n");
		assert(good.size() == 3);
		assert(good[0].generator == 240011 && good[0].species == Species::RedPom && good[0].x == 10.0f);
		assert(good[1].species == Species::RandPom && good[2].species == Species::PomBase);
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
	reject("P2_POM_2 1\n1 RedPom 0 0 0\n");                                              // wrong version
	reject("P2_POM_1 0\n");                                                              // empty
	reject("P2_POM_1 2\n1 RedPom 0 0 0\n1 RedPom 0 0 0\n");                              // duplicate generator
	reject("P2_POM_1 1\n1 GreenPom 0 0 0\n");                                            // unknown species
	reject("P2_POM_1 1\n4294967296 RedPom 0 0 0\n");                                     // id overflow
	reject("P2_POM_1 1\n1 RedPom nan 0 0\n");                                            // non-finite position
	reject("P2_POM_1 1\n1 RedPom 100001 0 0\n");                                         // position bound
	reject("P2_POM_1 1\n1 RedPom 0 0 0\ntrailing\n");                                    // trailing data
	reject("P2_POM_1 1\n1 RedPom 0 0\n");                                                // truncated row

	// Invalid arguments throw.
	auto threw = [](auto&& call) {
		try {
			call();
		} catch (const std::runtime_error&) {
			return true;
		}
		return false;
	};
	assert(threw([] { budget(Species::PomBase); }));
	assert(threw([] { speciesColour(Species::PomBase); }));
	assert(threw([] { accept(Species::RedPom, true, true, -1); }));
	assert(threw([] { refund(Species::RedPom, 9); }));
	assert(threw([] { shotCount(Species::RandPom, -1); }));
	assert(threw([] { queenColour(-1.0f, 0x7u); }));
	assert(threw([] { closeOutcome(std::nanf(""), 1.0f, false, false); }));
	assert(threw([] { spawnAllowed(Species::RedPom, 0, "x", 0x7u, 0); }));
	assert(threw([] { speciesFromName("Nope"); }));

	// Source six-state FSM (Pom.h:153-161): wait/dead/open/close/shot/swing.
	static_assert(int(State::Wait) == 0 && int(State::Dead) == 1 && int(State::Open) == 2 && int(State::Close) == 3
	                  && int(State::Shot) == 4 && int(State::Swing) == 5,
	              "pom state ids");
	assert(std::string(stateName(State::Wait)) == "wait" && std::string(stateName(State::Dead)) == "dead"
	       && std::string(stateName(State::Open)) == "open" && std::string(stateName(State::Close)) == "close"
	       && std::string(stateName(State::Shot)) == "shot" && std::string(stateName(State::Swing)) == "swing");
	// Death only from an exhausted budget with conservation settled; no corpse.
	assert(dead(true, 0) && !dead(false, 0) && !dead(true, 1) && !dead(false, 1));
	assert(threw([] { dead(true, -1); }));

	std::puts("pikmin2_pom_policy PASS");
	return 0;
}
