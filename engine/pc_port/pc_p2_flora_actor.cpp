// Opt-in P2 Pellet Posy (Pelplant, enemy ID 0) release + capture receptor (#171).
//
// The existing P1 Palm actor already owns the visuals and the fell/pellet-drop
// mechanics; this module is a native, sidecar-gated policy layer on top:
//   * full-only vulnerability: small and growing posies are made invulnerable
//     and any stored damage is discarded (Pelplant.h:187-190),
//   * instant fell on the s__0 head: P1's flower-damage route already fells a
//     fully grown posy on a direct head hit (pelplant.cpp:485,518); the head
//     portion is observed and logged,
//   * dead-state release: P1 spawnItems drops the configured number pellet
//     (pelplantState.cpp:445-451); the released pellet is claimed here so the
//     Pikmin capture is observable,
//   * no regrowth: the P1 Palm has no regrowth timer, matching the audit.
//
// The Onion-side seed receipt is NOT implemented here: a captured pellet that
// reaches a receiver is reported with seeds=0 and onion_slice_unimplemented=1.
// Absent p2-flora-pelplant.txt the module is inert; a malformed sidecar aborts
// (fail-closed) rather than silently falling back to P1 behaviour.
//
// Binding is two-phase: the sidecar is parsed and kept as pending specs, and a
// spec is promoted to a bound posy as soon as a live TEKI_Palm with that
// generator id exists. Generator actors can appear after GameCoreSection
// finalSetup, so setup does not abort on a not-yet-spawned proxy; a spec that
// never resolves simply never emits its READY/observation lines.
#include "pc_p2_flora_actor.h"
#include "pc_p2_flora_policy.h"
#include "pc_bbft.h"
#include "Generator.h"
#include "Pellet.h"
#include "teki.h"
#include "TekiPersonality.h"
#include "system.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <vector>

namespace {
// A bound P1 Palm proxy plus the release/capture observation state. The pellet
// pointers are only compared, never dereferenced after death, so a recycled
// address at worst mislabels one event within this bounded slice.
struct Bound {
	BTeki* actor          = nullptr;
	p2flora::PelplantSpec spec;
	bool fell             = false;
	bool fellLogged       = false;
	bool releaseLogged    = false;
	bool captureLogged    = false;
	bool receiptLogged    = false;
	Pellet* released      = nullptr;

	unsigned generator() const { return spec.generator; }
	unsigned pelletSize() const { return unsigned(spec.pellet); }
	int colour() const { return spec.colour; }
};

std::vector<p2flora::PelplantSpec> pending;
std::vector<Bound> posies;
std::vector<Pellet*> knownPellets;   // present before any posy fell
std::vector<Pellet*> trackedPellets; // claimed from a fell posy
bool scannedActors = false;          // one-shot binding diagnostic

void fail()
{
	std::fputs("P2_FLORA_PELPLANT invalid sidecar\n", stderr);
	std::abort();
}

bool contains(const std::vector<Pellet*>& list, Pellet* pellet)
{
	for (Pellet* entry : list) {
		if (entry == pellet) {
			return true;
		}
	}
	return false;
}

void collectPellets(std::vector<Pellet*>& out)
{
	if (!pelletMgr) {
		return;
	}
	Iterator it(pelletMgr);
	CI_LOOP(it)
	{
		Pellet* pellet = static_cast<Pellet*>(*it);
		if (pellet) {
			out.push_back(pellet);
		}
	}
}

const char* colourName(int colour)
{
	if (colour < 0) {
		return "random";
	}
	if (colour == 0) {
		return "blue";
	}
	if (colour == 1) {
		return "red";
	}
	return "yellow";
}

// Stamp the P1 Palm proxy with the source growth stage and vulnerability.
// The pellet identity (kind/colour/chance) is deliberately NOT rewritten: the
// P1 arena only loads the pellet configs the stage references, and forcing a
// different kind makes newNumberPellet return null, so spawnPellets releases
// nothing. The proxy keeps its own loaded pellet; the sidecar's declared
// pellet/colour are recorded and compared against what actually drops.
void configure(Bound& bound)
{
	BTeki* actor       = bound.actor;
	const int strength = static_cast<int>(bound.spec.stage);
	actor->setPersonalityF(TekiPersonality::FLT_Strength, float(strength));
	if (strength >= 2) {
		actor->clearTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
	} else {
		actor->setTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
	}
}

// Promote every pending spec that now has a live TEKI_Palm proxy.
void bindPending()
{
	if (pending.empty() || !tekiMgr) {
		return;
	}
	if (!scannedActors) {
		scannedActors = true;
		int count    = 0;
		Iterator diag(tekiMgr);
		CI_LOOP(diag)
		{
			Teki* teki = static_cast<Teki*>(*diag);
			if (!teki) {
				continue;
			}
			const unsigned uid = teki->mGenerator ? teki->mGenerator->_70 : 0;
			std::printf("P2_FLORA_PELPLANT_SCAN generator=%u type=%d palm=%d\n", uid, int(teki->mTekiType),
			            int(teki->mTekiType == TEKI_Palm));
			if (++count >= 64) {
				break;
			}
		}
		std::printf("P2_FLORA_PELPLANT_SCAN_TOTAL actors=%d wanted=%u\n", count, pending.front().generator);
		std::fflush(stdout);
	}
	for (auto it = pending.begin(); it != pending.end();) {
		Teki* found = nullptr;
		Iterator scan(tekiMgr);
		CI_LOOP(scan)
		{
			Teki* teki = static_cast<Teki*>(*scan);
			if (!teki || !teki->mGenerator || teki->mGenerator->_70 != it->generator) {
				continue;
			}
			if (teki->mTekiType != TEKI_Palm || found) {
				fail();
			}
			found = teki;
		}
		if (!found) {
			++it;
			continue;
		}
		Bound bound;
		bound.actor = found;
		bound.spec  = *it;
		posies.push_back(bound);
		configure(posies.back());
		std::printf("P2_FLORA_PELPLANT_READY generator=%u stage=%s pellet=%d colour=%s visual=P1_Palm_proxy "
		            "source_fsm=p1_palm_pellet_policy=2\n",
		            it->generator, p2flora::stageName(it->stage), it->pellet, colourName(it->colour));
		it = pending.erase(it);
	}
}
} // namespace

