// Headless marker-contract fixture for MiniHoudai78 correlated birth.
// Lane muse-groink (#500). This file is compiled by the isolated fixture
// build only; it is not part of the game target and it alters no family,
// placement, or shared module.
//
// Contract under test (deterministic, no GL, no engine actors):
//   p2-groink-teki.txt          parsed by the REAL p2groink::read sidecar parser
//   p2-placement-slots.txt      P2_PLACEMENT_SLOTS_1 + <generator> <slot> rows
//                               (same shape pc_p2_placement_probe_run reads)
//   p2-muse-groink-resolve.txt  P2_MUSE_GROINK_RESOLVE_1 <source_id> <target> <generator>
//
// The fixture requires source_id=78, the resolve target to equal the slot uid
// for the sidecar generator, then drives a REAL P2GroinkCarcass through
// become/step until the policy itself emits RequestBirth. Markers mirror the
// root observer (experimental/pikmin2_muse_groink.py muse_contract):
//   P2_MUSE_GROINK_SIDECAR / _SLOT / _RESOLVE / _BIRTH_POLICY, then
//   PASS MUSE_GROINK_CORRELATED (exit 0) or FAIL MUSE_GROINK_CORRELATED
//   reason=<...> (exit 1).
//
// This proves the sidecar parser, slot/resolve wiring, and carcass birth leg.
// Generation 2 also asserts the reviewed muse-placement slot contract at
// runtime: the header-inline accepted slot for 78 must equal the staged uid,
// 78 must be a muse candidate, and pedestal 97 must be excluded (returns 0).
// It is labeled contract evidence, never a natural gameplay birth.
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <string>

#include "../pc_port/pc_p2_generated_placement.h"
#include "../pc_port/pc_p2_groink_teki_policy.h"

namespace {

void fail(const char* reason) {
    std::printf("FAIL MUSE_GROINK_CORRELATED reason=%s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

bool readSlots(const char* path, std::map<unsigned, unsigned>& out) {
    std::ifstream in(path);
    if (!in) return false;
    std::string magic;
    if (!(in >> magic) || magic != "P2_PLACEMENT_SLOTS_1") return false;
    unsigned generator = 0, slot = 0;
    while (in >> generator >> slot) out[generator] = slot;
    return true;
}

struct Resolve {
    unsigned sourceId = 0;
    unsigned target = 0;
    unsigned generator = 0;
};

bool readResolve(const char* path, Resolve& out) {
    std::ifstream in(path);
    if (!in) return false;
    std::string magic;
    unsigned count = 0;
    if (!(in >> magic >> count)) return false;
    if (magic != "P2_MUSE_GROINK_RESOLVE_1" || count != 1) return false;
    if (!(in >> out.sourceId >> out.target >> out.generator)) return false;
    return out.sourceId != 0 && out.target != 0 && out.generator != 0;
}

} // namespace

int main() {
    p2groink::Binding binding;
    {
        std::ifstream sidecar("p2-groink-teki.txt");
        if (!sidecar || !p2groink::read(sidecar, binding)) fail("sidecar_parse");
    }
    std::printf("P2_MUSE_GROINK_SIDECAR generator=%u type=%d\n", binding.generator, binding.type);
    std::fflush(stdout);

    std::map<unsigned, unsigned> slots;
    if (!readSlots("p2-placement-slots.txt", slots)) fail("slots_parse");
    const auto slotIt = slots.find(binding.generator);
    if (slotIt == slots.end() || slotIt->second == 0) fail("slot_unmapped");
    std::printf("P2_MUSE_GROINK_SLOT generator=%u slot=%u\n", binding.generator, slotIt->second);
    std::fflush(stdout);

    Resolve resolve;
    if (!readResolve("p2-muse-groink-resolve.txt", resolve)) fail("resolve_parse");
    if (resolve.sourceId != 78) fail("resolve_source");
    if (resolve.generator != binding.generator) fail("resolve_generator");
    if (resolve.target != slotIt->second) fail("slot_disagree");
    std::printf("P2_MUSE_GROINK_RESOLVE source_id=%u target=%u\n", resolve.sourceId, resolve.target);
    std::fflush(stdout);

    // Reviewed slot contract (muse-placement l52/#492): the staged uid must
    // equal the native accepted slot for 78; 97 stays excluded.
    if (!pc_p2_generated_placement_is_muse_candidate(78)) fail("slot_candidate");
    if (pc_p2_generated_placement_muse_slot(78) != slotIt->second) fail("slot_contract");
    if (pc_p2_generated_placement_muse_slot(97) != 0) fail("pedestal_excluded");
    std::printf("P2_MUSE_GROINK_SLOT_CONSTANTS source=78 slot=%u pedestal=0\n",
                pc_p2_generated_placement_muse_slot(78));
    std::fflush(stdout);

    // Real carcass birth leg: the sidecar config must drive the policy itself
    // to RequestBirth (pellet alive, gauge managed, fixed small ticks).
    P2GroinkCarcass carcass;
    if (!carcass.become(binding.carcass)) fail("carcass_reject");
    bool birth = false;
    for (int tick = 0; tick < 100000 && !birth; ++tick) {
        const P2GroinkCarcassStep step = carcass.step(0.016f, true, true, true);
        if (!step.valid) fail("carcass_invalid");
        for (std::size_t i = 0; i < step.count; ++i) {
            if (step.commands[i] == P2GroinkCarcassCommand::RequestBirth) birth = true;
        }
    }
    if (!birth) fail("carcass_no_birth");
    std::printf("P2_MUSE_GROINK_BIRTH_POLICY births=1 timer_done=1\n");
    std::printf("PASS MUSE_GROINK_CORRELATED\n");
    std::fflush(stdout);
    return 0;
}
