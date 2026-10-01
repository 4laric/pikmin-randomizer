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

const P2SaraiSpecies kSaraiSpecies{23, "SARAI", "Sarai", "sarai", false};
const P2SaraiSpecies kDemonSpecies{32, "DEMON", "Demon", "demon", true};

namespace {
// One-shot markers are per binding (#215): the old process-static flags
// reported only the first of several Sarai.
struct Binding {
    P2SaraiHost* host;
    unsigned generator;
    int type;
    const P2SaraiSpecies* species = &kSaraiSpecies;
    int ticks = 0;
    bool sawCapture = false;
    bool sawDeath = false;
    bool escaped = false;
    float lastHealth = -1.0f;
};
std::map<BTeki*, Binding> s;
std::vector<std::unique_ptr<P2SaraiHost>> hosts;
// Naturally dead Sarai anchors: kept until the central forget/reset seam so the
// Pod delivery receipt can still resolve the corpse after the live binding is
// revoked (mirrors the Kurage/Mamuta pattern). The species is kept with the
// corpse so a Demon anchor that lands here (finalised, or failing revalidation
// before finalisation) can never resolve as a private-room corpse:sarai
// receipt (#215 review).
struct Corpse {
    unsigned generator;
    const P2SaraiSpecies* species;
};
std::map<BTeki*, Corpse> corpses;

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
void bindDeliverySource(BTeki* actor, unsigned generator, const P2SaraiSpecies& sp = kSaraiSpecies)
{
    if (!actor || !generator) return;
    pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), sp.sourceId, generator);
    std::printf("P2_%s_DELIVERY_BIND generator=%u source_id=%u\n", sp.marker, generator, sp.sourceId);
    std::fflush(stdout);
}

