#include "pc_p2_campaign_actor.h"
#include "pc_p2_sarai_manager.h"
#include "pc_p2_generated_placement.h"
#include "pc_p2_sarai_host.h"
#include "pc_p2_retail_player.h"
#include "pc_randomizer.h"
#include "Generator.h"
#include "Graphics.h"
#include "teki.h"
#include "system.h"
#include "sysNew.h"
#include "gameflow.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <memory>
#include <string>
#include <vector>

namespace {
struct Binding {
    P2SaraiHost* host;
    unsigned generator;
    int type;
};
std::map<BTeki*, Binding> s;
std::vector<std::unique_ptr<P2SaraiHost>> hosts;
// Naturally dead Sarai anchors: kept until the central forget/reset seam so the
// Pod delivery receipt can still resolve the corpse after the live binding is
// revoked (mirrors the Kurage/Mamuta pattern).
std::map<BTeki*, unsigned> corpses;

// Exactly one match is required so a stale/ambiguous scene fails closed.
bool findOwnerActor(unsigned wantedGenerator, int wantedType, BTeki*& match)
{
    match = nullptr;
    if (!tekiMgr) return false;
    Iterator actors(tekiMgr);
    CI_LOOP(actors) {
        BTeki* actor = static_cast<BTeki*>(*actors);
        if (!actor || !actor->mGenerator) continue;
        if (pc_p2_campaign_token(actor) != wantedGenerator || actor->mTekiType != wantedType) continue;
        if (match) return false;
        match = actor;
    }
    return match != nullptr;
}

// The staged sarai-attack-mouths.txt is a P2_DEMON_MOUTHS_1 text bank; the rest
// pose is its first sampled frame. Derive the two static rest offsets from its
// translation columns (same rule as the lane fixture).
bool readRestOffsets(const char* path, Vector3f& mouthA, Vector3f& mouthB)
{
    std::ifstream in(path);
    std::string magic, digest;
    int count = 0;
    if (!(in >> magic >> digest >> count) || magic != "P2_DEMON_MOUTHS_1" || count < 1) return false;
    int frame = 0;
    float values[24];
    if (!(in >> frame)) return false;
    for (float& x : values) if (!(in >> x)) return false;
    mouthA.set(values[3], values[7], values[11]);
    mouthB.set(values[15], values[19], values[23]);
    return true;
}

// Ordinary-delivery bridge (lane 06 contract, #828): bind source 23 to this
// live actor so GoalItem::suckMe can grant onion:p2:23 exactly once through
// pc_randomizer_p2_corpse_delivered. Mirrors ElecBug (28), Kogane (9) and
// Sokkuri (79). Single-use: consumed on delivery and cleared on
// forget/recycle. Rejected (unbindable id) is logged by the callee, never
// fatal.
void bindDeliverySource(BTeki* actor, unsigned generator)
{
    if (!actor || !generator) return;
    pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), 23, generator);
    std::printf("P2_SARAI_DELIVERY_BIND generator=%u source_id=23\n", generator);
    std::fflush(stdout);
}

