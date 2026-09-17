#pragma once
// Native flora hookup bridge: drives the #697 converter from live facts (#723).
//
// Engine-free and dependency-free (only the #697 header): the guarded fixture
// links this bridge plus the converter and proves it fires with markers. The
// shared-engine per-tick call (pc_bbft.cpp) and CMake membership are a
// serialized follow-on owned by #722; this bridge never touches shared files.
// The EngineHooks seams declared in pc_p2_flora_convert.h stay the #171/#186
// review surface; this bridge implements the same policy inline so the
// fixture can prove firing without shared edits.
#include <cstddef>

#include "pc_p2_flora_convert.h"

namespace p2florahookup {

// Live facts for one swallow event (mirrors the Pom shotPikmin inputs).
struct HookupFacts {
    p2flora::Species species;
    int swallowed;
    bool ownColour;
    int pikiKind; // 0..6 native Piki kind presented at the mouth
};

// Admission policy for the mouth (admitSwallow seam, read-only mirror).
// Refuses unknown species, negative swallows and out-of-range Piki kinds.
bool hookupAdmit(const HookupFacts& facts);

// One driven conversion: admit, convert, route every sprout to its receiver
// (receiveSprout seam: all routed sprouts count as received here), then emit
// the CONVERT/SPROUT marker lines. Returns sprouts routed, or -1 on refusal.
int hookupConvert(const HookupFacts& facts);

// Scenery binding driver (bindScenery seam): registers the prop identity in
// the given registry and emits the SCENERY marker line. Returns the slot
// index, or -1 on refusal.
int hookupBindScenery(p2flora::SceneryRegistry& registry, const char* identity, int slot);

// Bridge self-check used by the guarded fixture: runs a fixed live-facts
// session (BluePom swallow 3, queen swallow 1, Pelplant 5, one scenery bind)
// and emits DONE/PASS marker lines. Returns failure count.
int p2_flora_hookup_suite();

} // namespace p2florahookup
