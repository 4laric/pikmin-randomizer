// Opt-in lane-23 real-engine Candypop binding (#448, family #171).
//
// See pc_p2_candypop.h. The module owns only the source identity/policy glue
// and the own-colour-aware conversion; the actor, swallow, close, discharge and
// sprout creation are the genuine engine `PomAi` behaviour. Strict sidecar
// file `p2-pom-engine.txt` (cwd, `P2_POM_1` rows, reusing the lane-23 Candypop
// parser), fail-closed:
//
//   P2_POM_1 <count>
//   <generator-u32> <BluePom|RedPom|YellowPom|BlackPom|WhitePom|RandPom|Pom> <x> <y> <z>
//
// BluePom/RedPom/YellowPom use the source own-colour refund. RandPom is the
// Queen: it never refunds, cycles Blue/Red/Yellow every fp02 = 2.6 s, and
// shoots ip13 = 9 leaf sprouts per swallowed Pikmin. BlackPom/WhitePom are
// reported unsupported here (the violet/ivory providers own them); the base Pom
// is rejected and never bound. Without the file the module is inert.
#include "pc_p2_candypop.h"
#include "pc_p2_pom_policy.h"
#include "pc_bbft.h"
#include "Boss.h"
#include "Generator.h"
#include "ItemMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "ObjType.h"
#include "Piki.h"
#include "PikiAI.h"
#include "PikiHeadItem.h"
#include "PikiState.h"
#include "Pom.h"
#include "Stickers.h"
#include "Vector.h"
#include <SDL2/SDL.h>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <utility>
#include <vector>

namespace {

constexpr float SimTick       = 1.0f / 30.0f;
constexpr int MaxCatchUpSteps = 4;
constexpr unsigned QueenMetMask = 0x7u; // fixture: Blue/Red/Yellow met

struct EngineSpec {
	std::uint32_t generator = 0;
	p2pom::Species species   = p2pom::Species::RedPom;
	int colour               = 1;
	float x                  = 0.0f;
	float y                  = 0.0f;
	float z                  = 0.0f;
};

std::vector<EngineSpec> specs;
bool specsLoaded = false;
std::vector<std::uint32_t> applied;
std::vector<std::pair<std::uint32_t, int>> queenColours;
unsigned clockLast   = 0;
float clockAcc       = 0.0f;
double behaviorSec   = 0.0;

[[noreturn]] void fail()
{
	std::fputs("P2_CANDYPOP invalid sidecar\n", stderr);
	std::abort();
}

bool engineSpecies(p2pom::Species species)
{
	return species == p2pom::Species::BluePom || species == p2pom::Species::RedPom
	    || species == p2pom::Species::YellowPom || species == p2pom::Species::RandPom;
}

int currentQueenColour(std::uint32_t generator)
{
	for (const auto& entry : queenColours) {
		if (entry.first == generator) {
			return entry.second;
		}
	}
	return -1;
}

void setQueenColour(std::uint32_t generator, int colour)
{
	for (auto& entry : queenColours) {
		if (entry.first == generator) {
			entry.second = colour;
			return;
		}
	}
	queenColours.push_back({generator, colour});
}

void loadSpecs()
{
	if (specsLoaded) {
		return;
	}
	specsLoaded = true;
	if (!pc_pikipelago_room_preview()) {
		return;
	}
	std::ifstream in("p2-pom-engine.txt");
	if (!in) {
		return; // inert without the sidecar
	}
	std::vector<p2pom::PomSpec> rows;
	try {
		rows = p2pom::readPoms(in);
	} catch (const std::exception&) {
		fail();
	}
	for (const p2pom::PomSpec& row : rows) {
		if (p2pom::isBase(row.species)) {
			std::printf("P2_POM_BASE_REJECTED generator=%u species=Pom source_id=82 reason=nonspawnable_base\n",
			            row.generator);
			continue;
		}
		if (!engineSpecies(row.species)) {
			std::printf("P2_CANDYPOP_UNSUPPORTED generator=%u species=%s reason=not_engine_colour\n", row.generator,
			            p2pom::speciesName(row.species));
			continue;
		}
		EngineSpec spec;
		spec.generator = row.generator;
		spec.species   = row.species;
		spec.colour    = p2pom::speciesColour(row.species);
		spec.x         = row.x;
		spec.y         = row.y;
		spec.z         = row.z;
		specs.push_back(spec);
	}
}

const EngineSpec* match(const Pom* pom)
{
	loadSpecs();
	if (specs.empty() || !pom) {
		return nullptr;
	}
	if (pom->mGenerator) {
		const unsigned generator = static_cast<unsigned>(pom->mGenerator->_70);
		for (const EngineSpec& spec : specs) {
			if (spec.generator == generator) {
				return &spec;
			}
		}
	}
	// At Pom init the generator link is assigned only after birth, so fall back
	// to the birth position the sidecar declared.
	for (const EngineSpec& spec : specs) {
		const float dx = pom->mSRT.t.x - spec.x;
		const float dz = pom->mSRT.t.z - spec.z;
		if (dx * dx + dz * dz <= 1.0f) {
			return &spec;
		}
	}
	return nullptr;
}

bool isApplied(std::uint32_t generator)
{
	for (std::uint32_t value : applied) {
		if (value == generator) {
			return true;
		}
	}
	return false;
}

const char* colourName(int colour)
{
	switch (colour) {
	case 0:
		return "blue";
	case 1:
		return "red";
	case 2:
		return "yellow";
	default:
		return "unknown";
	}
}

} // namespace