std::unique_ptr<P2SaraiHost> buildHost(BTeki* match, unsigned generatorId, bool campaign)
{
    Vector3f restA, restB;
    if (!readRestOffsets("sarai-attack-mouths.txt", restA, restB)) return nullptr;
    auto host = std::make_unique<P2SaraiHost>();
    if (!host->load("courses/pikmin2room/sarai0.mod", restA, restB)) return nullptr;
    if (!host->preloadPoseMeshes("sarai-wait-poses.txt")
        || !host->preloadPoseMeshes("sarai-move-poses.txt")
        || !host->preloadPoseMeshes("sarai-attack-poses.txt")
        || !host->preloadPoseMeshes("sarai-waitact2-poses.txt")
        || !host->preloadPoseMeshes("sarai-waitact1-poses.txt")) return nullptr;
    if (!host->applyPoseFrame(0)) return nullptr;

    std::ifstream events("sarai-retail-events.txt");
    if (!events) return nullptr;
    p2retail::Table table;
    try { table = p2retail::read(events); } catch (...) { return nullptr; }
    p2retail::Motion wait, move, attack, catchFly, fallMeck;
    for (const auto& motion : table.motions) {
        if (motion.name == "wait1.bca") wait = motion;
        else if (motion.name == "move1.bca") move = motion;
        else if (motion.name == "attack1.bca") attack = motion;
        else if (motion.name == "waitact2.bca") catchFly = motion;
        else if (motion.name == "waitact1.bca") fallMeck = motion;
    }
    if (wait.name.empty() || move.name.empty() || attack.name.empty() || catchFly.name.empty() || fallMeck.name.empty())
        return nullptr;
    host->setNaturalMotions(wait, move, attack, catchFly, fallMeck);
    host->setNaturalPoseProfiles("sarai-wait-poses.txt", "sarai-move-poses.txt",
        "sarai-attack-poses.txt", "sarai-waitact2-poses.txt", "sarai-waitact1-poses.txt");

    const Vector3f home = match->getPosition();
    // P2 Sarai rests at mapMgr->getMinY + mNormalFlightHeight (fp01 = 100.0f;
    // Sarai.cpp:194, Sarai.h:89). The ported host draws the mesh at mSRT.t, so
    // add the flight height here or the model clips the floor (user: too low).
    host->setPosition(Vector3f(home.x, home.y + 100.0f, home.z));
    // Static bind: draw the Sarai and keep the anchor at its spawn for combat/
    // transport acceptance fixtures that must not have the captor move it.
    const char* staticMode = std::getenv("PIKMIN_SARAI_STATIC");
    if (staticMode && std::strcmp(staticMode, "1") == 0) {
    if (!host->bindNativeActor(match, generatorId, match->mTekiType)) return nullptr;
        return host;
    }
    // The converted private room's only spawned enemy starts away from the
    // captain and no patrol/scan state is implemented here, so the view cone is
    // widened and the territory/sight radii cover the room (same accommodation
    // as the Demon ordinary host). Approach speed, turn cap and grab range stay
    // at the fixture's natural values. Campaign seed-bridge bindings
    // (bind_dynamic) use the retail-scale geometry instead (#834).
    // Campaign seed-bridge bindings (#834) use the retail-scale general
    // geometry (EnemyParmsBase defaults fp09/fp12/fp13: territory 200, sight
    // 200, view 90) so eight Sarai no longer share one room-wide capture
    // territory over the captain. Speeds stay fixture-tuned in both paths.
    if (campaign) {
        host->enableNatural(30.0f, 3.0f, 20.0f, 12.0f,
            P2SaraiHost::kCampaignTerritoryRadius,
            P2SaraiHost::kCampaignViewAngleDegrees,
            P2SaraiHost::kCampaignSightRadius, home);
        std::printf("P2_SARAI_GEOMETRY mode=campaign territory=%.0f view=%.0f sight=%.0f cooldown=%.0f\n",
                    P2SaraiHost::kCampaignTerritoryRadius,
                    P2SaraiHost::kCampaignViewAngleDegrees,
                    P2SaraiHost::kCampaignSightRadius,
                    P2SaraiHost::kReacquireCooldownSeconds);
        std::fflush(stdout);
    } else {
        host->enableNatural(30.0f, 3.0f, 20.0f, 12.0f, 1000.0f, 360.0f, 1200.0f, home);
    }
    if (!host->naturalEnabled()) return nullptr;
    if (!host->bindNativeActor(match, pc_p2_campaign_token(match), match->mTekiType)) return nullptr;
    return host;
}
} // namespace

