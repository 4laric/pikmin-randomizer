// Lane 48 (#486, cave wave #468): engine glue for the seeded Candypop bud actor.
//
// Reads the live lane-44 P2CaveRoomLayout, plans one actor per ``kind=="bud"``
// node through the engine-free pc_p2_cave_bud.h, and drives the ordinary
// conversion: an airborne Pikmin inside the source slot radius is consumed, the
// budget (lane 23 p2pom::IpTtlBudget = 5) decrements, and the bud births the
// source-count real PikiHeadItem sprouts of the bud's colour. The sprout is
// completed through the ordinary pluck (PikiHeadItem::interactBikkuri), so the
// live squad gains the colour naturally. The generator (41), geometry (45),
// gate physics (50) and item carry (46) are untouched.
#include "pc_p2_cave_bud_actor.h"
#include "pc_p2_cave_bud.h"
#include "pc_p2_cave_rooms_engine.h"
#include "pc_p2_pom_policy.h"
#include "pc_p2_receipt_host.h"
#include "pc_p2_cave.h"
#include "pc_p2_cave_transfer.h"
#include "pc_p2_teki_lifetime.h"
#include "Pom.h"
#include "Generator.h"
#include "Stickers.h"
#include <cmath>
#include <set>
#include <fstream>
#include <filesystem>
#include <sstream>
#include <cstdlib>

#include "Interactions.h"
#include "ItemMgr.h"
#include "MapMgr.h"
#include "Piki.h"
#include "PikiHeadItem.h"
#include "PikiMgr.h"
#include "PikiState.h"

#include <cstdio>
#include <string>
#include <vector>

