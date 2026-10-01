// Generic held ship part (#901). Contract: pc_held_part_policy.h.
#include "pc_held_part.h"

#include "pc_held_part_policy.h"
#include "pc_randomizer.h"

#include "FlowController.h"
#include "ID32.h"
#include "Pellet.h"
#include "PlayerState.h"
#include "RadarInfo.h"
#include "TekiPersonality.h"
#include "Traversable.h"
#include "teki.h"

#include <cstdio>
#include <cstring>

namespace {

bool partExists(unsigned id)
{
    // PlayerState::existUfoParts: collected, cached on the ground for this
    // stage (GeneratorCache::hasUfoParts), or alive as a pellet right now.
    if (!playerState || !flowCont.mCurrentStage) return false;
    return playerState->existUfoParts(id);
}

// Four-character part id ('uf06'); ID32::mStringID is host byte order.
struct PartName {
    char s[5];
    explicit PartName(unsigned id)
    {
        for (int i = 0; i < 4; ++i) {
            const char c = char((id >> (24 - 8 * i)) & 0xff);
            s[i] = (c >= 32 && c < 127) ? c : '?';
        }
        s[4] = 0;
    }
};

// Generator uid of the birth in progress (GenObjectTeki::birth,
// pc_p2_boss_arena_birth). A newborn BTeki has no mGenerator until its
// generator links it after birth returns.
unsigned birthUid = 0;

unsigned generatorUid(BTeki* teki)
{
    if (teki && teki->mGenerator) return pc_randomizer_generator_id(teki->mGenerator);
    return birthUid;
}

} // namespace

void pc_held_part_birth_uid(unsigned uid)
{
    birthUid = uid;
}

unsigned pc_held_part_p2_source(BTeki* teki)
{
    if (!teki) return 0;
    // Family modules key their binding by the PelletView base; the seed binds
    // by generator uid. Either one marks a P2-bound actor.
    if (const unsigned source = pc_randomizer_p2_source_for(static_cast<PelletView*>(teki))) return source;
    const unsigned uid = generatorUid(teki);
    return uid && pc_randomizer_p2_bridge() ? pc_randomizer_p2_source_for_id(uid) : 0u;
}

unsigned pc_held_part_for_pellet_config(int pelletConfigIdx)
{
    if (!pelletMgr || pelletConfigIdx < 0) return 0;
    PelletConfig* config = pelletMgr->getConfigFromIdx(pelletConfigIdx);
    if (!config || !Pellet::isUfoPartsID(config->mModelId.mId)) return 0;
    return config->mModelId.mId;
}

void pc_held_part_log_assign(unsigned partId, unsigned source, unsigned target, int p1Kind, const char* via)
{
    const bool arena = via && via[0] == 'a';
    std::printf("P2_HELD_PART_ASSIGN part=%s source_id=%u target=%u %s=%d via=%s\n", PartName(partId).s, source,
                target, arena ? "p1_boss" : "p1_teki", p1Kind, via ? via : "?");
    std::fflush(stdout);
}

bool pc_held_part_birth(BTeki* teki)
{
    if (!teki || !teki->mPersonality) return false;
    ID32& id = teki->mPersonality->mID;
    const bool isPart = Pellet::isUfoPartsID(id.mId);
    if (!isPart) return false;
    const PartName partName(id.mId);
    const char* name = partName.s;
    const unsigned source = pc_held_part_p2_source(teki);
    // The existence scan only matters for a P2-bound holder; a P1 holder is
    // vanilla and always holds (the scan is read-only either way).
    const bool exists = source ? partExists(id.mId) : false;
    if (!p2heldpart::keepAtBirth(isPart, exists, source != 0)) {
        std::printf("P2_HELD_PART_CLEAR part=%s generator=%u teki=%d source_id=%u reason=exists\n", name,
                    generatorUid(teki), int(teki->mTekiType), source);
        std::fflush(stdout);
        id.setID('none');
        return false;
    }
    std::printf("P2_HELD_PART_HOLD part=%s generator=%u teki=%d source_id=%u\n", name, generatorUid(teki),
                int(teki->mTekiType), source);
    std::fflush(stdout);
    return true;
}

