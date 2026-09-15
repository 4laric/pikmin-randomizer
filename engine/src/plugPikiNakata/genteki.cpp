#include "Age.h"
#include "DebugLog.h"
#include "Dolphin/os.h"
#include "Generator.h"
#include "TekiParameters.h"
#include "TekiPersonality.h"
#include "sysNew.h"
#include "teki.h"
#include "pc_randomizer.h"
#include <cstdio>

static bool randomizerProtected(TekiPersonality* personality) {
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
    const int replacement = pc_randomizer_enemy_for_generator(mTekiType, randomizerProtected(mPersonality), generator);
    tekiMgr->mUsingType[replacement] = true;
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
    const bool protectedSpawn = randomizerProtected(mPersonality);
    const int replacement = pc_randomizer_enemy_for_generator(mTekiType, protectedSpawn, info.mGenerator);
	Teki* teki = tekiMgr->newTeki(replacement);
	if (!teki) {
		return nullptr;
	}

	mPersonality->mPosition.set(info.mPosition);
	mPersonality->mNestPosition.set(info.mScale);
	mPersonality->mFaceDirection = info.mRotation.y;
	teki->mPersonality->input(*mPersonality);
	teki->reset();
	teki->startAI(0);
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
        const unsigned source = pc_randomizer_p2_source_for_id(uid);
        if (source)
            std::printf("P2_SEED_RESOLVE source_id=%u target=%u original_type=%d x=%.1f z=%.1f\n",
                        source, uid, int(mTekiType), info.mPosition.x, info.mPosition.z);
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
