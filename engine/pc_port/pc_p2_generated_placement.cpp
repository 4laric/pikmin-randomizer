#include "pc_randomizer.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_campaign_placements.h"
#include "pc_p2_generated_placement.h"
#include "pc_p2_sarai_manager.h"
#include "pc_p2_otakara.h"
#include "pc_p2_bluechappy.h"
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
MuseBinding g_museBindings[64];
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
    if (g_museBound >= 64) return false;
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
    if (wanted.empty()) return false;
    bool bound = false;
    Iterator actors(tekiMgr);
    CI_LOOP(actors) {
        BTeki* actor = static_cast<BTeki*>(*actors);
        if (!actor || !actor->mGenerator) continue;
        const unsigned token = pc_p2_campaign_token(actor);
        if (!wanted.count(token)) continue;
        // The dynamic binder skips already-bound actors and actors whose
        // sidecar is absent, quietly returning false for both.
        if (pc_p2_sarai_manager_bind_dynamic(actor, token, token)) bound = true;
    }
    return bound;
}

static bool recordBind(BTeki* actor, unsigned accepted, unsigned sourceId,
                       unsigned seedTargetUid, unsigned generatorId)
{
    if (!actor || !sourceId || !seedTargetUid || !accepted) {
        std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u generator=%u bound=0 reason=bad-request\n",
                    sourceId, seedTargetUid, generatorId);
        std::fflush(stdout);
        return false;
    }
    if (seedTargetUid != accepted) {
        std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u generator=%u bound=0 reason=slot-rejected\n",
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

static bool museBind(BTeki* actor, unsigned sourceId, unsigned seedTargetUid, unsigned generatorId)
{
    const bool campaign = pc_randomizer_p2_bridge()
        && pc_randomizer_p2_source_for_id(seedTargetUid) == sourceId
        && p2campaign::accepted(sourceId, seedTargetUid);
    return recordBind(actor, campaign ? seedTargetUid : pc_p2_generated_placement_muse_slot(sourceId),
                      sourceId, seedTargetUid, generatorId);
}

static bool waterwraithBind(BTeki* actor, unsigned sourceId, unsigned seedTargetUid, unsigned generatorId)
{
    return recordBind(actor, pc_p2_generated_placement_waterwraith_slot(sourceId), sourceId, seedTargetUid, generatorId);
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
    case 42: // Orange Bulborb (BlueChappy, adult); lane 42.
        if (pc_p2_bluechappy_bind_dynamic(actor, generatorId, sourceId)) {
            std::printf("P2_GENERATED_PLACEMENT source_id=42 target=%u bound=1\n", seedTargetUid);
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
    case 41: // Antenna Beetle (Fuefuki); muse observer lane 57.
    case 57: // Lesser Spotted Jellyfloat (Kurage); muse observer lane 58.
    case 58: // Careening Dirigibug (BombSarai); muse observer lane 59.
    case 78: // Gatling Groink (MiniHoudai); muse observer lane 60.
        return museBind(actor, sourceId, seedTargetUid, generatorId);
    case 99: // Waterwraith (BlackMan); provider #575, consumer lane 572.
        return waterwraithBind(actor, sourceId, seedTargetUid, generatorId);
    default:
        return false;
    }
}
