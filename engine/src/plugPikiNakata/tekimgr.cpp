#include "pc_p2_umimushi.h"
#include "pc_p2_jigumo.h"
#include "pc_p2_snakejoint.h"
#include "pc_p2_dangomushi.h"
#include "pc_p2_hanachirashi.h"
#include "pc_p2_catfish.h"
#include "pc_p2_mar.h"
#include "pc_p2_tadpole.h"
#include "pc_p2_hana.h"
#include "pc_p2_kurage_teki.h"
#include "pc_p2_teki_lifetime.h"
#include "pc_p2_onikurage_teki.h"
#include "pc_p2_frog.h"
#include "pc_p2_kogane.h"
#include "pc_p2_mamuta.h"
#include "pc_p2_tank.h"
#include "pc_p2_hiba.h"
#include "pc_p2_flora_actor.h"
#include "pc_p2_qurione.h"
#include "pc_p2_shijimi.h"
#include "pc_p2_kochappy_fsm.h"
#ifdef PIKI_PC_PORT
#include "pc_p2_sheargrub.h"
#include "pc_p2_breadbug_visual.h"
#include "pc_p2_giant_breadbug_visual.h"
#include "pc_p2_bulblax_visual.h"
#include "pc_p2_breadbug_actor.h"
#include "pc_p2_giant_breadbug_actor.h"
#include "pc_p2_queen.h"
#include "pc_p2_king.h"
#include "pc_p2_batch2.h"
#include "pc_p2_projectiles.h"
#include "pc_p2_sokkuri.h"
#include "pc_p2_armor.h"
#include "pc_p2_elecbug.h"
#include "pc_p2_tamago.h"
#include "pc_p2_imomushi.h"
#include "pc_p2_batch3.h"
#include "pc_p2_long_legs.h"
#include "pc_p2_dweevil.h"
#include "pc_p2_bombotakara.h"
#endif
#include "DebugLog.h"
#include "Dolphin/os.h"
#include "MemStat.h"
#include "PlayerState.h"
#include "TekiAnimationManager.h"
#include "TekiParameters.h"
#include "TekiStrategy.h"
#include "TekiYamashita.h"
#include "gameflow.h"
#include "nlib/System.h"
#include "sysNew.h"
#include "teki.h"
#include "timers.h"

/**
 * @todo: Documentation
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(__LINE__) // Never used in the DLL

/**
 * @todo: Documentation
 * @note UNUSED Size: 0000F0
 */
DEFINE_PRINT("tekiMgr");

TekiMgr* tekiMgr;

immut char* TekiMgr::typeNames[TEKI_TypeCount] = {
	"frog",     // 0, Yellow Wollywog
	"iwagen",   // 1, Iwagen (unused enemy)
	"iwagon",   // 2, Rolling Boulder
	"chappy",   // 3, Dwarf Bulborb
	"swallow",  // 4, Spotty Bulborb
	"mizigen",  // 5, Honeywisp Spawner
	"qurione",  // 6, Honeywisp
	"palm",     // 7, Pellet Posy
	"collec",   // 8, Breadbug
	"kinoko",   // 9, Puffstool
	"shell",    // 10, Pearly Clamclamp (shell)
	"napkid",   // 11, Swooping Snitchbug
	"hollec",   // 12, Breadbug Nest
	"pearl",    // 13, Pearly Clamclamp (pearl)
	"rocpe",    // 14, Pearly Clamclamp (ship part)
	"tank",     // 15, Fiery Blowhog
	"mar",      // 16, Puffy Blowhog
	"beatle",   // 17, Armored Cannon Beetle
	"kabekuiA", // 18, Female Sheargrub
	"kabekuiB", // 19, Male Sheargrub
	"kabekuiC", // 20, Shearwig
	"tamago",   // 21, Giant Egg (for Smoky Progg)
	"dororo",   // 22, Smoky Progg
	"hibaA",    // 23, Fire Geyser
	"miurin",   // 24, Mamuta
	"otama",    // 25, Wogpole
	"usuba",    // 26, Usuba (unused enemy, crashes)
	"yamash3",  // 27, ? (unused enemy, crashes)
	"yamash4",  // 28, ? (unused enemy, crashes)
	"yamash5",  // 29, ? (unused enemy, crashes)
	"namazu",   // 30, Water Dumple
	"chappb",   // 31, Dwarf Bulbear
	"swallob",  // 32, Spotty Bulbear
	"frow",     // 33, Wollywog
	"nakata1",  // 34, ? (unused enemy, crashes)
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	// Lane-30 captor spawn identity. No dedicated Demon teki bank exists in the
	// port; the spawned actor is an invisible identity/lifetime anchor whose
	// visual is drawn by P2DemonHost, so it reuses the retail Chappy bank.
	// The identity is the distinct appended type id (TEKI_P2Demon), not the name.
	"chappy",   // 35, PC-only lane-30 captor anchor
#endif
};

