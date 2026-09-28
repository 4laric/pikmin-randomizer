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
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    bool done = false;
};

std::vector<BudActor> actors;
int conversionTotal = 0;

p2pom::Species speciesForColour(const std::string& colour)
{
    if (colour == "blue") return p2pom::Species::BluePom;
    if (colour == "red") return p2pom::Species::RedPom;
    if (colour == "white") return p2pom::Species::WhitePom;
    return p2pom::Species::YellowPom;
}

// Ordinary conversion output: one real PikiHeadItem of the bud's colour, then
// the ordinary pluck (PikiHeadItem::interactBikkuri) turns it into a live Piki.
void birthAndPluck(BudActor& actor)
{
    if (!itemMgr) return;
    PikiHeadItem* sprout = static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));
    if (!sprout) {
        std::printf("P2_CAVE_BUD_SPROUT_RETRY slot=%s colour=%s item_capacity=1\n",
                    actor.slot_id.c_str(), actor.colour.c_str());
        return;
    }
    Vector3f position(actor.x, actor.y + 50.0f, actor.z);
    sprout->init(position);
    sprout->setColor(actor.colour_index);
    InteractBikkuri pluck(nullptr);
    const bool plucked = sprout->interactBikkuri(pluck);
    std::printf("P2_CAVE_BUD_SPROUT slot=%s colour=%s colour_index=%d plucked=%d natural=1\n",
                actor.slot_id.c_str(), actor.colour.c_str(), actor.colour_index, int(plucked));
    if (plucked) {
        ++actor.conversions;
        ++conversionTotal;
    }
}
}  // namespace

bool pc_p2_cave_bud_active() { return !actors.empty(); }

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
    actors.clear();
    conversionTotal = 0;
}

void pc_p2_cave_bud_setup()
{
    actors.clear();
    conversionTotal = 0;
    const P2CaveRoomLayout* layout = pc_p2_cave_rooms_layout();
    if (!layout) return;
    const std::vector<p2cavebud48::BudPlan> plans = p2cavebud48::planBuds(*layout, p2pom::IpTtlBudget);
    for (const p2cavebud48::BudPlan& plan : plans) {
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
    if (!actors.empty()) std::fflush(stdout);
}

void pc_p2_cave_bud_tick()
{
    if (actors.empty() || !pikiMgr) return;
    for (BudActor& actor : actors) {
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
            for (int index = 0; index < shot; ++index) birthAndPluck(actor);
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