void pc_p2_candypop_reset()
{
	specsLoaded = false;
	specs.clear();
	applied.clear();
	queenColours.clear();
	clockLast   = SDL_GetTicks();
	clockAcc    = 0.0f;
	behaviorSec = 0.0;
}

void pc_p2_candypop_setup()
{
	loadSpecs();
	if (!specs.empty()) {
		std::printf("P2_CANDYPOP_SIDECAR engine_buds=%u\n", unsigned(specs.size()));
	}
	std::fflush(stdout);
}

void pc_p2_candypop_tick()
{
	loadSpecs();
	if (specs.empty() || !bossMgr) {
		return;
	}
	const unsigned now = SDL_GetTicks();
	if (clockLast == 0) {
		clockLast = now;
	}
	clockAcc += float(now - clockLast) * 0.001f;
	clockLast = now;
	int steps = 0;
	while (clockAcc >= SimTick && steps < MaxCatchUpSteps) {
		clockAcc -= SimTick;
		behaviorSec += double(SimTick);
		++steps;
	}
	Iterator it(bossMgr);
	CI_LOOP(it)
	{
		Boss* boss = static_cast<Boss*>(*it);
		if (!boss || !boss->isAlive() || boss->mObjType != OBJTYPE_Pom) {
			continue;
		}
		Pom* pom             = static_cast<Pom*>(boss);
		const EngineSpec* spec = match(pom);
		if (!spec) {
			continue;
		}
		const bool queen = p2pom::queen(spec->species);
		if (!isApplied(spec->generator)) {
			applied.push_back(spec->generator);
			// The staged boss generator carries a valid P1 container colour so the
			// engine birth gate passes; stamp the source identity here.
			const int initial = queen ? p2pom::queenColour(float(behaviorSec), QueenMetMask) : spec->colour;
			pom->setColor(initial);
			if (queen) {
				setQueenColour(spec->generator, initial);
			}
			std::printf(
			    "P2_POM_READY generator=%u species=%s source_id=%d colour=%d budget=%d queen=%d engine=1 x=%.2f y=%.2f z=%.2f\n",
			    spec->generator, p2pom::speciesName(spec->species), p2pom::speciesId(spec->species), initial,
			    p2pom::budget(spec->species), int(queen), spec->x, spec->y, spec->z);
			std::printf("P2_POM_INVULNERABLE generator=%u invulnerable_after_landing=1\n", spec->generator);
		}
		if (queen) {
			const int colour = p2pom::queenColour(float(behaviorSec), QueenMetMask);
			if (colour != currentQueenColour(spec->generator)) {
				setQueenColour(spec->generator, colour);
				pom->setColor(colour);
				std::printf("P2_POM_QUEEN_COLOUR generator=%u colour=%d met=%u\n", spec->generator, colour,
				            unsigned(QueenMetMask));
			}
		}
	}
	std::fflush(stdout);
}