void pc_p2_sarai_manager_reset()
{
    // Lane 06 single-use bindings: drop every ordinary-delivery source before
    // clearing the maps. The central pc_randomizer_p2_delivery_reset only
    // closes the ledger; it never clears p2TekiSources, so without this a
    // stage teardown would strand live source-23 entries keyed by destroyed
    // actor addresses for a recycled Teki to inherit (the exact hazard the
    // forget path guards). Covers live bindings and death-observed corpses
    // whose delivery may not have been consumed yet. Idempotent.
    for (auto& entry : s) {
        pc_randomizer_p2_forget_source(static_cast<PelletView*>(entry.first));
        entry.second.host->unbindNativeActor(entry.first);
    }
    for (auto& entry : corpses)
        pc_randomizer_p2_forget_source(static_cast<PelletView*>(entry.first));
    const std::size_t count = s.size();
    s.clear();
    hosts.clear();
    corpses.clear();
    std::printf("P2_SARAI_RESET cleared=%zu\n", count);
    std::fflush(stdout);
}

void pc_p2_sarai_manager_forget(BTeki* actor)
{
    if (!actor) return;
    // Lane 06 single-use binding: drop the ordinary-delivery source so a
    // recycled actor address can never inherit source 23. The central
    // pc_p2_forget_teki seam also clears it; this is idempotent.
    pc_randomizer_p2_forget_source(static_cast<PelletView*>(actor));
    auto it = s.find(actor);
    if (it != s.end()) {
        std::printf("P2_SARAI_FORGET generator=%u phase=cleanup\n", it->second.generator);
        std::fflush(stdout);
        it->second.host->unbindNativeActor(actor);
        s.erase(it);
    }
    corpses.erase(actor);
}

void pc_p2_sarai_manager_setup()
{
    // Seed-bridge campaign path (#439, Otakara pattern): in bridge mode the
    // generated-placement seam claims every actor the randomizer resolved to
    // Sarai source 23. No env var is consulted and several copies may bind;
    // actors whose sidecar is absent are skipped quietly by the dynamic
    // binder. The env/fixture path below is unchanged.
    if (pc_randomizer_p2_bridge()) {
        pc_p2_generated_placement_sweep_sarai();
        return;
    }
    const char* ordinary = std::getenv("PIKMIN_SARAI_ORDINARY");
    if (!ordinary || std::strcmp(ordinary, "1") != 0) return;
    if (!tekiMgr) return;

    const char* gen = std::getenv("PIKMIN_SARAI_GENERATOR");
    const char* type = std::getenv("PIKMIN_SARAI_TYPE");
    const unsigned wantedGenerator = gen && *gen ? unsigned(std::strtoul(gen, nullptr, 10)) : 385875968u;
    const int wantedType = type && *type ? std::atoi(type) : 3;

    BTeki* match = nullptr;
    if (!findOwnerActor(wantedGenerator, wantedType, match)) return;
    // Repeated setup is idempotent: the first bind wins, mirroring the
    // dynamic binder's already-bound refusal. Re-binding would orphan the
    // live host and double-print the delivery marker.
    if (s.count(match)) return;
    auto host = buildHost(match, pc_p2_campaign_token(match), false);
    if (!host) return;
    s[match] = { host.get(), pc_p2_campaign_token(match), match->mTekiType };
    bindDeliverySource(match, pc_p2_campaign_token(match));
    std::printf("P2_SARAI_READY source_id=23 species=Sarai generator=%u type=%d health=%.1f behavior=source\n",
                pc_p2_campaign_token(match), match->mTekiType, match->mHealth);
    std::printf("P2_SARAI_CORPSE_READY generator=%u drop=BDT_Normal ledger=onion receipt=corpse:sarai:%u\n",
                pc_p2_campaign_token(match), pc_p2_campaign_token(match));
    std::fflush(stdout);
    hosts.push_back(std::move(host));
}

