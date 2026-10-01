#include "pc_p2_campaign_actor.h"
#include "Age.h"
#include "DebugLog.h"
#include "Dolphin/os.h"
#include "Generator.h"
#include "TekiParameters.h"
#include "TekiPersonality.h"
#include "sysNew.h"
#include "teki.h"
#include "pc_randomizer.h"
#include "pc_p2_generated_placement.h"
#include "pc_p2_kabuto_host.h"
#include "pc_p2_placement_probe.h"
#include "pc_p2_boss_arena.h"
#include "pc_p2_boss_arena_policy.h"
#include <cstdio>
#include "pc_held_part.h"
#include <cstdlib>

static bool randomizerProtected(TekiPersonality* personality, const void* generator) {
    // #901: a seed-bound P2 occupant takes over a P1 ship-part holder; the
    // part stays in the personality mID and transfers to it.
    if (pc_held_part_transfers(personality->mID.mId, personality->getI(TekiPersonality::INT_Parameter0), generator))
        return false;
    return personality->mID.mId != 'none' || personality->getI(TekiPersonality::INT_Parameter0) != 0;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(13)

/**
 * @todo: Documentation
 * @note UNUSED Size: 0000F0
 */
DEFINE_PRINT(nullptr)

/**
 * @todo: Documentation
 */
static GenObject* makeObjectTeki()
{
	return new GenObjectTeki();
}

/**
 * @todo: Documentation
 */
void GenObjectTeki::initialise()
{
	GenObjectFactory::factory->registerMember('teki', &makeObjectTeki, "敵を発生", 10);
}

/**
 * @todo: Documentation
 */
GenObjectTeki::GenObjectTeki()
    : GenObject('teki', "敵を生む") // 'create enemies'
{
	mTekiType    = TEKI_Frog;
	mPersonality = new TekiPersonality();
}

/**
 * @todo: Documentation
 */
void GenObjectTeki::doRead(RandomAccessStream& input)
{
	if (mVersion <= 8) {
		mTekiType = input.readInt();
	} else {
		mTekiType = input.readByte();
	}

	mPersonality->read(input, mVersion);
}

/**
 * @todo: Documentation
 */
void GenObjectTeki::doWrite(RandomAccessStream& output)
{
	output.writeByte((s8)mTekiType);
	mPersonality->write(output);
}

/**
 * @todo: Documentation
 */
void GenObjectTeki::updateUseList(Generator* generator, int)
{
	if (mTekiType < TEKI_START || mTekiType >= TEKI_TypeCount) {
		ERROR("GenObjectTeki::updateUseList:kind:%d\n", mTekiType);
		return;
	}

	tekiMgr->mUsingType[mTekiType] = true;
    // Keep original generator identity; reserve replacement assets before birth.
    const int replacement = pc_randomizer_enemy_for_generator(mTekiType, randomizerProtected(mPersonality, generator), generator);
    tekiMgr->mUsingType[replacement] = true;
    pc_p2_reserve_source_extras(generator);
    // Replacements may spawn their own actors (Cannon Beetle boulders).
    const int replacementSpawn = tekiMgr->mTekiParams[replacement]->getI(TPI_SpawnType);
    if (replacementSpawn >= TEKI_START && replacementSpawn < TEKI_TypeCount)
        tekiMgr->mUsingType[replacementSpawn] = true;

	if (!tekiMgr->hasType(mTekiType)) {
		ERROR("!tekiMgr->hasType(kind)\n");
		return;
	}

	int tekiType = tekiMgr->mTekiParams[mTekiType]->getI(TPI_SpawnType);
	if (tekiType >= TEKI_START && tekiType < TEKI_TypeCount) {
		tekiMgr->mUsingType[tekiType] = true;
	}
}

/**
 * @todo: Documentation
 */
Creature* GenObjectTeki::birth(BirthInfo& info)
{
    const bool protectedSpawn = randomizerProtected(mPersonality, info.mGenerator);
    // #901: a P1 part-holder slot handed to a seed-bound P2 occupant.
    const bool heldPartTransfer = pc_held_part_transfers(mPersonality->mID.mId,
        mPersonality->getI(TekiPersonality::INT_Parameter0), info.mGenerator);
    const int replacement = pc_randomizer_enemy_for_generator(mTekiType, protectedSpawn, info.mGenerator);
	Teki* teki = tekiMgr->newTeki(replacement);
	if (!teki) {
		return nullptr;
	}

	mPersonality->mPosition.set(info.mPosition);
	mPersonality->mNestPosition.set(info.mScale);
	mPersonality->mFaceDirection = info.mRotation.y;
	teki->mPersonality->input(*mPersonality);
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	// #901: the newborn has no mGenerator until birth returns; let the
	// held-part birth decision see this slot's P2 binding.
	if (heldPartTransfer) {
		const unsigned uid = pc_randomizer_generator_id(info.mGenerator);
		pc_held_part_log_assign(mPersonality->mID.mId, pc_randomizer_p2_source_for_id(uid), uid, mTekiType, "slot");
		pc_held_part_birth_uid(uid);
	}
#endif
	teki->reset();
	teki->startAI(0);
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	pc_held_part_birth_uid(0);
#endif
	teki->mSRT.r = info.mRotation;
	if (info.mGenerator->doAdjustFaceDir()) {
		teki->setCreatureFlag(CF_AdjustFaceDirOnSpawn);
	}

	teki->mRebirthDay = info.mGenerator->getRebirthDay();
    if (pc_randomizer_spawn_slots())
        std::printf("ENEMY_SLOT_BIRTH uid=%u original=%d actual=%d\n", pc_randomizer_generator_id(info.mGenerator), mTekiType, replacement);
    if (pc_randomizer_enemy_shuffle())
        std::printf("[Pikmin Randomizer] ENEMY_SPAWN original=%d actual=%d protected=%d x=%.1f z=%.1f\n", mTekiType, replacement, int(protectedSpawn), info.mPosition.x, info.mPosition.z);
    if (pc_randomizer_p2_bridge() && info.mGenerator) {
        const unsigned uid = pc_randomizer_generator_id(info.mGenerator);
        // P2 boss arenas: read-only clearance measurement of the teki-hosted
        // P1 boss arenas (Puffstool, Cannon Beetle), opt-in.
        if (std::getenv("PIKMIN_P2_BOSS_ARENA_PROBE") && p2bossarena::isArenaUid(uid))
            {
            pc_p2_boss_arena_probe(info.mPosition.x, info.mPosition.y, info.mPosition.z, uid, "p1teki", mTekiType);
            pc_p2_placement_probe_birth(info.mPosition.x, info.mPosition.y, info.mPosition.z, info.mGenerator->_70, uid, mTekiType);
        }
        const unsigned source = pc_randomizer_p2_source_for_id(uid);
        if (source) {
            std::printf("P2_SEED_RESOLVE source_id=%u target=%u original_type=%d x=%.1f z=%.1f\n",
                        source, uid, int(mTekiType), info.mPosition.x, info.mPosition.z);
            if (protectedSpawn) {
                // #948: the generator carries a non-transferable protected drop
                // (Parameter0 holder or a non-part personality), so the P1
                // type was born. Say so rather than failing every family bind
                // silently downstream.
                std::printf("P2_GENERATED_PLACEMENT source_id=%u target=%u generator=%u bound=0 reason=protected-drop\n",
                            source, uid, uid);
            }
            // Generated placement (lane 03/04): claim the spawned actor for its
            // seeded P2 identity module instead of leaving it as a P1 stand-in.
            // wf7 dweevil-impl (#871): pass the seed uid as the generator id.
            // The newborn BTeki has no mGenerator yet, so its campaign token
            // reads 0 here; passing the token created a bogus generator=0
            // Otakara registration (one actor claimed under two identities).
            pc_p2_generated_placement_bind(static_cast<BTeki*>(teki), source, uid, uid);
            // Cannon Beetle family generated-session host (lane 20, #424): no-op
            // for every source outside 75/95/96.
            pc_p2_kabuto_bind_dynamic(teki, uid, source);
            // Lane-04 placement evidence: sample the generated slot's terrain/route
            // at the birth position. Additive; the slot uid is already resolved.
            if (uid)
                pc_p2_placement_probe_birth(info.mPosition.x, info.mPosition.y, info.mPosition.z,
                                            info.mGenerator->_70, uid, replacement);
        }
    }
	return teki;
}

#ifdef WIN32

void GenObjectTeki::doGenAge(AgeServer& server)
{
	server.StartOptionBox("敵", &mTekiType, 252);
	for (int i = 0; i < TEKI_TypeCount; i++) {
		server.NewOption(tekiMgr->getTypeName(i), i);
	}
	server.EndOptionBox();
	mPersonality->genAge(server);
}

#endif