namespace {
struct BudActor {
    std::string slot_id;
    std::string colour;
    int colour_index = 2;
    int segment = 0;
    int count = p2cavebud48::VanillaConversionCount;
    int used = 0;
    int refunds = 0;
    int conversions = 0;
    int pending = 0;
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    bool done = false;
    unsigned generator = 0;
    Pom* body = nullptr;
    bool retired = false;
};

std::vector<BudActor> actors;
int conversionTotal = 0;
bool bodyReady = false;
bool bodyPrepared = false;
unsigned long bodyScene = 0;
std::string bodyToken;
std::set<std::string> activatedBodyTokens;

[[noreturn]] void invalidBody(const char* reason)
{
    std::fprintf(stderr,"Invalid P2 cave Pom profile: %s\n",reason);
    std::abort();
}

BudActor* boundBody(const Pom* pom)
{
    if (!bodyReady || !pom || bodyScene != pc_p2_scene_generation()) return nullptr;
    const auto* layout = pc_p2_cave_rooms_layout();
    if (!layout || !pc_p2_cave_body_profile_context(layout->seed, layout->cave.c_str(),
            layout->floor, bodyToken.c_str())) return nullptr;
    // A saved address may already belong to the free pool. Prove current
    // manager membership before reading any field through that address.
    if (!bossMgr) return nullptr;
    bool present = false;
    Iterator active(bossMgr);
    CI_LOOP(active) {
        Creature* current = *active;
        if (current == pom) { present = current->mObjType == OBJTYPE_Pom; break; }
    }
    if (!present) return nullptr;
    for (auto& actor : actors)
        if (!actor.retired && actor.body == pom && pom->mGenerator && pom->mGenerator->_70 == actor.generator)
            return &actor;
    return nullptr;
}

void setupBodies(const P2CaveRoomLayout& layout)
{
    std::ifstream in("p2-cave-route-pom.txt");
    std::string magic, key, profile, cave, token, extra;
    unsigned long long seed = 0; int floor = 0, count = 0;
    bool valid = bool(in >> magic >> key >> profile) && magic == "P2_CAVE_ROUTE_POM_1"
        && key == "profile" && profile == "wfg-pw-acquisition-v1";
    valid = valid && bool(in >> key >> seed) && key == "seed";
    valid = valid && bool(in >> key >> cave) && key == "cave";
    valid = valid && bool(in >> key >> floor) && key == "floor";
    valid = valid && bool(in >> key >> token) && key == "token";
    valid = valid && bool(in >> key >> count) && key == "buds" && count == 2;
    if (!valid || cave != "forest_2" || floor != 1 || seed != layout.seed
        || cave != layout.cave || floor != layout.floor || token.size() != 32
        || token.find_first_not_of("0123456789abcdef") != std::string::npos)
        invalidBody("identity/context");
    std::ifstream entryFile("p2-cave-entry.txt");
    std::ostringstream entryText; entryText << entryFile.rdbuf();
    P2CaveEntry entry; std::string entryError;
    if (!entryFile || entryFile.bad() || !p2_cave_parse_entry(entryText.str(),entry,entryError)
        || entry.schema != 2 || entry.floor != floor || entry.token != token)
        invalidBody("full staged ENTRY2 identity");
    if (activatedBodyTokens.count(token)) invalidBody("reused scene token");
    std::set<unsigned> ids;
    int layoutBuds = 0;
    for (const auto& unit : layout.units) if (unit.kind == "bud") ++layoutBuds;
    if (layoutBuds != 2) invalidBody("layout bud count");
    for (int i = 0; i < 2; ++i) {
        BudActor actor; unsigned long long generator;
        if (!(in >> actor.slot_id >> generator >> actor.colour_index >> actor.x >> actor.y >> actor.z >> actor.count)
            || generator > 0xffffffffULL || !ids.insert(static_cast<unsigned>(generator)).second
            || actor.slot_id != "forest_2:f1:bud:" + std::to_string(i)
            || actor.colour_index != 3+i || actor.count != 5
            || !std::isfinite(actor.x) || !std::isfinite(actor.y) || !std::isfinite(actor.z))
            invalidBody("row");
        actor.generator = static_cast<unsigned>(generator);
        actor.colour = i == 0 ? "purple" : "white";
        const auto* unit = p2CaveRoomsFind(layout,actor.slot_id);
        const float ground = mapMgr ? mapMgr->getMinY(actor.x,actor.z,true) : NAN;
        if (!unit || unit->kind != "bud" || actor.x != p2CaveRoomsWorldX(layout,*unit)
            || actor.z != p2CaveRoomsWorldZ(layout,*unit) || !mapMgr
            || !std::isfinite(ground) || std::fabs(actor.y-ground) > 1.0f)
            invalidBody("layout/body position");
        actor.segment = unit->segment_index;
        actors.push_back(actor);
    }
    if ((in >> extra) || !in.eof() || !bossMgr) invalidBody("trailing data or absent manager");
    int bodies = 0;
    Iterator it(bossMgr);
    CI_LOOP(it) {
        Creature* creature = *it;
        if (!creature || creature->mObjType != OBJTYPE_Pom) continue;
        ++bodies;
        auto* pom = static_cast<Pom*>(creature);
        BudActor* match = nullptr;
        for (auto& actor : actors) if (pom->mGenerator && actor.generator == pom->mGenerator->_70) match = &actor;
        if (!match || match->body || !std::isfinite(pom->mSRT.t.x)
            || !std::isfinite(pom->mSRT.t.y) || !std::isfinite(pom->mSRT.t.z)
            || std::fabs(pom->mSRT.t.x-match->x)>1.0f
            || std::fabs(pom->mSRT.t.y-match->y)>1.0f || std::fabs(pom->mSRT.t.z-match->z)>1.0f)
            invalidBody("actual generator/body set");
        match->body = pom;
    }
    if (bodies != 2 || !actors[0].body || !actors[1].body) invalidBody("missing body");
    bodyToken = token;
    bodyPrepared = true;
}

p2pom::Species speciesForColour(const std::string& colour)
{
    if (colour == "blue") return p2pom::Species::BluePom;
    if (colour == "red") return p2pom::Species::RedPom;
    if (colour == "white") return p2pom::Species::WhitePom;
    return p2pom::Species::YellowPom;
}

// Ordinary conversion output: one real PikiHeadItem of the bud's colour, then
// the ordinary pluck (PikiHeadItem::interactBikkuri) turns it into a live Piki.
bool birthAndPluck(BudActor& actor)
{
    if (!itemMgr) return false;
    PikiHeadItem* sprout = static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));
    if (!sprout) {
        std::printf("P2_CAVE_BUD_SPROUT_RETRY slot=%s colour=%s item_capacity=1\n",
                    actor.slot_id.c_str(), actor.colour.c_str());
        return false;
    }
    Vector3f position(actor.x, actor.y + 50.0f, actor.z);
    sprout->init(position);
    sprout->setColor(actor.colour_index);
    sprout->startAI(0);
    InteractBikkuri pluck(nullptr);
    const bool plucked = sprout->interactBikkuri(pluck);
    std::printf("P2_CAVE_BUD_SPROUT slot=%s colour=%s colour_index=%d plucked=%d natural=1\n",
                actor.slot_id.c_str(), actor.colour.c_str(), actor.colour_index, int(plucked));
    if (plucked) {
        ++actor.conversions;
        ++conversionTotal;
    }
    // A failed immediate pluck leaves a real sprout for ordinary player plucking.
    // The output has been born and must not be retried/duplicated.
    return true;
}
}  // namespace

