#include "pc_randomizer.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_generated_placement.h"
#include "pc_p2_sarai_manager.h"
#include "pc_p2_campaign_policy.h"
#include "pc_p2_otakara.h"
#include "pc_p2_bluechappy.h"
#include "pc_p2_chappy.h"
#include "teki.h"
#include <cstdio>
#include <set>

namespace {
struct MuseBinding {
    const BTeki* actor;
    unsigned source;
    unsigned target;
    unsigned generator;
};
// Sized for every ordinary generator a seed can bind to a sidecar-recorded
// family in one stage (#948); `registry-full` is logged past it.
static const int kMaxRecords = 128;
MuseBinding g_museBindings[kMaxRecords];
int g_museBound = 0;

bool museRecord(const BTeki* actor, unsigned source, unsigned target, unsigned generator)
{
    for (int i = 0; i < g_museBound; ++i) {
        if (g_museBindings[i].actor == actor) {
            g_museBindings[i].source = source;
            g_museBindings[i].target = target;
            g_museBindings[i].generator = generator;
            return true;
        }
    }
    if (g_museBound >= kMaxRecords) return false;
    g_museBindings[g_museBound].actor = actor;
    g_museBindings[g_museBound].source = source;
    g_museBindings[g_museBound].target = target;
    g_museBindings[g_museBound].generator = generator;
    ++g_museBound;
    return true;
}
} // namespace

bool pc_p2_generated_placement_is_bound(const BTeki* actor)
{
    if (!actor) return false;
    for (int i = 0; i < g_museBound; ++i) {
        if (g_museBindings[i].actor == actor) return true;
    }
    return false;
}

int pc_p2_generated_placement_bound_count()
{
    return g_museBound;
}

void pc_p2_generated_placement_forget(const BTeki* actor)
{
    if (!actor) return;
    for (int i = 0; i < g_museBound; ++i) {
        if (g_museBindings[i].actor == actor) {
            for (int j = i + 1; j < g_museBound; ++j) g_museBindings[j - 1] = g_museBindings[j];
            --g_museBound;
            return;
        }
    }
}

void pc_p2_generated_placement_reset()
{
    g_museBound = 0;
}

bool pc_p2_generated_placement_sweep_sarai()
{
    if (!pc_randomizer_p2_bridge() || !tekiMgr) return false;
    const std::set<unsigned> wanted = pc_p2_campaign_ids(23);
    // #215: Demon (32) rides the same host/manager with its species profile.
    const std::set<unsigned> demons = pc_p2_campaign_ids(32);
    if (wanted.empty() && demons.empty()) return false;
    bool bound = false;
    Iterator actors(tekiMgr);
    CI_LOOP(actors) {
        BTeki* actor = static_cast<BTeki*>(*actors);
        if (!actor || !actor->mGenerator) continue;
        const unsigned token = pc_p2_campaign_token(actor);
        if (demons.count(token)) {
            if (pc_p2_sarai_manager_bind_demon(actor, token, token)) bound = true;
            continue;
        }
        if (!wanted.count(token)) continue;
        // The dynamic binder skips already-bound actors and actors whose
        // sidecar is absent, quietly returning false for both.
        if (pc_p2_sarai_manager_bind_dynamic(actor, token, token)) bound = true;
    }
    return bound;
}

// Record a seed-resolved sidecar bind (57/58/78/99). The only checks are
// runtime ones (#948): the seed must actually bind this source at this
// target, and the per-stage registry must have room. Slot ids are never
// compared against a compiled list.
static bool recordBind(BTeki* actor, unsigned sourceId, unsigned seedTargetUid, unsigned generatorId)
{
    if (!actor || !sourceId || !seedTargetUid) {
        std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u generator=%u bound=0 reason=bad-request\n",
                    sourceId, seedTargetUid, generatorId);
        std::fflush(stdout);
        return false;
    }
    if (!pc_randomizer_p2_bridge() || pc_randomizer_p2_source_for_id(seedTargetUid) != sourceId) {
        std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u generator=%u bound=0 reason=seed-target-mismatch\n",
                    sourceId, seedTargetUid, generatorId);
        std::fflush(stdout);
        return false;
    }
    if (!museRecord(actor, sourceId, seedTargetUid, generatorId)) {
        std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u generator=%u bound=0 reason=registry-full\n",
                    sourceId, seedTargetUid, generatorId);
        std::fflush(stdout);
        return false;
    }
    std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u generator=%u bound=1\n",
                sourceId, seedTargetUid, generatorId);
    std::fflush(stdout);
    // Placement accepted, but no P2 behavior module has taken the actor: the
    // family sidecar path still owns behavior. Callers must not read bound=1
    // as a family FSM claim.
    return false;
}