void pc_p2_flora_reset()
{
	posies.clear();
	pending.clear();
	knownPellets.clear();
	trackedPellets.clear();
	scannedActors = false;
}

void pc_p2_flora_forget(BTeki* actor)
{
	for (auto it = posies.begin(); it != posies.end(); ++it) {
		if (it->actor == actor) {
			posies.erase(it);
			return;
		}
	}
}

void pc_p2_flora_setup()
{
	pc_p2_flora_reset();
	if (!pc_pikipelago_room_preview() || !tekiMgr) {
		return;
	}
	std::ifstream in("p2-flora-pelplant.txt");
	if (!in) {
		return; // inert without the sidecar
	}
	try {
		pending = p2flora::readPelplants(in);
	} catch (const std::exception&) {
		fail();
	}

	bindPending();

	std::vector<Pellet*> existing;
	collectPellets(existing);
	knownPellets = existing;
	if (posies.empty() && pending.empty()) {
		return;
	}
	std::printf("P2_FLORA_PELPLANT_SIDECAR bound=%u pending=%u existing_pellets=%u\n", unsigned(posies.size()),
	            unsigned(pending.size()), unsigned(knownPellets.size()));
	std::fflush(stdout);
}

void pc_p2_flora_tick()
{
	if (!pending.empty()) {
		bindPending();
	}
	if (posies.empty()) {
		return;
	}
	std::vector<Pellet*> current;
	collectPellets(current);

	// Vulnerability policy and fell observation.
	for (Bound& bound : posies) {
		BTeki* actor = bound.actor;
		if (!actor) {
			continue;
		}
		if (!actor->isAlive()) {
			if (!bound.fellLogged) {
				bound.fell       = true;
				bound.fellLogged = true;
				const bool head  = actor->_344 == 0;
				std::printf("P2_FLORA_PELPLANT_FELL generator=%u stage=%s instant_fell_head=%d pellet=%d "
				            "released_on_death=1 regrowth=0\n",
				            bound.generator(), p2flora::stageName(bound.spec.stage), int(head), bound.spec.pellet);
			}
			continue;
		}
		const int strength = int(actor->getPersonalityF(TekiPersonality::FLT_Strength));
		if (strength >= 2) {
			actor->clearTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
		} else {
			actor->setTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
			actor->mStoredDamage = 0.0f;
		}
	}

	// Claim the pellet a fell posy dropped (P1 spawnItems performs the actual
	// release; we only bind the new number pellet for observation).
	for (Bound& bound : posies) {
		if (!bound.fell || bound.releaseLogged || !bound.actor) {
			continue;
		}
		for (Pellet* pellet : current) {
			if (!pellet->isAlive() || pellet->isUfoParts()) {
				continue;
			}
			if (contains(knownPellets, pellet) || contains(trackedPellets, pellet)) {
				continue;
			}
			bound.released      = pellet;
			bound.releaseLogged = true;
			trackedPellets.push_back(pellet);
			const int actualType  = pellet->mConfig->mPelletType();
			const int actualColour = pellet->mConfig->mPelletColor();
			const bool declared    = actualType == bound.spec.pellet && actualColour == bound.spec.colour;
			std::printf("P2_FLORA_PELLET_RELEASED generator=%u pellet=%d colour=%d declared_pellet=%d declared_colour=%d "
			            "declared_match=%d capture_receptor=1\n",
			            bound.generator(), actualType, actualColour, bound.spec.pellet, bound.spec.colour, int(declared));
			break;
		}
	}

	// Capture receptor: a Pikmin starts carrying the released pellet.
	for (Bound& bound : posies) {
		if (!bound.released || bound.captureLogged || !bound.released->isAlive()) {
			continue;
		}
		if (bound.released->mCarrierCount >= 1) {
			bound.captureLogged = true;
			std::printf("P2_FLORA_PELLET_CAPTURED generator=%u carriers=%u carrier=%p\n", bound.generator(),
			            unsigned(bound.released->mCarrierCount), static_cast<void*>(bound.released->mPikiCarrier));
		}
	}
}

bool pc_p2_flora_receipt(Pellet* pellet)
{
	if (!pellet) {
		return false;
	}
	for (Bound& bound : posies) {
		if (bound.released != pellet) {
			continue;
		}
		if (!bound.receiptLogged) {
			bound.receiptLogged = true;
			std::printf("P2_FLORA_ONION_RECEIPT generator=%u pellet=%d pokos=0 seeds=0 onion_slice_unimplemented=1\n",
			            bound.generator(), bound.spec.pellet);
		}
		return true;
	}
	return false;
}