bool pc_p2_cave_bud_active() { return !actors.empty(); }

bool pc_p2_cave_bud_body_profile()
{
    std::error_code error;
    const bool exists = std::filesystem::exists("p2-cave-route-pom.txt",error);
    if (error) invalidBody("unreadable profile path");
    return exists || bodyReady || bodyPrepared;
}

int pc_p2_cave_bud_body_species(const Pom* pom)
{
    const auto* actor = boundBody(pom);
    return actor ? actor->colour_index : -1;
}

int pc_p2_cave_bud_body_remaining(const Pom* pom)
{
    const auto* actor = boundBody(pom);
    return actor ? actor->count-actor->used : 0;
}

void pc_p2_cave_bud_body_output(const Pom* pom, bool sameSpecies)
{
    auto* actor = boundBody(pom);
    if (!actor || actor->used >= actor->count) invalidBody("unauthorized output");
    if (sameSpecies) ++actor->refunds; else ++actor->used;
    ++actor->conversions; ++conversionTotal;
    actor->done = actor->used == actor->count;
    std::printf("P2_CAVE_POM_OUTPUT slot=%s species=%d refund=%d used=%d budget=5 ordinary_pluck_pending=1\n",
        actor->slot_id.c_str(),actor->colour_index,int(sameSpecies),actor->used);
}

void pc_p2_cave_bud_body_retire(Pom* pom)
{
    auto* actor = boundBody(pom);
    if (!actor || actor->count != 5 || actor->used != 5 || !actor->done || actor->pending)
        invalidBody("retirement before exhausted budget");
    if (pom->isHolding()) invalidBody("retirement with held input");
    Stickers stickers(pom); Iterator it(&stickers);
    CI_LOOP(it) {
        Creature* c = *it;
        if (c && c->isAlive() && c->isPiki()) invalidBody("retirement with attached input");
    }
    // Do not keep a free-pool address. Sprouts remain independently pending
    // until the player plucks them through the ordinary engine interaction.
    actor->body = nullptr;
    actor->retired = true;
    std::printf("P2_CAVE_POM_RETIRED slot=%s used=5 budget=5 scene=%lu\n",
        actor->slot_id.c_str(),bodyScene);
}

int pc_p2_cave_bud_count() { return static_cast<int>(actors.size()); }

int pc_p2_cave_bud_conversions() { return conversionTotal; }

bool pc_p2_cave_bud_position(const char* colour, Vector3f& out)
{
    if (!colour) return false;
    for (const BudActor& actor : actors) {
        if (actor.colour == colour) {
            out = Vector3f(actor.x, actor.y, actor.z);
            return true;
        }
    }
    return false;
}

void pc_p2_cave_bud_shutdown()
{
    bodyReady = false;
    bodyPrepared = false;
    bodyToken.clear();
    actors.clear();
    conversionTotal = 0;
}