// Demon (32) profile host (#215): own staged model, all twelve retail clips,
// the retail event table and the retail parms. Fails closed (nullptr) when any
// staged file is missing or malformed; never falls back to Sarai assets.
std::unique_ptr<P2SaraiHost> buildDemonHost(BTeki* match, unsigned generatorId)
{
    Vector3f restA, restB;
    if (!readRestOffsets("demon-attack-mouths.txt", restA, restB)) return nullptr;
    std::ifstream parmsIn("demon-parms.txt");
    p2demon::Parms parms;
    if (!parmsIn || !p2demon::loadParms(parmsIn, parms)) {
        std::printf("P2_DEMON_PARMS_INVALID generator=%u\n", generatorId);
        std::fflush(stdout);
        return nullptr;
    }
    std::ifstream events("demon-retail-events.txt");
    if (!events) return nullptr;
    p2retail::Table table;
    try { table = p2retail::read(events); } catch (...) { return nullptr; }
    auto host = std::make_unique<P2SaraiHost>();
    host->setSpecies(kDemonSpecies);
    if (!host->load("courses/pikmin2room/demon0.mod", restA, restB)) return nullptr;
    const Vector3f home = match->getPosition();
    // Sarai::onInit: the Demon starts at its spawn and climbs to fp01 through
    // setHeightVelocity; start it at flight height so the first frames do not
    // clip the floor.
    host->setPosition(Vector3f(home.x, home.y + parms.proper.normalFlightHeight, home.z));
    if (!host->enableDemon(parms, table, "demon", home, generatorId ^ 0x9e3779b9u)) return nullptr;
    if (!host->bindNativeActor(match, generatorId, match->mTekiType)) return nullptr;
    host->demonAnchorInit();
    std::printf("P2_DEMON_PARMS source_id=32 retail=1 life=%.1f territory=%.1f home=%.1f sight=%.1f view=%.1f "
                "turn=%.2f max_turn=%.1f attack_damage=%.1f fp01=%.1f fp02=%.1f fp03=%.1f fp04=%.1f fp05=%.1f "
                "fp11=%.2f fp12=%.2f fp21=%.2f fp22=%.2f fp23=%.2f fp41=%.1f\n",
                parms.general.life, parms.general.territoryRadius, parms.general.homeRadius,
                parms.general.sightRadius, parms.general.viewAngle, parms.general.turnSpeed,
                parms.general.maxTurnAngle, parms.general.attackDamage, parms.proper.normalFlightHeight,
                parms.proper.grabFlightHeight, parms.proper.stateTransitionHeight,
                parms.proper.normalMovementSpeed, parms.proper.grabMovementSpeed, parms.proper.climbingFactor0,
                parms.proper.climbingFactor5, parms.proper.payoffProbability1, parms.proper.payoffProbability5,
                parms.proper.strugglingTime, parms.proper.fallMeckSpeed);
    std::printf("P2_DEMON_BANK source_id=32 clips=12 carcass=type5 model=courses/pikmin2room/demon0.mod draw=p2_model\n");
    std::fflush(stdout);
    return host;
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

namespace {
bool bindSpecies(BTeki* actor, unsigned generatorId, unsigned seedTargetUid, const P2SaraiSpecies& sp)
{
    if (!actor || !generatorId || s.count(actor)) return false;
    auto host = sp.demon ? buildDemonHost(actor, generatorId) : buildHost(actor, generatorId, true);
    if (!host) {
        std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u bound=0 reason=host\n", sp.sourceId, seedTargetUid);
        // #215 review: a seed slot assigned to the Demon whose staged demon-*
        // files are missing stays a plain P1 anchor and can never deliver its
        // check. Say so loudly instead of leaving only the generic marker.
        if (sp.demon)
            std::printf("P2_DEMON_HOST_UNAVAILABLE source_id=32 generator=%u target=%u "
                        "reason=staging slot_check_unreachable=1\n", generatorId, seedTargetUid);
        std::fflush(stdout);
        return false;
    }
    Binding binding{host.get(), generatorId, actor->mTekiType};
    binding.species = &sp;
    binding.lastHealth = actor->mHealth;
    s[actor] = binding;
    bindDeliverySource(actor, generatorId, sp);
    std::printf("P2_%s_READY source_id=%u species=%s generator=%u type=%d health=%.1f behavior=source generated=1 seed_target=%u\n",
                sp.marker, sp.sourceId, sp.species, generatorId, actor->mTekiType, actor->mHealth, seedTargetUid);
    if (sp.demon)
        std::printf("P2_DEMON_OWN_BIND source_id=32 generator=%u anchor_type=%d anchor_ai=suppressed "
                    "host=P2SaraiHost profile=Demon proxy=0\n", generatorId, actor->mTekiType);
    else
        std::printf("P2_SARAI_CORPSE_READY generator=%u drop=BDT_Normal ledger=onion receipt=corpse:sarai:%u\n",
                    generatorId, generatorId);
    std::fflush(stdout);
    hosts.push_back(std::move(host));
    return true;
}
} // namespace

bool pc_p2_sarai_manager_bind_dynamic(BTeki* actor, unsigned generatorId, unsigned seedTargetUid)
{
    return bindSpecies(actor, generatorId, seedTargetUid, kSaraiSpecies);
}

bool pc_p2_sarai_manager_bind_demon(BTeki* actor, unsigned generatorId, unsigned seedTargetUid)
{
    return bindSpecies(actor, generatorId, seedTargetUid, kDemonSpecies);
}

P2SaraiHost* pc_p2_sarai_manager_demon_host(const BTeki* actor)
{
    auto it = s.find(const_cast<BTeki*>(actor));
    if (it == s.end() || !it->second.species->demon) return nullptr;
    return it->second.host;
}

void pc_p2_sarai_manager_update_actor(BTeki* actor)
{
    auto it = s.find(actor);
    if (it == s.end()) return;
    auto& binding = it->second;
    // Finalised Demon corpse: nothing left to drive (see draw_actor).
    if (binding.species->demon && binding.escaped) return;
    if (!binding.host->revalidateNativeActor(actor, binding.generator, binding.type)) {
        corpses[actor] = {binding.generator, binding.species};
        s.erase(it);
        return;
    }
    if (binding.species->demon) {
        // Demon (#215): the anchor's P1 AI is suppressed (pc_p2_sarai_suppress_ai),
        // so its queued Pikmin damage is drained here and death is finalised
        // only after the retail Fall/Dead sequence reaches Dead KEYEVENT_END.
        if (!binding.escaped) {
            binding.host->demonAnchorDrain();
            if (actor->mHealth < binding.lastHealth - 0.001f) {
                std::printf("P2_DEMON_DAMAGE source_id=32 generator=%u health=%.1f delta=%.1f\n",
                            binding.generator, actor->mHealth, binding.lastHealth - actor->mHealth);
                std::fflush(stdout);
            }
            binding.lastHealth = actor->mHealth;
            binding.host->update();
            binding.host->demonAnchorFollow();
            if (actor->mHealth <= 0.0f && !binding.sawDeath) {
                binding.sawDeath = true;
                std::printf("P2_DEMON_DEAD source_id=32 generator=%u health=%.1f state=%d\n",
                            binding.generator, actor->mHealth, binding.host->naturalStateId());
                std::fflush(stdout);
            }
            if (binding.host->demonKillRequested()) {
                binding.escaped = true;
                corpses[actor] = {binding.generator, binding.species};
                binding.host->demonAnchorFinalize();
            }
        }
        return;
    }
    // The spawned actor is the damage/lifetime anchor. While alive it follows
    // the Sarai host so Pikmin can reach and damage it; the host owns the
    // behaviour and visual. On death the engine corpse path takes over.
    if (actor->isAlive()) actor->mSRT.t = binding.host->position();
    else {
        corpses[actor] = {binding.generator, binding.species};
        if (!binding.sawDeath) {
            binding.sawDeath = true;
            std::printf("P2_SARAI_DEAD source_id=23 generator=%u health=%.1f\n",
                        binding.generator, actor->mHealth);
            std::fflush(stdout);
        }
    }
    binding.host->update();
    ++binding.ticks;
    if (binding.host->occupied() && !binding.sawCapture) {
        binding.sawCapture = true;
        std::printf("P2_SARAI_CAPTURE source_id=23 generator=%u slot=0 owner_exact=1\n", binding.generator);
        std::fflush(stdout);
    }
    if (binding.ticks % 90 == 0) {
        const Vector3f p = binding.host->position();
        std::printf("P2_SARAI_TICK tick=%d generator=%u health=%.1f phase=%d state=%d occupied=%d dead=%d pos=(%.1f,%.1f,%.1f)\n",
                    binding.ticks, binding.generator, actor->mHealth, binding.host->naturalPhase(),
                    binding.host->naturalStateId(), int(binding.host->occupied()), int(binding.host->dead()),
                    p.x, p.y, p.z);
        std::fflush(stdout);
    }
}

bool pc_p2_sarai_manager_draw_actor(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse)
{
    auto it = s.find(actor);
    if (it == s.end()) return false;
    auto& binding = it->second;
    // A finalised Demon corpse has detached its generator (revalidation would
    // fail); the binding stays until the central forget seam, so the carried
    // pellet keeps the Demon carcass visual instead of the P1 vehicle's.
    if (binding.species->demon && binding.escaped) {
        if (corpse) binding.host->demonDrawCarcass(gfx, matrix);
        return true;
    }
    if (!binding.host->revalidateNativeActor(actor, binding.generator, binding.type)) {
        s.erase(it);
        return false;
    }
    if (binding.species->demon) {
        // Demon: the live host draws its own mesh; after the anchor becomes the
        // carried corpse, the host draws the retail carcass pose (type5) at it.
        binding.host->refresh(gfx);
        return true;
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
    // Private-room corpse:sarai receipt is Sarai-only; the Demon delivers
    // through the campaign Onion ledger (onion:p2:32:<token>).
    if (i != s.end() && i->second.species->demon) return false;
    if (i != s.end()) { generator = i->second.generator; return true; }
    auto c = corpses.find(t);
    if (c == corpses.end() || c->second.species->demon) return false;
    generator = c->second.generator;
    return true;
}

int pc_p2_sarai_manager_bound_count()
{
    return int(s.size() + corpses.size());
}