bool pc_p2_generated_placement_bind(BTeki* actor, unsigned sourceId, unsigned seedTargetUid, unsigned generatorId)
{
    if (!actor || !sourceId) return false;
    switch (sourceId) {
    case 23: // Swooping Snitchbug (Sarai); lane 30.
        if (pc_p2_sarai_manager_bind_dynamic(actor, generatorId, seedTargetUid)) {
            std::printf("P2_GENERATED_PLACEMENT source_id=23 target=%u bound=1\n", seedTargetUid);
            std::fflush(stdout);
            return true;
        }
        return false;
    case 32: // Bumbling Snitchbug (Demon), Sarai host species profile (#215).
        // The newborn actor has no generator yet (campaign token 0), so the
        // birth-time claim defers and the setup sweep binds it.
        if (!actor->mGenerator) {
            std::printf("P2_GENERATED_PLACEMENT source_id=32 target=%u bound=0 reason=deferred_to_setup_sweep\n",
                        seedTargetUid);
            std::fflush(stdout);
            return false;
        }
        if (pc_p2_sarai_manager_bind_demon(actor, generatorId, seedTargetUid)) {
            std::printf("P2_GENERATED_PLACEMENT source_id=32 target=%u bound=1\n", seedTargetUid);
            std::fflush(stdout);
            return true;
        }
        return false;
    case 42: // Orange Bulborb (BlueChappy, adult); lane 42.
        if (pc_p2_bluechappy_bind_dynamic(actor, generatorId, sourceId)) {
            std::printf("P2_GENERATED_PLACEMENT source_id=42 target=%u bound=1\n", seedTargetUid);
            std::fflush(stdout);
            return true;
        }
        return false;
    case 2: // Red Bulborb (Chappy); inst-chappy lane.
    case 33: // Fiery Bulblax (FireChappy); inst-chappy lane.
    case 35: // Spotty Bulbear (KumaChappy); inst-chappy lane.
    case 43: // Hairy Bulborb (YellowChappy); inst-chappy lane.
    case 53: // Emperor Bulblax (KingChappy); inst-chappy lane.
    case 67: // Bulbmin (LeafChappy); inst-chappy lane.
    case 76: // Dwarf Bulbear (KumaKochappy); inst-chappy lane.
        if (pc_p2_chappy_bind_dynamic(actor, generatorId, sourceId)) {
            std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u bound=1\n", sourceId,
                        seedTargetUid);
            std::fflush(stdout);
            return true;
        }
        return false;
    case 59: // elemental Otakara Dweevils; lane 22.
    case 60:
    case 61:
    case 62:
        if (pc_p2_otakara_bind_dynamic(actor, generatorId, sourceId)) {
            std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u bound=1\n", sourceId, seedTargetUid);
            std::fflush(stdout);
            return true;
        }
        return false;
    case 41: // Antenna Beetle (Fuefuki); #245 OWN campaign module.
        // pc_p2_fuefuki_teki_setup binds the seed actor to the source FSM
        // (hostType 41 -> TEKI_Chappy, suppressed host AI) at finalSetup.
        if (pc_randomizer_p2_bridge() && pc_randomizer_p2_source_for_id(seedTargetUid) == 41) {
            std::printf("P2_GENERATED_PLACEMENT source_id=41 target=%u generator=%u bound=1 module=fuefuki_teki\n",
                        seedTargetUid, generatorId);
            std::fflush(stdout);
            return true;
        }
        std::printf("P2_GENERATED_PLACEMENT source_id=41 target=%u generator=%u bound=0 reason=seed-target-mismatch\n",
                    seedTargetUid, generatorId);
        std::fflush(stdout);
        return false;
    case 57: // Lesser Spotted Jellyfloat (Kurage); muse observer lane 58.
    case 72: // Greater Spotted Jellyfloat (OniKurage); #960 rides the Kurage OWN module.
    case 58: // Careening Dirigibug (BombSarai); muse observer lane 59.
    case 78: // Gatling Groink (MiniHoudai); muse observer lane 60.
    case 99: // Waterwraith (BlackMan); provider #575, consumer lane 572.
        return recordBind(actor, sourceId, seedTargetUid, generatorId);
    default:
        // Every other campaign id binds in its family setup sweep (keyed by
        // pc_p2_campaign_ids), which needs the vehicle from
        // p2campaign::hostType. A seed-bound id with no static host has no
        // campaign-keyed module; say so instead of birthing a bare P1 actor
        // silently (#948, #951 U25). A proxy-tier row may still claim it.
        if (pc_randomizer_p2_bridge() && pc_randomizer_p2_source_for_id(seedTargetUid) == sourceId
            && !p2campaign::hasStaticHost(sourceId)) {
            std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u generator=%u bound=0 reason=no-campaign-module\n",
                        sourceId, seedTargetUid, generatorId);
            std::fflush(stdout);
        }
        return false;
    }
}