void pc_p2_cave_bud_setup()
{
    bodyReady = false;
    bodyPrepared = false;
    actors.clear();
    conversionTotal = 0;
    const P2CaveRoomLayout* layout = pc_p2_cave_rooms_layout();
    if (!layout) {
        if (pc_p2_cave_bud_body_profile()) invalidBody("missing layout");
        return;
    }
    const bool bodyProfile = pc_p2_cave_bud_body_profile();
    if (bodyProfile) setupBodies(*layout);
    const std::vector<p2cavebud48::BudPlan> plans = p2cavebud48::planBuds(*layout, p2pom::IpTtlBudget);
    for (const p2cavebud48::BudPlan& plan : plans) {
        if (bodyProfile) break;
        BudActor actor;
        actor.slot_id = plan.slot_id;
        actor.colour = plan.colour;
        actor.colour_index = plan.colour_index;
        actor.segment = plan.segment;
        actor.count = plan.count;
        actor.x = plan.x;
        actor.z = plan.z;
        actor.y = mapMgr ? mapMgr->getMinY(actor.x, actor.z, true) : 0.0f;
        actors.push_back(actor);
        std::printf("P2_CAVE_BUD_ACTOR slot=%s colour=%s segment=%d count=%d x=%.3f y=%.3f z=%.3f spawned=1\n",
                    actor.slot_id.c_str(), actor.colour.c_str(), actor.segment, actor.count,
                    actor.x, actor.y, actor.z);
    }
    std::error_code readError;
    const bool present=std::filesystem::exists("p2-cave-bud-entry.txt",readError);
    std::ifstream saved("p2-cave-bud-entry.txt");
    if (readError || (present && !saved)) {
        std::fputs("Cannot read P2 cave bud checkpoint\n",stderr); std::abort();
    }
    if (saved) {
        std::string magic, cave, id, extra; unsigned long long seed; int floor, count;
        bool valid=bool(saved>>magic>>seed>>cave>>floor>>count)
            && magic=="P2_CAVE_BUD_STATE_1" && seed==layout->seed
            && cave==layout->cave && floor==layout->floor && count==int(actors.size());
        for (BudActor& actor : actors) {
            int used=-1;
            if (!(saved>>id>>used) || id!=actor.slot_id || used<0 || used>actor.count) valid=false;
            actor.used=used; actor.done=used==actor.count;
        }
        if ((saved>>extra) || !saved.eof()) valid=false;
        if (!valid) { std::fputs("Invalid P2 cave bud checkpoint\n",stderr); std::abort(); }
        std::printf("P2_CAVE_BUD_RESTORE actors=%zu\n",actors.size());
    }
    if (!actors.empty()) std::fflush(stdout);
}

void pc_p2_cave_bud_tick()
{
    if (pc_p2_cave_bud_body_profile()) {
        if (!bodyReady) {
            const auto* layout = pc_p2_cave_rooms_layout();
            if (!bodyPrepared || !layout || !pc_p2_cave_body_profile_context(layout->seed,
                layout->cave,layout->floor,bodyToken)) invalidBody("unready runtime context");
            if (activatedBodyTokens.count(bodyToken)) invalidBody("reused runtime token");
            if (!bossMgr) invalidBody("missing runtime body manager");
            int currentBodies = 0;
            Iterator bodyIt(bossMgr);
            CI_LOOP(bodyIt) {
                Creature* c = *bodyIt;
                if (!c || c->mObjType != OBJTYPE_Pom) continue;
                ++currentBodies;
                bool found = false;
                for (const auto& actor : actors) if (actor.body == c && c->mGenerator
                    && c->mGenerator->_70 == actor.generator) found = true;
                if (!found) invalidBody("changed runtime body inventory");
            }
            if (currentBodies != 2) invalidBody("missing runtime bodies");
            bodyScene = pc_p2_scene_generation();
            activatedBodyTokens.insert(bodyToken);
            bodyReady = true;
            // Recheck actual identities before arming the native AI.
            for (const auto& actor : actors) if (!boundBody(actor.body)) invalidBody("stale body");
            std::printf("P2_CAVE_POM_PROFILE cave=forest_2 floor=1 bodies=2 scene=%lu ordinary_pluck=1\n",bodyScene);
        }
        return; // Real Pom AI owns capture/output; no proxy or auto-pluck.
    }
    if (actors.empty() || !pikiMgr) return;
    for (BudActor& actor : actors) {
        while (actor.pending > 0 && birthAndPluck(actor)) --actor.pending;
        if (actor.done) continue;
        const p2pom::Species species = speciesForColour(actor.colour);
        // Collect thrown/airborne Pikmin inside the ordinary slot radius, then
        // consume them so the pikiMgr walk is never invalidated mid-iteration.
        std::vector<Piki*> candidates;
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* piki = static_cast<Piki*>(*it);
            if (!piki || !piki->isAlive() || piki->getState() != PIKISTATE_Flying) continue;
            const float dx = piki->mSRT.t.x - actor.x;
            const float dz = piki->mSRT.t.z - actor.z;
            if (dx * dx + dz * dz <= p2pom::SlotRadius * p2pom::SlotRadius) candidates.push_back(piki);
        }
        int swallowed = 0;
        for (Piki* piki : candidates) {
            if (actor.used >= actor.count) break;
            const int thrownColour = int(piki->mColor);
            if (p2pom::refund(species, thrownColour)) {
                ++actor.refunds;
                std::printf("P2_CAVE_BUD_REFUND slot=%s colour=%s thrown_colour=%d used=%d budget=%d slot_refunded=1\n",
                            actor.slot_id.c_str(), actor.colour.c_str(), thrownColour, actor.used, actor.count);
                // Same-colour refund must preserve the thrown actor.
                continue;
            } else {
                ++actor.used;
                ++swallowed;
                std::printf("P2_CAVE_BUD_ACCEPT slot=%s colour=%s thrown_colour=%d used=%d budget=%d\n",
                            actor.slot_id.c_str(), actor.colour.c_str(), thrownColour, actor.used, actor.count);
            }
            piki->setEraseKill();
            piki->kill(false);
        }
        if (swallowed > 0) {
            const int shot = p2pom::shotCount(species, swallowed);
            std::printf("P2_CAVE_BUD_CLOSE slot=%s colour=%s outcome=shot used=%d budget=%d swallowed=%d\n",
                        actor.slot_id.c_str(), actor.colour.c_str(), actor.used, actor.count, swallowed);
            actor.pending += shot;
            while (actor.pending > 0 && birthAndPluck(actor)) --actor.pending;
            if (actor.used >= actor.count) actor.done = true;
        }
        if (!actor.done && actor.conversions > 0 && actor.used >= actor.count) {
            std::printf("P2_CAVE_BUD_DONE slot=%s colour=%s used=%d refunds=%d conversions=%d\n",
                        actor.slot_id.c_str(), actor.colour.c_str(), actor.used, actor.refunds, actor.conversions);
            actor.done = true;
        }
    }
    std::fflush(stdout);
}

