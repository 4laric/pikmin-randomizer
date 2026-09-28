// Sarai (Swooping Snitchbug, source 23) campaign capture/teardown proof.
//
// Brief: rd-p2-sarai-campaign (#457). The integrator addendum established that
// Sarai 23 already works in campaign mode; this lane's job is to PROVE the
// capture path against campaign-shaped hosts rather than rebuild it.
//
// Engine-free: the real pc_p2_sarai_capture_bridge.cpp is compiled here against
// stub engine headers that shadow the real Piki/Creature/CollPart/Interaction
// types (include dir BEFORE pc_port). The bridge owns the shipped exactly-once
// mouth-stick/detach logic, so driving it here observes the real behaviour, not
// a reimplementation.
//
// Campaign-shaped hosts: the owner is the P2 source-23 actor resolved through
// pc_p2_campaign_policy.h / pc_p2_campaign_actor.h (the campaign vehicle and
// token), never an arena fixture. Captain safety (#632) does not apply to this
// engine-free, captain-free fixture: it never starts a runtime, never touches a
// live Navi, and drives no CAPTAIN_DOWN-observable tick.
//
// Coverage:
//   1. campaign host shape for source 23 (pc_p2_campaign_policy.h vehicle);
//   2. capture admission against a live campaign captain/Pikmin owner;
//   3. release/drop/flick exactly-once with no stranded Pikmin;
//   4. teardown (owner_lost, scene_exit, forget) leaves no mouth link or claim;
//   5. the binding token is the campaign id, not an arena fixture id.
#include "Piki.h"
#include "Collision.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_campaign_policy.h"
#include "pc_p2_sarai_capture.h"
#include "pc_p2_sarai_capture_bridge.h"

#include <cstdio>
#include <cstdlib>
#include <map>
#include <vector>

using namespace p2sarai;

// --- Engine doubles (campaign owner identity) ------------------------------
// tekiMgr / Generator / BTeki come from tools/p2_sarai_campaign_stubs via the
// second BEFORE include dir; the randomizer bridge doubles below mirror the
// real contract used by pc_p2_campaign_actor.h.
TekiMgr manager;
TekiMgr* tekiMgr = &manager;

namespace {
int gChecks = 0;
bool gBridge = false;
std::map<unsigned long, unsigned> gSourceForUid;
std::map<const void*, unsigned> gUidForGenerator;

struct CampaignHost : Creature {
    Vector3f position;
};

void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_sarai_campaign_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

void initMouth(CollPart& mouth, const Vector3f& centre, unsigned partType = PART_BoundSphere)
{
    mouth.mPartType = partType;
    mouth.mRadius = kMouthRadius;
    mouth.mCentre = centre;
}
} // namespace

// --- Randomizer bridge doubles --------------------------------------------
bool pc_randomizer_p2_bridge() { return gBridge; }
unsigned pc_randomizer_p2_source_for_id(unsigned long id)
{
    auto it = gSourceForUid.find(id);
    return it == gSourceForUid.end() ? 0 : it->second;
}
unsigned pc_randomizer_generator_id(const void* generator)
{
    auto it = gUidForGenerator.find(generator);
    return it == gUidForGenerator.end() ? 0 : it->second;
}
void pc_randomizer_set_generator_id(const void*, unsigned) {}