bool pc_held_part_claim_spawn_items(BTeki* teki)
{
    if (!teki) return false;
    const unsigned source = pc_held_part_p2_source(teki);
    if (!p2heldpart::spawnItemsRuns(teki->mPcHeldPartDropped, source != 0)) return false;
    teki->mPcHeldPartDropped = true;
    if (teki->mPersonality && Pellet::isUfoPartsID(teki->mPersonality->mID.mId)) {
        // A P1 holder's part shape was built at stage init (vanilla); only a
        // P2 occupant can hold a late un** part.
        if (source) pc_held_part_ensure_shape(teki->mPersonality->mID.mId);
        std::printf("P2_HELD_PART_DROP part=%s generator=%u teki=%d source_id=%u via=spawnItems health=%.1f\n",
                    PartName(teki->mPersonality->mID.mId).s, generatorUid(teki), int(teki->mTekiType), source,
                    double(teki->mHealth));
        std::fflush(stdout);
    }
    return true;
}

bool pc_held_part_drop(BTeki* teki, const char* via)
{
    if (!teki || !teki->mPersonality) return false;
    const unsigned id = teki->mPersonality->mID.mId;
    const bool isPart = Pellet::isUfoPartsID(id);
    // Cheap pre-check so the pellet scan in existUfoParts only runs on a
    // real P2 holder death.
    if (teki->mPcHeldPartDropped || !isPart || teki->mHealth > 0.0f) return false;
    const unsigned source = pc_held_part_p2_source(teki);
    const p2heldpart::Funnel funnel =
        via && !std::strcmp(via, "dieSoon") ? p2heldpart::Funnel::DieSoon : p2heldpart::Funnel::Die;
    if (!p2heldpart::funnelDrops(funnel, source != 0)) return false;
    const p2heldpart::Drop drop = p2heldpart::onDeath(false, isPart, teki->mHealth, partExists(id));
    teki->mPcHeldPartDropped = true;
    const PartName name(id);
    if (drop == p2heldpart::Drop::AlreadyExists) {
        if (radarInfo) radarInfo->detachParts(teki);
        std::printf("P2_HELD_PART_SKIP part=%s generator=%u teki=%d source_id=%u reason=exists via=%s\n", name.s,
                    generatorUid(teki), int(teki->mTekiType), source, via ? via : "?");
        std::fflush(stdout);
        return false;
    }
    pc_held_part_ensure_shape(id);
    teki->spawnPellets(int(id), PELCOLOR_Part, 1);
    if (radarInfo) radarInfo->detachParts(teki);
    const bool spawned = partExists(id);
    const Vector3f& pos = teki->getPosition();
    // The spawned pellet itself (read-only scan): where it is and how fast it
    // was launched, so a carry can be followed from the log.
    Vector3f pelPos(0.0f, 0.0f, 0.0f), pelVel(0.0f, 0.0f, 0.0f);
    int minCarriers = -1;
    if (pelletMgr) {
        Iterator it(pelletMgr);
        CI_LOOP(it)
        {
            Pellet* pel = static_cast<Pellet*>(*it);
            if (pel && pel->isAlive() && pel->mConfig && pel->mConfig->mModelId.mId == id) {
                pelPos = pel->getPosition();
                pelVel = pel->mVelocity;
                minCarriers = pel->mConfig->mCarryMinPikis();
                break;
            }
        }
    }
    std::printf("P2_HELD_PART_DROP part=%s generator=%u teki=%d source_id=%u via=%s ok=%d x=%.1f z=%.1f "
                "pellet=(%.1f,%.1f,%.1f) vel=(%.1f,%.1f,%.1f) min_carriers=%d\n",
                name.s, generatorUid(teki), int(teki->mTekiType), source, via ? via : "?", spawned ? 1 : 0,
                double(pos.x), double(pos.z), double(pelPos.x), double(pelPos.y), double(pelPos.z), double(pelVel.x),
                double(pelVel.y), double(pelVel.z), minCarriers);
    std::fflush(stdout);
    return spawned;
}

bool pc_held_part_transfers(unsigned heldId, int parameter0, const void* generator)
{
    if (!generator || parameter0 != 0 || !Pellet::isUfoPartsID(heldId) || !pc_randomizer_p2_bridge()) return false;
    return pc_randomizer_p2_source_for_id(pc_randomizer_generator_id(generator)) != 0;
}

void pc_held_part_ensure_shape(unsigned partId)
{
    if (!pelletMgr || !Pellet::isUfoPartsID(partId)) return;
    if (pelletMgr->pcEnsureShape(partId)) return;
    std::printf("P2_HELD_PART_SHAPE part=%s ok=0\n", PartName(partId).s);
    std::fflush(stdout);
}