bool pc_p2_cave_bud_pending()
{
    if (pc_p2_cave_bud_body_profile()) {
        if (!bodyReady || bodyScene != pc_p2_scene_generation()) return true;
        const auto* layout = pc_p2_cave_rooms_layout();
        if (!layout || !pc_p2_cave_body_profile_context(layout->seed,layout->cave,
                layout->floor,bodyToken) || !bossMgr) return true;
        for (const auto& actor : actors) {
            if (actor.retired) {
                if (actor.body || actor.count != 5 || actor.used != 5 || !actor.done || actor.pending) return true;
                continue;
            }
            if (!boundBody(actor.body)) return true;
        }
        // Inspect live manager members, not retained addresses; unexpected
        // recycled/new Pom bodies cannot inherit a retired budget's authority.
        Iterator active(bossMgr);
        CI_LOOP(active) {
            Creature* current = *active;
            if (!current || current->mObjType != OBJTYPE_Pom) continue;
            auto* pom = static_cast<Pom*>(current);
            if (!boundBody(pom) || pom->isHolding()) return true;
            Stickers stickers(pom); Iterator it(&stickers);
            CI_LOOP(it) { Creature* c = *it; if (c && c->isAlive() && c->isPiki()) return true; }
        }
        if (!itemMgr) return true;
        Iterator it(itemMgr);
        CI_LOOP(it) { Creature* c = *it; if (c && c->mObjType == OBJTYPE_Pikihead && c->isAlive()) return true; }
    }
    for (const BudActor& actor : actors) if (actor.pending) return true;
    return false;
}

bool pc_p2_cave_bud_save(const char* path)
{
    const P2CaveRoomLayout* layout=pc_p2_cave_rooms_layout();
    if (!layout || actors.empty()) return true;
    if (pc_p2_cave_bud_pending()) return false;
    std::ostringstream out;
    out << "P2_CAVE_BUD_STATE_1\n" << layout->seed << ' ' << layout->cave << ' '
        << layout->floor << ' ' << actors.size() << '\n';
    for (const BudActor& actor : actors) out << actor.slot_id << ' ' << actor.used << '\n';
    return pc_p2_receipt_host_atomic_write(path,out.str().c_str());
}