bool pc_p2_sarai_manager_bind_dynamic(BTeki* actor, unsigned generatorId, unsigned seedTargetUid)
{
    if (!actor || !generatorId || s.count(actor)) return false;
    auto host = buildHost(actor, generatorId, true);
    if (!host) {
        std::printf("P2_GENERATED_PLACEMENT source_id=23 target=%u bound=0 reason=host\n", seedTargetUid);
        std::fflush(stdout);
        return false;
    }
    s[actor] = { host.get(), generatorId, actor->mTekiType };
    bindDeliverySource(actor, generatorId);
    std::printf("P2_SARAI_READY source_id=23 species=Sarai generator=%u type=%d health=%.1f behavior=source generated=1 seed_target=%u\n",
                generatorId, actor->mTekiType, actor->mHealth, seedTargetUid);
    std::printf("P2_SARAI_CORPSE_READY generator=%u drop=BDT_Normal ledger=onion receipt=corpse:sarai:%u\n",
                generatorId, generatorId);
    std::fflush(stdout);
    hosts.push_back(std::move(host));
    return true;
}

void pc_p2_sarai_manager_update_actor(BTeki* actor)
{
    static int tickCount = 0;
    static bool sawCapture = false;
    static bool sawDeath = false;
    auto it = s.find(actor);
    if (it == s.end()) return;
    auto& binding = it->second;
    if (!binding.host->revalidateNativeActor(actor, binding.generator, binding.type)) {
        corpses[actor] = binding.generator;
        s.erase(it);
        return;
    }
    // The spawned actor is the damage/lifetime anchor. While alive it follows
    // the Sarai host so Pikmin can reach and damage it; the host owns the
    // behaviour and visual. On death the engine corpse path takes over.
    if (actor->isAlive()) actor->mSRT.t = binding.host->position();
    else {
        corpses[actor] = binding.generator;
        if (!sawDeath) {
            sawDeath = true;
            std::printf("P2_SARAI_DEAD source_id=23 generator=%u health=%.1f\n",
                        binding.generator, actor->mHealth);
            std::fflush(stdout);
        }
    }
    binding.host->update();
    ++tickCount;
    if (binding.host->occupied() && !sawCapture) {
        sawCapture = true;
        std::printf("P2_SARAI_CAPTURE source_id=23 generator=%u slot=0 owner_exact=1\n", binding.generator);
        std::fflush(stdout);
    }
    if (tickCount % 90 == 0) {
        const Vector3f p = binding.host->position();
        std::printf("P2_SARAI_TICK tick=%d generator=%u health=%.1f phase=%d state=%d occupied=%d dead=%d pos=(%.1f,%.1f,%.1f)\n",
                    tickCount, binding.generator, actor->mHealth, binding.host->naturalPhase(),
                    binding.host->naturalStateId(), int(binding.host->occupied()), int(binding.host->dead()),
                    p.x, p.y, p.z);
        std::fflush(stdout);
    }
}

bool pc_p2_sarai_manager_draw_actor(BTeki* actor, Graphics& gfx, const Matrix4f&, bool)
{
    auto it = s.find(actor);
    if (it == s.end()) return false;
    auto& binding = it->second;
    if (!binding.host->revalidateNativeActor(actor, binding.generator, binding.type)) {
        s.erase(it);
        return false;
    }
    // Suppress the retail anchor draw; the host owns the Sarai visual. A dead
    // host keeps suppressing the anchor so only the corpse pellet is visible.
    if (!binding.host->dead()) binding.host->refresh(gfx);
    return true;
}

bool pc_p2_sarai_receipt(PelletView* view, unsigned& generator)
{
    if (!view) return false;
    BTeki* t = static_cast<BTeki*>(view);
    auto i = s.find(t);
    if (i != s.end()) { generator = i->second.generator; return true; }
    auto c = corpses.find(t);
    if (c == corpses.end()) return false;
    generator = c->second;
    return true;
}

int pc_p2_sarai_manager_bound_count()
{
    return int(s.size() + corpses.size());
}