int pc_p2_candypop_budget(const Pom* pom)
{
	const EngineSpec* spec = match(pom);
	return spec ? p2pom::budget(spec->species) : 0;
}

int pc_p2_convert_candypop(Pom* pom, int remaining)
{
	const EngineSpec* spec = match(pom);
	if (!spec) {
		return -1;
	}
	if (remaining < 0) {
		remaining = 0;
	}
	const bool queen          = p2pom::queen(spec->species);
	const int sproutColour    = queen ? currentQueenColour(spec->generator) : spec->colour;
	const int sproutsPerInput = queen ? p2pom::QueenShotMul : 1;
	Stickers stickers(pom);
	Iterator it(&stickers);
	int converted = 0, used = 0, refunds = 0, bornTotal = 0;
	CI_LOOP(it)
	{
		Creature* creature = *it;
		if (!creature || !creature->isAlive() || !creature->isPiki()) {
			continue;
		}
		Piki* piki            = static_cast<Piki*>(creature);
		const int input       = int(piki->mColor);
		const bool sameColour = !queen && input == spec->colour;
		if (!sameColour && used >= remaining) {
			// Budget exhausted: release the input rather than consuming it.
			piki->endStickObject();
			piki->mFSM->transit(piki, PIKISTATE_Normal);
			piki->changeMode(PikiMode::FreeMode, naviMgr->getNavi());
			it.dec();
			continue;
		}
		int bornThisInput = 0;
		for (int s = 0; s < sproutsPerInput; ++s) {
			PikiHeadItem* sprout = static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));
			if (!sprout) {
				break; // exhausted item capacity; keep any sprouts already born
			}
			Vector3f position = pom->mSRT.t;
			position.y += 50.0f;
			sprout->init(position);
			sprout->setColor(sproutColour < 0 ? 0 : sproutColour);
			const float angle = float(converted * p2pom::QueenShotMul + s) * 1.256637f;
			sprout->mVelocity.set(p2pom::LaunchHoriz * std::sin(angle), p2pom::LaunchVert,
			                      p2pom::LaunchHoriz * std::cos(angle));
			sprout->startAI(0);
			C_SAI(sprout)->start(sprout, PikiHeadAI::PIKIHEAD_Flying);
			++bornThisInput;
		}
		if (bornThisInput == 0) {
			// Capacity failure must never eat an input.
			piki->endStickObject();
			piki->mFSM->transit(piki, PIKISTATE_Normal);
			piki->changeMode(PikiMode::FreeMode, naviMgr->getNavi());
			it.dec();
			continue;
		}
		bornTotal += bornThisInput;
		piki->setEraseKill();
		piki->kill(false);
		it.dec();
		++converted;
		if (sameColour) {
			++refunds;
		} else {
			++used;
		}
		std::printf("P2_CANDYPOP_WITNESS generator=%u species=%s input=%s refund=%d\n", spec->generator,
		            p2pom::speciesName(spec->species), colourName(input), int(sameColour));
	}
	std::printf("P2_CANDYPOP_CONVERT generator=%u species=%s converted=%d used=%d refunds=%d\n", spec->generator,
	            p2pom::speciesName(spec->species), converted, used, refunds);
	if (queen && bornTotal > 0) {
		std::printf("P2_CANDYPOP_SPROUTS generator=%u species=RandPom sprouts=%d multiplier=%d\n", spec->generator,
		            bornTotal, p2pom::QueenShotMul);
	}
	std::fflush(stdout);
	return used;
}
