// Opt-in P2 plant scenery policy actor (family #171, #448).
//
// The port already owns the P1 Plant scenery actor (include/PlantMgr.h,
// src/plugPikiKando/plantMgr.cpp); this module is an additive policy layer over
// live Plant actors bound by generator id:
//   * LOD sizing: general parameters are repurposed as LOD volumes (territory
//     lifts the sphere, private/home radius define cylinders); fp01 on Clover
//     and the brown figworts is the general floor offset (asset-contract value,
//     reconstructed). The bound plant's scale is clamped and the floor offset is
//     applied only for species that carry the floor role,
//   * Spectralid sentinel: only Tanpopo/Ooinu_l/Magaret reserve the child slot
//     and may spawn the five yellow Spectralids on first touch; any other
//     species carrying the sentinel is suppressed. This slice cannot reach the
//     lane-15 pc_p2_qurione module's spawn interface (it is a visual-only
//     binder), so a reserved sentinel plant reports BLOCKED reason=no_qurione_seam
//     rather than forking the flier.
// Sidecar format (cwd), strict and fail-closed:
//   P2_PLANT_1 <count>
//   <generator-u32> <species> <lod_scale> <floor_offset> <sentinel 0|1>
#include "pc_p2_plant.h"
#include "pc_p2_plant_policy.h"
#include "pc_bbft.h"
#include "Generator.h"
#include "PlantMgr.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <vector>

namespace {
struct Bound {
	p2plant::PlantSpec spec;
	Plant* plant = nullptr;
};

std::vector<p2plant::PlantSpec> pending;
std::vector<Bound> plants;
bool scanned = false;

[[noreturn]] void fail()
{
	std::fputs("P2_PLANT invalid sidecar\n", stderr);
	std::abort();
}

void applyLod(const Bound& bound)
{
	const p2plant::Species species = bound.spec.species;
	const float scale              = p2plant::clampScale(bound.spec.lodScale);
	const p2plant::LodRole floorRole = p2plant::lodRole(species, p2plant::Volume::Fp01);
	float floor                      = 0.0f;
	bool clamped                     = false;
	if (floorRole == p2plant::LodRole::FloorOffset) {
		floor = p2plant::clampFloorOffset(p2plant::floorOffset(species));
	} else if (bound.spec.floorOffset != 0.0f) {
		clamped = true; // provided but not a floor-role species -> dropped
	}
	if (bound.plant) {
		bound.plant->mSRT.s.set(scale, scale, scale);
		bound.plant->mSRT.t.y += floor;
	}
	std::printf("P2_PLANT_LOD generator=%u species=%s territory=%s private=%s home=%s floor_role=%s floor_offset=%.3f "
	            "scale=%.3f clamped=%d reconstructed=%d bound=%d\n",
	            bound.spec.generator, p2plant::speciesName(species),
	            p2plant::lodRoleName(p2plant::lodRole(species, p2plant::Volume::Territory)),
	            p2plant::lodRoleName(p2plant::lodRole(species, p2plant::Volume::PrivateRadius)),
	            p2plant::lodRoleName(p2plant::lodRole(species, p2plant::Volume::HomeRadius)),
	            p2plant::lodRoleName(floorRole), floor, scale, int(clamped), int(p2plant::floorOffsetReconstructed(species)),
	            int(bound.plant != nullptr));
}

void applySentinel(const Bound& bound)
{
	const p2plant::SentinelDecision decision = p2plant::spectralidDecision(bound.spec.species, bound.spec.sentinel, true);
	if (decision == p2plant::SentinelDecision::None) {
		std::printf("P2_PLANT_SENTINEL_NONE generator=%u species=%s sentinel=0\n", bound.spec.generator,
		            p2plant::speciesName(bound.spec.species));
		return;
	}
	if (decision == p2plant::SentinelDecision::SuppressedNoSlot) {
		std::printf("P2_PLANT_SENTINEL_SUPPRESSED generator=%u species=%s reason=no_reserved_slot\n", bound.spec.generator,
		            p2plant::speciesName(bound.spec.species));
		return;
	}
	std::printf("P2_PLANT_SENTINEL_ARMED generator=%u species=%s per_touch=%d slot_reserved=1\n", bound.spec.generator,
	            p2plant::speciesName(bound.spec.species), p2plant::SpectralidPerTouch);
	// pc_p2_qurione is a visual-only binder owned by lane 15; it exposes no
	// spawn seam and must not be forked or have its shared interface changed.
	std::printf("P2_PLANT_SENTINEL_BLOCKED generator=%u species=%s reason=no_qurione_seam spawn=blocked\n",
	            bound.spec.generator, p2plant::speciesName(bound.spec.species));
}

void bindPending()
{
	if (pending.empty() || !plantMgr) {
		return;
	}
	if (!scanned) {
		scanned = true;
		int count = 0;
		Iterator diag(plantMgr);
		CI_LOOP(diag)
		{
			Plant* plant = static_cast<Plant*>(*diag);
			if (!plant) {
				continue;
			}
			std::printf("P2_PLANT_SCAN generator=%u plant_type=%u\n", plant->mGenerator ? plant->mGenerator->_70 : 0,
			            unsigned(plant->mPlantType));
			if (++count >= 64) {
				break;
			}
		}
		std::printf("P2_PLANT_SCAN_TOTAL actors=%d wanted=%u\n", count, pending.front().generator);
		std::fflush(stdout);
	}
	for (auto it = pending.begin(); it != pending.end();) {
		Plant* found = nullptr;
		Iterator scan(plantMgr);
		CI_LOOP(scan)
		{
			Plant* plant = static_cast<Plant*>(*scan);
			if (!plant || !plant->mGenerator || plant->mGenerator->_70 != it->generator) {
				continue;
			}
			if (found) {
				fail();
			}
			found = plant;
		}
		if (!found) {
			++it;
			continue;
		}
		Bound bound;
		bound.spec  = *it;
		bound.plant = found;
		plants.push_back(bound);
		std::printf("P2_PLANT_READY generator=%u species=%s plant_type=%u bound=1\n", it->generator,
		            p2plant::speciesName(it->species), unsigned(found->mPlantType));
		applyLod(plants.back());
		applySentinel(plants.back());
		it = pending.erase(it);
	}
}
} // namespace

void pc_p2_plant_reset()
{
	pending.clear();
	plants.clear();
	scanned = false;
}

void pc_p2_plant_setup()
{
	pc_p2_plant_reset();
	if (!pc_pikipelago_room_preview() || !plantMgr) {
		return;
	}
	std::ifstream in("p2-plant.txt");
	if (!in) {
		return; // inert without the sidecar
	}
	try {
		pending = p2plant::readPlants(in);
	} catch (const std::exception&) {
		fail();
	}
	bindPending();
	std::printf("P2_PLANT_SIDECAR bound=%u pending=%u\n", unsigned(plants.size()), unsigned(pending.size()));
	std::fflush(stdout);
}

void pc_p2_plant_tick()
{
	if (!pending.empty()) {
		bindPending();
	}
}
