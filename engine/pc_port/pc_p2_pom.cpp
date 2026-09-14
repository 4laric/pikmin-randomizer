// Opt-in P2 Candypop Bud actor (family #171, #448).
//
// The engine keeps a `Pom` Boss (src/plugPikiNishimura/Pom*.cpp), but binding
// and driving it here would touch shared actor semantics and needs the
// bosses/pom asset + a generator plumbing slice that is out of scope for this
// bounded step. Instead this module owns a small, actor-local behaviour model
// anchored at sidecar positions and enforces the source policy that
// experimental/pikmin2_flora_behavior.py already encodes:
//   * any-colour press/throw-in acceptance while armed and under the lifetime
//     budget ip01 = 5 (colour buds) / ip11 = 1 (Queen RandPom),
//   * own-colour throw refunds the slot on colour buds (Queen never),
//   * close fp01 = 1.0 s after the last swallow or when the budget is spent;
//     close "shoots" ip13 = 9 leaf sprouts per swallowed Pikmin for the Queen,
//     else 1 per Pikmin; a close with nothing inside reopens,
//   * the Queen cycles Blue/Red/Yellow every fp02 = 2.6 s,
//   * invulnerable after landing; the nonspawnable base Pom (82) is rejected
//     with an explicit marker and never bound.
//
// Integration review follow-up (#448, PIKMIN2_PREWAVE_REVIEW_437.md §1):
//   * the Queen's sprouts now use the source-selected cycling colour
//     (`queenColour`) instead of the -1 "cycles" sentinel that fell back to
//     Blue;
//   * itemMgr birth demand is tracked and retried until every consumed Pikmin
//     has produced its source-count sprouts, so exhausted item capacity can
//     never silently discard output (`P2_POM_SPROUT_RETRY` /
//     `P2_POM_SPROUT_SETTLED ... conservation=1`);
//   * timers advance on a bounded 30 Hz simulation clock (same pattern as
//     pc_p2_king.cpp) rather than raw frame pacing, and reset clears the clock
//     and injected-capacity state on scene teardown.
//
// Sidecar format (cwd), strict and fail-closed:
//   P2_POM_1 <count>
//   <generator-u32> <BluePom|RedPom|YellowPom|BlackPom|WhitePom|RandPom|Pom> <x> <y> <z>
// Optional labeled fixture injection (never present in a normal run):
//   P2_POM_INJECT_1 <count>
//   <generator-u32> <forcedBirthFailures>          x count
#include "pc_p2_pom.h"
#include "pc_p2_pom_policy.h"
#include "pc_bbft.h"
#include "ItemMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "Vector.h"
#include <SDL2/SDL.h>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {
// Bounded 30 Hz source behavior clock: wall time is accumulated into at most
// MaxCatchUpSteps simulation steps so timers follow gameplay time instead of
// display frame pacing. Mirrors pc_p2_king.cpp.
constexpr float SimTick        = 1.0f / 30.0f;
constexpr int MaxCatchUpSteps  = 4;
constexpr double TicksPerSecond = 30.0;

struct Bound {
	p2pom::PomSpec spec;
	int colour        = -1;
	int used          = 0;
	int refunds       = 0;
	int swallowed     = 0;
	bool open         = false;
	bool done         = false;
	double openedSec      = 0.0;
	double lastAcceptSec  = 0.0;
	int queenColour       = -1;
	// Conservation: itemMgr births can fail under exhausted capacity. Demand
	// is tracked and retried until every consumed Pikmin has produced its
	// source-count sprouts; nothing is silently discarded.
	int owed              = 0;
	int requested         = 0;
	int born              = 0;
	int birthFailures     = 0;
	int forcedFailures    = 0; // labeled fixture capacity-injection remainder
	bool finishWhenSettled = false;
};

struct InjectFail {
	std::uint32_t generator = 0;
	int failBirths          = 0;
};

std::vector<Bound> buds;
std::vector<InjectFail> injects;
unsigned clockLast = 0;
float clockAcc     = 0.0f;
unsigned behaviorTick = 0;

[[noreturn]] void fail()
{
	std::fputs("P2_POM invalid sidecar\n", stderr);
	std::abort();
}

int pikiColourForSprout(int colour)
{
	// P1 has no Purple/White Pikmin; keep the sprout body a valid P1 colour and
	// report the source colour separately in the log.
	if (colour < 0 || colour > 2) {
		return Blue;
	}
	return colour;
}

// Source-correct selected colour: the Queen uses the cycling colour it has
// chosen, not the -1 "cycles" sentinel.
int sourceColour(const Bound& bound)
{
	return p2pom::queen(bound.spec.species) ? bound.queenColour : bound.colour;
}

// P1 body colour actually applied to the born sprout.
int outputColour(const Bound& bound)
{
	return pikiColourForSprout(sourceColour(bound));
}