int main()
{
    // --- 1. Campaign host shape for source 23 -------------------------------
    {
        for (int original = 0; original < 34; ++original) {
            require(p2campaign::hostType(23, original, false) == 3,
                    "source 23 maps to the campaign ordinary host vehicle (TEKI_Chappy)");
            require(p2campaign::hostType(23, original, true) == original,
                    "protected spawn keeps the original host for source 23");
        }
    }

    // --- 5. Campaign binding token, not an arena fixture id ----------------
    CampaignHost host;
    CollPart mouthA, mouthB;
    initMouth(mouthA, Vector3f(0.0f, 100.0f, 0.0f));
    initMouth(mouthB, Vector3f(10.0f, 100.0f, 0.0f));

    unsigned campaignToken = 0;
    {
        gBridge = true;
        Generator* gen = new Generator();
        const unsigned uid = 5465461u; // a committed source-23 placement from pc_p2_campaign_placements.h
        gen->_70 = 7001u;              // retail on-file id, deliberately different from the uid
        BTeki* actor = new BTeki();
        actor->mGenerator = gen;
        gUidForGenerator[gen] = uid;
        gSourceForUid[uid] = 23;
        manager.actors.push_back(actor);

        require(pc_p2_campaign_source(actor) == 23, "campaign source resolves from the seed uid");
        require(pc_p2_campaign_token(actor) == uid, "campaign token is the seed uid, not Generator::_70");
        const auto ids = pc_p2_campaign_ids(23);
        require(ids.count(uid) == 1 && ids.size() == 1, "source-23 campaign id set carries the seed uid");
        campaignToken = pc_p2_campaign_token(actor);

        delete actor;
        delete gen;
        manager.actors.clear();
    }
    require(campaignToken != 0, "campaign token available for the capture owner");

    // --- 2. Capture admission against a campaign-shaped owner ---------------
    {
        gBridge = true;
        pc_p2_sarai_forget();
        Piki pikiA, pikiB, pikiC;

        require(pc_p2_sarai_piki_capture(&pikiA, &host, &mouthA, campaignToken, 0),
                "campaign owner captures the first Pikmin into mouth slot 0");
        require(pc_p2_sarai_piki_bound(&pikiA), "first Pikmin is mouth-bound");
        require(pc_p2_sarai_piki_owned_by(&pikiA, &host), "binding owner is the campaign host");
        require(pc_p2_sarai_piki_slot(&pikiA) == 0, "first Pikmin occupies slot 0");
        require(pikiA.isStickToMouth() && pikiA.getStickObject() == &host && pikiA.getStickPart() == &mouthA,
                "engine mouth link is authored against the campaign mouth part");
        require(pc_p2_sarai_carried_count(&host) == 1, "host carries exactly one Pikmin");

        require(pc_p2_sarai_piki_capture(&pikiB, &host, &mouthB, campaignToken, 1),
                "campaign owner captures a second Pikmin into mouth slot 1");
        require(pc_p2_sarai_piki_slot(&pikiB) == 1, "second Pikmin occupies slot 1");
        require(pc_p2_sarai_carried_count(&host) == 2, "host carries exactly two Pikmin");

        // Duplicate, dead, already-stuck and invalid-slot captures are refused
        // without disturbing the existing bindings.
        require(!pc_p2_sarai_piki_capture(&pikiA, &host, &mouthA, campaignToken, 0),
                "a Pikmin already mouth-bound is refused");
        require(!pc_p2_sarai_piki_capture(&pikiC, &host, &mouthA, 0u, 0),
                "a zero owner generation is refused");
        require(!pc_p2_sarai_piki_capture(&pikiC, &host, &mouthA, campaignToken, kMouthSlots),
                "a slot beyond the two mouth slots is refused");
        require(!pc_p2_sarai_piki_capture(nullptr, &host, &mouthA, campaignToken, 0),
                "null Pikmin is refused");
        require(!pc_p2_sarai_piki_capture(&pikiC, nullptr, &mouthA, campaignToken, 0),
                "null owner is refused");
        require(!pc_p2_sarai_piki_capture(&pikiC, &host, nullptr, campaignToken, 0),
                "null mouth is refused");
        pikiC.alive = false;
        require(!pc_p2_sarai_piki_capture(&pikiC, &host, &mouthA, campaignToken, 0),
                "a dead Pikmin is refused");
        pikiC.alive = true;
        pikiC.startStickMouth(&host, &mouthA); // already stuck to a mouth elsewhere
        require(!pc_p2_sarai_piki_capture(&pikiC, &host, &mouthA, campaignToken, 0),
                "a Pikmin already stuck elsewhere is refused");
        pikiC.endStickMouth();
        CollPart nonMouth;
        initMouth(nonMouth, Vector3f(0, 0, 0), PART_Cylinder);
        require(!pc_p2_sarai_piki_capture(&pikiC, &host, &nonMouth, campaignToken, 0),
                "a non-bouncy/non-sphere mouth part is refused");
        require(pc_p2_sarai_carried_count(&host) == 2, "refusals never disturb the two live bindings");
    }

    // --- 3. Drop (FallMeck) is exactly-once and strands nothing -------------
    {
        gBridge = true;
        pc_p2_sarai_forget(); // release the section-2 stack bindings before reuse
        Piki pikiA, pikiB;
        CampaignHost other;
        require(pc_p2_sarai_piki_capture(&pikiA, &host, &mouthA, campaignToken, 0), "re-capture A");
        require(pc_p2_sarai_piki_capture(&pikiB, &host, &mouthB, campaignToken, 1), "re-capture B");

        require(pc_p2_sarai_drop_owned(&other, 10.0f, 200.0f) == 0, "a different owner releases nothing");
        require(pc_p2_sarai_carried_count(&host) == 2, "foreign drop leaves the campaign bindings live");

        const unsigned released = pc_p2_sarai_drop_owned(&host, 10.0f, 200.0f);
        require(released == 2, "attacking drop releases both captives");
        require(pc_p2_sarai_carried_count(&host) == 0, "no Pikmin stranded after the drop");
        require(!pc_p2_sarai_piki_bound(&pikiA) && !pc_p2_sarai_piki_bound(&pikiB),
                "dropped Pikmin are no longer bound");
        require(!pikiA.isStickToMouth() && !pikiB.isStickToMouth(), "dropped Pikmin are off the mouth");
        require(pikiA.stimulateCalls == 1 && pikiB.stimulateCalls == 1, "each captive received exactly one flick");
        require(pikiA.lastDamage == fallMeckDamage(10.0f) && pikiA.lastKnockback == kFlickKnockback,
                "FallMeck delivered the source attack damage through InteractFlick");
        require(pikiA.mVelocity.y == fallMeckReleaseVelocity(200.0f) && pikiA.mVelocity.y == -200.0f,
                "FallMeck applied the source downward release velocity");
        require(pc_p2_sarai_drop_owned(&host, 10.0f, 200.0f) == 0, "a second drop is inert (exactly-once)");
    }

    // --- 3b. Escape (Flick) is harmless and exactly-once --------------------
    {
        gBridge = true;
        pc_p2_sarai_forget();
        Piki piki;
        require(pc_p2_sarai_piki_capture(&piki, &host, &mouthA, campaignToken, 0), "re-capture for flick");
        const unsigned detached = pc_p2_sarai_flick_owned(&host);
        require(detached == 1, "escape flick detaches the captive");
        require(pc_p2_sarai_carried_count(&host) == 0, "no Pikmin stranded after flick");
        require(!piki.isStickToMouth(), "flicked Pikmin is off the mouth");
        require(piki.stimulateCalls == 1 && piki.lastDamage == kFlickDamage, "escape flick is harmless (0 damage)");
        require(pc_p2_sarai_flick_owned(&host) == 0, "a second flick is inert");
    }

    // --- 3c. A dead captive is detached without a damaging flick ------------
    {
        gBridge = true;
        pc_p2_sarai_forget();
        Piki piki;
        require(pc_p2_sarai_piki_capture(&piki, &host, &mouthA, campaignToken, 0), "re-capture dead-path");
        piki.alive = false;
        require(pc_p2_sarai_drop_owned(&host, 10.0f, 200.0f) == 0, "dead captive is not a damaging release");
        require(pc_p2_sarai_carried_count(&host) == 0, "dead captive is not stranded");
        require(piki.stimulateCalls == 0, "dead captive received no flick");
    }

    // --- 4. Teardown paths leave no stranded Pikmin ------------------------
    {
        gBridge = true;
        pc_p2_sarai_forget();
        Piki piki;
        // Stale owner generation is inert; the exact campaign token revokes.
        require(pc_p2_sarai_piki_capture(&piki, &host, &mouthA, campaignToken, 0), "re-capture owner_lost");
        pc_p2_sarai_owner_lost(campaignToken ^ 0x1u);
        require(pc_p2_sarai_piki_bound(&piki), "a stale owner generation does not revoke");
        pc_p2_sarai_owner_lost(campaignToken);
        require(!pc_p2_sarai_piki_bound(&piki) && pc_p2_sarai_carried_count(&host) == 0,
                "owner_lost revokes the exact generation and strands nothing");
        require(!piki.isStickToMouth(), "owner_lost clears the engine mouth link");

        // scene_exit detaches every live binding unconditionally.
        Piki pikiA, pikiB;
        require(pc_p2_sarai_piki_capture(&pikiA, &host, &mouthA, campaignToken, 0), "scene_exit capture A");
        require(pc_p2_sarai_piki_capture(&pikiB, &host, &mouthB, campaignToken, 1), "scene_exit capture B");
        pc_p2_sarai_scene_exit();
        require(pc_p2_sarai_carried_count(&host) == 0, "scene_exit strands no Pikmin");
        require(!pc_p2_sarai_piki_bound(&pikiA) && !pc_p2_sarai_piki_bound(&pikiB),
                "scene_exit clears every binding");
        require(!pikiA.isStickToMouth() && !pikiB.isStickToMouth(), "scene_exit clears every mouth link");

        // A room teardown after re-entry is clean: no binding survives.
        require(pc_p2_sarai_piki_capture(&pikiA, &host, &mouthA, campaignToken, 0), "re-entry capture");
        pc_p2_sarai_forget();
        require(!pc_p2_sarai_piki_bound(&pikiA) && pc_p2_sarai_carried_count(&host) == 0,
                "forget clears the claim after teardown");
    }

    std::printf("p2_sarai_campaign_test PASS checks=%d\n", gChecks);
    std::fflush(stdout);
    return 0;
}