int TekiMgr::typeIds[TEKI_TypeCount] = {
	'tkfr', // 0, Yellow Wollywog
	'tkig', // 1, Iwagen (unused enemy)
	'tkiw', // 2, Rolling Boulder
	'tkch', // 3, Dwarf Bulborb
	'tksw', // 4, Spotty Bulborb
	'tkmi', // 5, Honeywisp Spawner
	'tkqu', // 6, Honeywisp
	'tkpa', // 7, Pellet Posy
	'tkco', // 8, Breadbug
	'tkki', // 9, Puffstool
	'tksh', // 10, Pearly Clamclamp (shell)
	'tkna', // 11, Swooping Snitchbug
	'tkho', // 12, Breadbug Nest
	'tkpe', // 13, Pearly Clamclamp (pearl)
	'tkro', // 14, Pearly Clamclamp (ship part)
	'tkta', // 15, Fiery Blowhog
	'tkma', // 16, Puffy Blowhog
	'tkbe', // 17, Armored Cannon Beetle
	'tkka', // 18, Female Sheargrub
	'tkkb', // 19, Male Sheargrub
	'tkkc', // 20, Shearwig
	'tktm', // 21, Giant Egg (for Smoky Progg)
	'tkdo', // 22, Smoky Progg
	'tkhi', // 23, Fire Geyser
	'tkmu', // 24, Mamuta
	'tkot', // 25, Wogpole
	'tkus', // 26, Usuba (unused enemy, crashes)
	'tky3', // 27, ? (unused enemy, crashes)
	'tky4', // 28, ? (unused enemy, crashes)
	'tky5', // 29, ? (unused enemy, crashes)
	'tknm', // 30, Water Dumple
	'tkcb', // 31, Dwarf Bulbear
	'tksb', // 32, Spotty Bulbear
	'tkfw', // 33, Wollywog
	'tkn1', // 34, ? (unused enemy, crashes)
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	'tkch', // 35, PC-only lane-30 captor anchor (reuses the Chappy pellet id)
#endif
};

/**
 * @todo: Documentation
 */