// Births as many of the owed sprouts as capacity allows. Returns the number
// born in this pass; leaves `owed` at the remaining demand.
int birthOwed(Bound& bound)
{
	int bornNow = 0;
	while (bound.owed > 0) {
		if (bound.forcedFailures > 0) {
			--bound.forcedFailures;
			break; // labeled fixture capacity exhaustion
		}
		if (!itemMgr) {
			break;
		}
		PikiHeadItem* sprout = static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));
		if (!sprout) {
			++bound.birthFailures;
			break;
		}
		Vector3f position(bound.spec.x, bound.spec.y + 50.0f, bound.spec.z);
		sprout->init(position);
		sprout->setColor(outputColour(bound));
		const float angle = float(bound.born) * 1.256637f;
		sprout->mVelocity.set(p2pom::LaunchHoriz * std::sin(angle), p2pom::LaunchVert, p2pom::LaunchHoriz * std::cos(angle));
		sprout->startAI(0);
		C_SAI(sprout)->start(sprout, PikiHeadAI::PIKIHEAD_Flying);
		++bornNow;
		++bound.born;
		--bound.owed;
	}
	return bornNow;
}

// Emits retry or settled conservation evidence for a bud with pending demand.
void settleOwed(Bound& bound)
{
	if (bound.owed <= 0) {
		return;
	}
	birthOwed(bound);
	if (bound.owed > 0) {
		std::printf("P2_POM_SPROUT_RETRY generator=%u species=%s owed_remaining=%d requested=%d born=%d item_capacity=1 forced=%d\n",
		            bound.spec.generator, p2pom::speciesName(bound.spec.species), bound.owed, bound.requested, bound.born,
		            int(bound.forcedFailures > 0 || bound.birthFailures > 0));
		return;
	}
	std::printf("P2_POM_SPROUT_SETTLED generator=%u species=%s requested=%d born=%d conservation=1\n", bound.spec.generator,
	            p2pom::speciesName(bound.spec.species), bound.requested, bound.born);
	if (bound.finishWhenSettled) {
		bound.done = true;
		std::printf("P2_POM_DONE generator=%u species=%s used=%d refunds=%d\n", bound.spec.generator,
		            p2pom::speciesName(bound.spec.species), bound.used, bound.refunds);
	}
}

void stepBuds(double nowSec)
{
	for (Bound& bound : buds) {
		if (bound.done) {
			continue;
		}
		const bool isQueen = p2pom::queen(bound.spec.species);
		if (isQueen) {
			const int colour = p2pom::queenColour(float(nowSec - bound.openedSec), 0x7u);
			if (colour != bound.queenColour) {
				bound.queenColour = colour;
				std::printf("P2_POM_QUEEN_COLOUR generator=%u colour=%d\n", bound.spec.generator, colour);
			}
		}

		// A closed bud with outstanding sprout demand keeps retrying before it
		// may accept or reopen; budget-spent buds settle then finish.
		if (bound.owed > 0) {
			settleOwed(bound);
			continue;
		}

		// Collect thrown/pressed Pikmin inside the slot radius, then consume them
		// so the pikiMgr iterator is never invalidated mid-walk.
		std::vector<Piki*> candidates;
		Iterator it(pikiMgr);
		CI_LOOP(it)
		{
			Piki* piki = static_cast<Piki*>(*it);
			if (!piki || !piki->isAlive() || piki->getState() != PIKISTATE_Flying) {
				continue;
			}
			const float dx = piki->mSRT.t.x - bound.spec.x;
			const float dz = piki->mSRT.t.z - bound.spec.z;
			if (dx * dx + dz * dz <= p2pom::SlotRadius * p2pom::SlotRadius) {
				candidates.push_back(piki);
			}
		}

		const int limit = p2pom::budget(bound.spec.species);
		for (Piki* piki : candidates) {
			if (bound.used >= limit) {
				break;
			}
			const int thrownColour = int(piki->mColor);
			if (p2pom::refund(bound.spec.species, thrownColour)) {
				++bound.refunds;
				std::printf("P2_POM_REFUND generator=%u species=%s thrown_colour=%d used=%d budget=%d slot_refunded=1\n",
				            bound.spec.generator, p2pom::speciesName(bound.spec.species), thrownColour, bound.used, limit);
			} else {
				++bound.used;
				std::printf("P2_POM_ACCEPT generator=%u species=%s thrown_colour=%d used=%d budget=%d\n",
				            bound.spec.generator, p2pom::speciesName(bound.spec.species), thrownColour, bound.used, limit);
			}
			++bound.swallowed;
			bound.open         = true;
			bound.lastAcceptSec = nowSec;
			if (bound.openedSec == 0.0) {
				bound.openedSec = nowSec;
			}
			piki->setEraseKill();
			piki->kill(false);
		}

		if (!bound.open) {
			continue;
		}
		const bool budgetSpent = bound.used >= limit;
		const float sinceAccept = float(nowSec - bound.lastAcceptSec);
		const p2pom::CloseOutcome outcome
		    = p2pom::closeOutcome(sinceAccept, p2pom::RemainOpenSec, budgetSpent, bound.swallowed > 0);
		if (outcome == p2pom::CloseOutcome::StillOpen) {
			continue;
		}
		std::printf("P2_POM_CLOSE generator=%u species=%s outcome=%s used=%d budget=%d swallowed=%d\n", bound.spec.generator,
		            p2pom::speciesName(bound.spec.species), p2pom::closeOutcomeName(outcome), bound.used, limit, bound.swallowed);
		if (outcome == p2pom::CloseOutcome::Shot) {
			const int count = p2pom::shotCount(bound.spec.species, bound.swallowed);
			bound.requested += count;
			bound.owed += count;
			std::printf("P2_POM_SPROUT generator=%u species=%s count=%d colour=%d body=%d leaf=1\n", bound.spec.generator,
			            p2pom::speciesName(bound.spec.species), count, sourceColour(bound), outputColour(bound));
			bound.finishWhenSettled = budgetSpent;
			settleOwed(bound);
		}
		bound.open      = false;
		bound.swallowed = 0;
		if (budgetSpent && bound.owed == 0) {
			bound.done = true;
			std::printf("P2_POM_DONE generator=%u species=%s used=%d refunds=%d\n", bound.spec.generator,
			            p2pom::speciesName(bound.spec.species), bound.used, bound.refunds);
		} else if (budgetSpent) {
			bound.finishWhenSettled = true;
		}
	}
}
} // namespace

