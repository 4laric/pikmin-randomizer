// Family-owned corpse receipt adapter for the Puffy Blowhog (Mar, EnemyID 29).
// Binds TEKI_Mar actors to generators and resolves a delivered corpse view to
// a generator for the shared Pod dispatch. Mirrors the kurage/groink receipt
// shape: live-plus-corpse lookup in one registry, first-resolution marker,
// forget/reset clearing. Source: Mar death path emits P2_MAR_DEAD
// (pc_p2_mar.cpp:452); this adapter adds the receipt half that path lacks.
// No other lane module is modified; every hook is a no-op for unregistered
// actors. Shared dispatch wiring (pc_p2_preview.cpp arm) needs #186 review.
#include "pc_p2_mar_receipt.h"
#include "teki.h"
#include "Generator.h"
#include <cstdio>
#include <map>
#include <set>

namespace {
// view -> generator for bound Mar actors; entries persist after death so a
// delivered corpse pellet (whose mPelletView is the dead actor) still resolves.
std::map<PelletView*, unsigned> bound;
// Generators already reported via P2_MAR_CORPSE_READY (first resolution only,
// so the marker proves the dispatch path fired exactly once per corpse).
std::set<unsigned> reported;
bool ready = false;

unsigned genOf(const BTeki* actor) {
    return actor && actor->mGenerator ? actor->mGenerator->_70 : 0u;
}
} // namespace

void pc_p2_mar_receipt_setup() {
    bound.clear();
    reported.clear();
    ready = true;
}

void pc_p2_mar_receipt_reset() {
    bound.clear();
    reported.clear();
    ready = false;
}

bool pc_p2_mar_receipt_bind(BTeki* actor) {
    if (!ready || !actor) return false;
    const unsigned generator = genOf(actor);
    if (generator == 0u) return false;
    PelletView* view = static_cast<PelletView*>(actor);
    if (bound.count(view) != 0) return true; // idempotent re-bind
    bound[view] = generator;
    std::printf("P2_MAR_RECEIPT_BIND generator=%u source_id=29\n", generator);
    std::fflush(stdout);
    return true;
}

bool pc_p2_mar_receipt(PelletView* view, unsigned& generator) {
    if (!ready || !view) return false;
    auto it = bound.find(view);
    if (it == bound.end()) return false;
    generator = it->second;
    if (reported.insert(generator).second) {
        std::printf("P2_MAR_CORPSE_READY generator=%u source_id=29 receipt=corpse:mar:%u\n",
                    generator, generator);
        std::fflush(stdout);
    }
    return true;
}

unsigned long pc_p2_mar_receipt_count() { return (unsigned long)bound.size(); }

bool pc_p2_mar_receipt_registered(BTeki* actor) {
    if (!actor) return false;
    return bound.count(static_cast<PelletView*>(actor)) != 0;
}

void pc_p2_mar_receipt_forget(BTeki* actor) {
    if (!actor) return;
    bound.erase(static_cast<PelletView*>(actor));
}