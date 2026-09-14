// Standalone P2 plant scenery policy test (#171/#448, lane 23).
// Compile with MinGW strict flags:
//   g++ -std=c++17 -Wall -Wextra -Werror -I native-patches/plant tests/pikmin2_plant_policy.cpp -o plant_policy.exe
// Mirrors tests/test_pikmin2_flora_behavior.py plant functions against the #171
// audit and the #353 asset contract.
#include "pc_p2_plant_policy.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace p2plant;

int main()
{
	// Species identity and names.
	assert(std::string(speciesName(Species::Tanpopo)) == "Tanpopo" && std::string(speciesName(Species::Ooinu_l)) == "Ooinu_l");
	assert(std::string(speciesName(Species::Magaret)) == "Magaret" && std::string(speciesName(Species::KareOoinu_l)) == "KareOoinu_l");
	assert(speciesFromName("Clover") == Species::Clover && speciesFromName("Zenmai") == Species::Zenmai);

	// LOD roles: territory lifts the sphere, private/home define cylinders.
	for (Species species : {Species::Tanpopo, Species::Clover, Species::Ooinu_l, Species::Magaret, Species::HikariKinoko}) {
		assert(lodRole(species, Volume::Territory) == LodRole::LiftedSphere);
		assert(lodRole(species, Volume::PrivateRadius) == LodRole::Cylinder);
		assert(lodRole(species, Volume::HomeRadius) == LodRole::Cylinder);
	}
	// fp01 is the general floor offset only on Clover and the brown figworts.
	assert(lodRole(Species::Clover, Volume::Fp01) == LodRole::FloorOffset);
	assert(lodRole(Species::KareOoinu_s, Volume::Fp01) == LodRole::FloorOffset);
	assert(lodRole(Species::KareOoinu_l, Volume::Fp01) == LodRole::FloorOffset);
	assert(lodRole(Species::Tanpopo, Volume::Fp01) == LodRole::None);
	assert(lodRole(Species::Ooinu_l, Volume::Fp01) == LodRole::None);
	assert(lodRole(Species::Magaret, Volume::Fp01) == LodRole::None);

	// Floor offsets: Clover uses the asset-contract 40.0 (reconstructed).
	assert(floorOffset(Species::Clover) == 40.0f && floorOffsetReconstructed(Species::Clover));
	assert(floorOffset(Species::KareOoinu_s) == 45.0f && floorOffset(Species::KareOoinu_l) == 20.0f);
	assert(floorOffset(Species::Tanpopo) == 0.0f && !floorOffsetReconstructed(Species::Tanpopo));

	// Spectralid sentinel: only Tanpopo/Ooinu_l/Magaret reserve the slot.
	assert(SpectralidPerTouch == 5);
	assert(spectralidReserved(Species::Tanpopo) && spectralidReserved(Species::Ooinu_l) && spectralidReserved(Species::Magaret));
	assert(!spectralidReserved(Species::Clover) && !spectralidReserved(Species::Ooinu_s));
	assert(spectralidDecision(Species::Tanpopo, true, true) == SentinelDecision::Spawn);
	assert(spectralidDecision(Species::Magaret, true, true) == SentinelDecision::Spawn);
	assert(spectralidDecision(Species::Clover, true, true) == SentinelDecision::SuppressedNoSlot);
	assert(spectralidDecision(Species::Tanpopo, false, true) == SentinelDecision::None);
	assert(spectralidDecision(Species::Tanpopo, true, false) == SentinelDecision::None);

	// Sway-on-touch policy.
	assert(SwayMinSpeed == 1.0f);
	assert(sways("captain", 1.1f, true) && sways("pikmin", -2.0f, true));
	assert(!sways("captain", 1.0f, true) && !sways("pikmin", 5.0f, false));
	assert(sways("purple_quake", 0.0f, false) && !sways("enemy", 10.0f, true));
	assert(touchSound("captain") && !touchSound("pikmin"));

	// Sizing clamps.
	assert(clampScale(1.0f) == 1.0f && clampScale(0.1f) == 0.25f && clampScale(9.0f) == 4.0f);
	assert(clampFloorOffset(-5.0f) == 0.0f && clampFloorOffset(50.0f) == 50.0f && clampFloorOffset(500.0f) == 100.0f);

	// Strict P2_PLANT_1 parsing.
	auto parse = [](const std::string& text) {
		std::istringstream in(text);
		return readPlants(in);
	};
	{
		const std::vector<PlantSpec> good = parse("P2_PLANT_1 3\n"
		                                          "240021 Ooinu_l 1.0 0 1\n"
		                                          "240022 Tanpopo 0.1 0 0\n"
		                                          "240023 Clover 9.0 25 1\n");
		assert(good.size() == 3);
		assert(good[0].generator == 240021 && good[0].species == Species::Ooinu_l && good[0].sentinel);
		assert(!good[1].sentinel && good[2].species == Species::Clover);
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
	reject("P2_PLANT_2 1\n1 Clover 1 0 0\n");                          // wrong version
	reject("P2_PLANT_1 0\n");                                          // empty
	reject("P2_PLANT_1 2\n1 Clover 1 0 0\n1 Clover 1 0 0\n");          // duplicate generator
	reject("P2_PLANT_1 1\n1 Bluebell 1 0 0\n");                        // unknown species
	reject("P2_PLANT_1 1\n4294967296 Clover 1 0 0\n");                 // id overflow
	reject("P2_PLANT_1 1\n1 Clover nan 0 0\n");                        // non-finite scale
	reject("P2_PLANT_1 1\n1 Clover 1 0 2\n");                          // sentinel not 0/1
	reject("P2_PLANT_1 1\n1 Clover 1 0 0\ntrailing\n");                // trailing data
	reject("P2_PLANT_1 1\n1 Clover 1 0\n");                            // truncated row

	auto threw = [](auto&& call) {
		try {
			call();
		} catch (const std::runtime_error&) {
			return true;
		}
		return false;
	};
	assert(threw([] { speciesFromName("Nope"); }));
	assert(threw([] { sways("sun", 1.0f, true); }));
	assert(threw([] { clampScale(std::nanf("")); }));
	assert(threw([] { clampFloorOffset(std::nanf("")); }));
	assert(threw([] { touchSound("sun"); }));

	std::puts("pikmin2_plant_policy PASS");
	return 0;
}