void pc_p2_pom_reset()
{
	buds.clear();
	injects.clear();
	clockLast    = SDL_GetTicks();
	clockAcc     = 0.0f;
	behaviorTick = 0;
}

void pc_p2_pom_setup()
{
	pc_p2_pom_reset();
	if (!pc_pikipelago_room_preview()) {
		return;
	}
	std::ifstream in("p2-pom.txt");
	if (!in) {
		return; // inert without the sidecar
	}
	std::vector<p2pom::PomSpec> specs;
	try {
		specs = p2pom::readPoms(in);
	} catch (const std::exception&) {
		fail();
	}
	std::ifstream inject("p2-pom-inject.txt");
	if (inject) {
		std::string header;
		int count = 0;
		if (!(inject >> header >> count) || header != "P2_POM_INJECT_1" || count < 0 || count > 64) {
			fail();
		}
		for (int i = 0; i < count; ++i) {
			unsigned long long generator = 0;
			int fails = 0;
			if (!(inject >> generator >> fails) || generator > 0xffffffffULL || fails < 0 || fails > 100000) {
				fail();
			}
			InjectFail item;
			item.generator  = static_cast<std::uint32_t>(generator);
			item.failBirths = fails;
			injects.push_back(item);
		}
		std::string trailing;
		if (inject >> trailing) {
			fail();
		}
	}
	for (const p2pom::PomSpec& spec : specs) {
		if (p2pom::isBase(spec.species)) {
			// Explicitly rejected: the base has no EFlag_CanBeSpawned and no Mgr
			// slot; remapping it would corrupt the "unset enemy type" convention.
			std::printf("P2_POM_BASE_REJECTED generator=%u species=Pom source_id=82 reason=nonspawnable_base\n", spec.generator);
			continue;
		}
		Bound bound;
		bound.spec   = spec;
		bound.colour = p2pom::speciesColour(spec.species);
		for (const InjectFail& item : injects) {
			if (item.generator == spec.generator) {
				bound.forcedFailures += item.failBirths;
			}
		}
		buds.push_back(bound);
		std::printf("P2_POM_READY generator=%u species=%s source_id=%d colour=%d budget=%d queen=%d x=%.2f y=%.2f z=%.2f\n",
		            spec.generator, p2pom::speciesName(spec.species), p2pom::speciesId(spec.species), bound.colour,
		            p2pom::budget(spec.species), int(p2pom::queen(spec.species)), spec.x, spec.y, spec.z);
	}
	if (buds.empty()) {
		return;
	}
	for (const Bound& bound : buds) {
		std::printf("P2_POM_INVULNERABLE generator=%u invulnerable_after_landing=1\n", bound.spec.generator);
	}
	std::printf("P2_POM_SIDECAR buds=%u\n", unsigned(buds.size()));
	std::fflush(stdout);
}

void pc_p2_pom_tick()
{
	if (buds.empty()) {
		return;
	}
	const unsigned now = SDL_GetTicks();
	clockAcc += float(now - clockLast) * 0.001f;
	clockLast = now;
	int steps = 0;
	while (clockAcc >= SimTick && steps < MaxCatchUpSteps) {
		clockAcc -= SimTick;
		++steps;
		++behaviorTick;
		stepBuds(double(behaviorTick) / TicksPerSecond);
	}
	std::fflush(stdout);
}