void TekiMgr::initTekiMgr()
{
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	{ pc_p2_snow_reset(); pc_p2_sheargrub_reset(); pc_p2_kochappy_reset(); pc_p2_dwarf_orange_reset(); pc_p2_kochappy_fsm_reset(); pc_p2_giant_breadbug_actor_reset(); pc_p2_breadbug_actor_reset(); pc_p2_queen_reset(); pc_p2_king_reset(); pc_p2_frog_reset(); pc_p2_kogane_reset(); pc_p2_mamuta_reset(); pc_p2_tank_reset(); pc_p2_hiba_reset(); pc_p2_bombotakara_reset(); pc_p2_dweevil_reset(); pc_p2_qurione_reset(); pc_p2_shijimi_reset(); pc_p2_kurage_teki_reset(); pc_p2_onikurage_teki_reset(); pc_p2_batch2_reset(); pc_p2_projectiles_reset(); pc_p2_sokkuri_reset(); pc_p2_armor_reset(); pc_p2_elecbug_reset(); pc_p2_tamago_reset(); pc_p2_umimushi_reset(); pc_p2_jigumo_reset(); pc_p2_snakejoint_reset(); pc_p2_dangomushi_reset(); pc_p2_hanachirashi_reset(); pc_p2_catfish_reset(); pc_p2_mar_reset(); pc_p2_tadpole_reset(); pc_p2_hana_reset(); pc_p2_imomushi_reset(); pc_p2_batch3_reset(); pc_p2_long_legs_reset(); pc_p2_flora_reset(); }
#endif
	tekiMgr = nullptr;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 00007C
 */
int TekiMgr::getTypeIndex(immut char* typeName)
{
	for (int i = 0; i < TEKI_TypeCount; i++) {
		if (strcmp(typeNames[i], typeName) == 0) {
			return i;
		}
	}
	PRINT_NAKATA("!getType:%s\n", typeName);
	return -1;
}

/**
 * @todo: Documentation
 */
TekiMgr::TekiMgr()
{
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	// Stage teardown nulls the global manager. Do not clear an unrelated live manager.
	if (!tekiMgr) { pc_p2_snow_reset(); pc_p2_sheargrub_reset(); pc_p2_kochappy_reset(); pc_p2_dwarf_orange_reset(); pc_p2_kochappy_fsm_reset(); pc_p2_giant_breadbug_actor_reset(); pc_p2_breadbug_actor_reset(); pc_p2_queen_reset(); pc_p2_king_reset(); pc_p2_frog_reset(); pc_p2_kogane_reset(); pc_p2_mamuta_reset(); pc_p2_tank_reset(); pc_p2_hiba_reset(); pc_p2_bombotakara_reset(); pc_p2_dweevil_reset(); pc_p2_qurione_reset(); pc_p2_shijimi_reset(); pc_p2_kurage_teki_reset(); pc_p2_onikurage_teki_reset(); pc_p2_batch2_reset(); pc_p2_projectiles_reset(); pc_p2_sokkuri_reset(); pc_p2_armor_reset(); pc_p2_elecbug_reset(); pc_p2_tamago_reset(); pc_p2_umimushi_reset(); pc_p2_jigumo_reset(); pc_p2_snakejoint_reset(); pc_p2_dangomushi_reset(); pc_p2_hanachirashi_reset(); pc_p2_catfish_reset(); pc_p2_mar_reset(); pc_p2_tadpole_reset(); pc_p2_hana_reset(); pc_p2_imomushi_reset(); pc_p2_batch3_reset(); pc_p2_long_legs_reset(); pc_p2_flora_reset(); }
#endif
	PRINT_NAKATA("TekiMgr>\n");
	memStat->start("tekiMgr");
	int heapStartSize = NSystem::getFreeHeap();
	mTekiAnimMgr      = new TekiAnimationManager(this);
	mMotionTable      = PaniTekiAnimator::createMotionTable();
	mStrategyTable    = new TekiStrategyTable(TEKI_TypeCount);
	mTekiSoundTables  = new PaniSoundTable*[TEKI_TypeCount];
	int i;
	for (i = 0; i < TEKI_TypeCount; i++) {
		mTekiParams[i]      = nullptr;
		mTekiSoundTables[i] = nullptr;
		mTekiShapes[i]      = nullptr;
	}

	TekiNakata::makeTekiParameters(this);
	TekiYamashita::makeTekiParameters(this);

	for (i = 0; i < TEKI_TypeCount; i++) {
		if (hasType(i)) {
			char buf[128];
			sprintf(buf, "tekipara/%s.bin", typeNames[i]);
			PRINT_NAKATA("TekiMgr:fileName:%d:%s\n", i, buf);
			mTekiParams[i]->load("", buf, 1);
		}
	}

	setUsingTypeTable(false);
	setVisibleTypeTable(true);
	memStat->end("tekiMgr");

	int heapEndSize = NSystem::getFreeHeap();

	memStat->start("tekis");
	int tekisHeapStartSize = NSystem::getFreeHeap();
	create(80);
	memStat->end("tekis");

	int tekiHeapEndSize = NSystem::getFreeHeap();
	PRINT("TekiMgr:manager uses %.2f[KB],%d tekis use %.2f[KB]\n", (heapStartSize - heapEndSize) / 1024.0f, 80,
	      (tekisHeapStartSize - tekiHeapEndSize) / 1024.0f);
	PRINT_NAKATA("TekiMgr<\n");
}

/**
 * @todo: Documentation
 */
void TekiMgr::startStage()
{
	char filename[128];
	char buf[128];
	PRINT_NAKATA("startStage>\n");
	TekiNakata::makeTekis(this);
	TekiYamashita::makeTekis(this);

	memStat->start("teki data");
	int dataHeapStartSize = NSystem::getFreeHeap();

	for (int i = 0; i < TEKI_TypeCount; i++) {
		if (isUsingType(i) && hasModel(i)) {
			memStat->start(typeNames[i]);
			sprintf(buf, "%s model data", typeNames[i]);
			int tekiHeapStartSize = NSystem::getFreeHeap();
			sprintf(filename, "tekis/%s/%s.mod", typeNames[i], typeNames[i]);
			PRINT_NAKATA("startStage:fileName:%d:%s\n", i, filename);
			mTekiShapes[i]       = new TekiShapeObject(gameflow.loadShape(filename, true));
			int modelHeapEndSize = NSystem::getFreeHeap();

			sprintf(buf, "%s animation data", typeNames[i]);
			int animHeapStartSize = NSystem::getFreeHeap();
			sprintf(filename, "tekikeys/%s.key", typeNames[i]);
			mTekiShapes[i]->mAnimMgr->loadAnims(filename, nullptr);
			PRINT_NAKATA("startStage:%d:%d\n", i, mTekiShapes[i]->mAnimMgr->countAnims());
			memStat->end(typeNames[i]);
			int tekiHeapEndSize = NSystem::getFreeHeap();
			add(mTekiShapes[i]->mAnimMgr);
			PRINT("startStage:%s uses %.2f[KB](model:%.2f,animation:%.2f)\n", typeNames[i], (tekiHeapStartSize - tekiHeapEndSize) / 1024.0f,
			      (tekiHeapStartSize - modelHeapEndSize) / 1024.0f, (animHeapStartSize - tekiHeapEndSize) / 1024.0f);
		}
	}

	memStat->end("teki data");
	NSystem::getFreeHeap();
	reset();
	PRINT_NAKATA("startStage<\n");
}

/**
 * @todo: Documentation
 */
void TekiMgr::update()
{
	gsys->mTimer->start("teki updt", true);
	MonoObjectMgr::update();
	gsys->mTimer->stop("teki updt");
}

/**
 * @todo: Documentation
 */
void TekiMgr::refresh(Graphics& gfx)
{
	gsys->mTimer->start("teki draw", true);
	for (int i = 0; i < mMaxElements; i++) {
		if (mEntryStatus[i] == 0) {
			Teki* teki = (Teki*)mObjectList[i];
			if (isVisibleType(teki->mTekiType)) {
				teki->refresh(gfx);
			}
		}
	}
	gsys->mTimer->stop("teki draw");
}

/**
 * @todo: Documentation
 */
Teki* TekiMgr::newTeki(int type)
{
	if (type < TEKI_START || type >= TEKI_TypeCount) {
		PRINT("?newTeki:%d\n", type);
		type = TEKI_Frog; // lol
	}
	Teki* teki = (Teki*)birth();
	if (!teki) {
		PRINT("!!!newTeki:can't create any more\n");
		return nullptr;
	}

#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	// Slot reuse calls the same centralized seam as the death funnel so a pooled
	// address can never retain a stale family registration.
	pc_p2_forget_teki(teki);
#endif
	teki->init(type);
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	pc_p2_snow_campaign_bind(teki);
#endif
	return teki;
}

/**
 * @todo: Documentation
 */
void TekiMgr::reset()
{
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	if (this == tekiMgr) { pc_p2_snow_reset(); pc_p2_sheargrub_reset(); pc_p2_kochappy_reset(); pc_p2_dwarf_orange_reset(); pc_p2_kochappy_fsm_reset(); pc_p2_breadbug_visual_reset(); pc_p2_giant_breadbug_visual_reset(); pc_p2_bulblax_visual_reset(); pc_p2_giant_breadbug_actor_reset(); pc_p2_breadbug_actor_reset(); pc_p2_queen_reset(); pc_p2_king_reset(); pc_p2_frog_reset(); pc_p2_kogane_reset(); pc_p2_mamuta_reset(); pc_p2_tank_reset(); pc_p2_hiba_reset(); pc_p2_bombotakara_reset(); pc_p2_dweevil_reset(); pc_p2_qurione_reset(); pc_p2_shijimi_reset(); pc_p2_kurage_teki_reset(); pc_p2_onikurage_teki_reset(); pc_p2_batch2_reset(); pc_p2_projectiles_reset(); pc_p2_sokkuri_reset(); pc_p2_armor_reset(); pc_p2_elecbug_reset(); pc_p2_tamago_reset(); pc_p2_umimushi_reset(); pc_p2_jigumo_reset(); pc_p2_snakejoint_reset(); pc_p2_dangomushi_reset(); pc_p2_hanachirashi_reset(); pc_p2_catfish_reset(); pc_p2_mar_reset(); pc_p2_tadpole_reset(); pc_p2_hana_reset(); pc_p2_imomushi_reset(); pc_p2_batch3_reset(); pc_p2_long_legs_reset(); pc_p2_flora_reset(); }
#endif
	PRINT_NAKATA("reset>\n");
	Iterator iter(this);
	CI_LOOP(iter)
	{
		Teki* teki = (Teki*)*iter;
		teki->reset();
	}

	PRINT_NAKATA("reset<\n");
}

/**
 * @todo: Documentation
 */
Creature* TekiMgr::createObject()
{
	return new Teki();
}

/**
 * @todo: Documentation
 */
TekiStrategy* TekiMgr::getStrategy(int tekiType)
{
	return mStrategyTable->getStrategy(tekiType);
}

/**
 * @todo: Documentation
 */
TekiParameters* TekiMgr::getTekiParameters(int tekiType)
{
	return mTekiParams[tekiType];
}

/**
 * @todo: Documentation
 */
TekiShapeObject* TekiMgr::getTekiShapeObject(int tekiType)
{
	return mTekiShapes[tekiType];
}

/**
 * @todo: Documentation
 */
PaniSoundTable* TekiMgr::getSoundTable(int tekiType)
{
	return mTekiSoundTables[tekiType];
}

/**
 * @todo: Documentation
 */
void TekiMgr::refresh2d(Graphics& gfx)
{
	Iterator iter(this);
	CI_LOOP(iter)
	{
		Teki* teki = (Teki*)*iter;
		teki->refresh2d(gfx);
	}
}

/**
 * @todo: Documentation
 */
void TekiMgr::setUsingTypeTable(bool isUsingType)
{
	for (int i = 0; i < TEKI_TypeCount; i++) {
		mUsingType[i] = isUsingType;
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 00000C
 */
void TekiMgr::setUsingType(int tekiType, bool isUsing)
{
	mUsingType[tekiType] = isUsing;
}

/**
 * @todo: Documentation
 */
void TekiMgr::setVisibleTypeTable(bool isVisibleType)
{
	for (int i = 0; i < TEKI_TypeCount; i++) {
		mVisibleType[i] = isVisibleType;
	}
}

/**
 * @todo: Documentation
 */
void TekiMgr::setVisibleType(int tekiType, bool isVisible)
{
	mVisibleType[tekiType] = isVisible;
}

/**
 * @todo: Documentation
 */
bool TekiMgr::hasModel(int type)
{
	return !(type == TEKI_Mizigen || type == TEKI_Nakata1 || type == TEKI_Yamash3 || type == TEKI_Yamash4 || type == TEKI_Yamash5);
}

/**
 * @todo: Documentation
 */
int TekiMgr::getResultFlag(int tekiType)
{
	int resFlag = 0;
	if (tekiType == TEKI_Collec) {
		resFlag = zen::RESFLAG_Collec;

	} else if (tekiType == TEKI_Frow) {
		resFlag = zen::RESFLAG_Otimoti;

	} else if (tekiType == TEKI_Shell) {
		resFlag = zen::RESFLAG_Shell;

	} else if (tekiType == TEKI_Swallow) {
		resFlag = zen::RESFLAG_Swallow;

	} else if (tekiType == TEKI_Qurione) {
		resFlag = zen::RESFLAG_Mizinko;
	} else {
		PRINT("!getResultFlag:not supported type:%d\n", tekiType);
	}

	return resFlag;
}
