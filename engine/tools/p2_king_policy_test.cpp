// Standalone Emperor Bulblax (KingChappy) actor policy test (#289, parent #172).
// Compile with MinGW strict flags:
//   g++ -std=c++17 -Wall -Wextra -Werror -I <native>/pc_port tests/pikmin2_king_policy.cpp -o king_policy.exe
// Mirrors tests/test_pikmin2_bulblax_behavior.py against the #227 reference.
#include "pc_p2_king_policy.h"
#include <cassert>
#include <cmath>
#include <sstream>
#include <cstdio>
using namespace p2king;

int main() {
	// State IDs, KingChappy.h:22-36.
	static_assert(Walk == 0 && Attack == 1 && Dead == 2 && Flick == 3 && WarCry == 4 && Damage == 5 && Turn == 6
	              && Eat == 7 && Hide == 8 && HideWait == 9 && Appear == 10 && Caution == 11 && Swallow == 12,
	              "state IDs");

	// Entry state: buried in HideWait. kingChappy.cpp:107.
	assert(entryState() == HideWait);

	// Disc key frames per clip, kingchappy/enemyanimmgr.txt.
	assert(clipKeys("attack").frames == 95 && clipKeys("attack").keyCount == 5 && clipKeys("attack").keys[0] == 25
	       && clipKeys("attack").keys[1] == 40 && clipKeys("attack").keys[2] == 70 && clipKeys("attack").keys[3] == 86
	       && clipKeys("attack").keys[4] == 92);
	assert(clipKeys("cry").frames == 138 && clipKeys("cry").keys[0] == 33 && clipKeys("cry").keys[1] == 38
	       && clipKeys("cry").keys[2] == 65 && clipKeys("cry").keys[3] == 100 && clipKeys("cry").keys[4] == 103);
	assert(clipKeys("damage").frames == 135 && clipKeys("damage").keyCount == 7 && clipKeys("damage").keys[0] == 12
	       && clipKeys("damage").keys[1] == 14 && clipKeys("damage").keys[2] == 15 && clipKeys("damage").keys[3] == 46
	       && clipKeys("damage").keys[4] == 60 && clipKeys("damage").keys[5] == 65 && clipKeys("damage").keys[6] == 94);
	assert(clipKeys("dead").frames == 200 && clipKeys("dead").keys[0] == 185);
	assert(clipKeys("dive").frames == 142 && clipKeys("dive").keys[0] == 58 && clipKeys("dive").keys[1] == 60
	       && clipKeys("dive").keys[2] == 90);
	assert(clipKeys("flick").frames == 70 && clipKeys("flick").keys[0] == 30 && clipKeys("flick").keys[1] == 35);
	assert(clipKeys("move1").frames == 80 && clipKeys("move1").keys[0] == 15 && clipKeys("move1").keys[1] == 54);
	assert(clipKeys("type3").frames == 75 && clipKeys("type3").keys[0] == 3 && clipKeys("type3").keys[1] == 55
	       && clipKeys("type3").keys[2] == 58);
	assert(clipKeys("wait2").frames == 40 && clipKeys("wait2").keys[0] == 0 && clipKeys("wait2").keys[1] == 39);
	assert(clipKeys("waitact1").frames == 50 && clipKeys("waitact1").keys[0] == 10 && clipKeys("waitact1").keys[1] == 33);
	assert(clipKeys("type1").frames == 45 && clipKeys("type2").frames == 35 && clipKeys("waitact2").frames == 60);
	assert(clipKeys("carry").frames == 0); // carry stays P1-authoritative

	// Appear trigger math: 60 disc * scale after 0 disc frames.
	// kingChappyState.cpp:1970-2016.
	assert(!hidewaitWake(59.9f, 0, 1.0f, 60.0f, 0));  // 0 frames waited is not > 0
	assert(hidewaitWake(59.9f, 1, 1.0f, 60.0f, 0));
	assert(!hidewaitWake(60.0f, 1, 1.0f, 60.0f, 0));  // strict <
	assert(hidewaitWake(89.9f, 1, 1.5f, 60.0f, 0));   // big scale widens the range
	assert(!hidewaitWake(90.0f, 1, 1.5f, 60.0f, 0));
	assert(!hidewaitWake(10.0f, 200, 1.0f, 60.0f, 200)); // header time_to_appearance gate
	assert(hidewaitWake(10.0f, 201, 1.0f, 60.0f, 200));
	assert(DistanceToSpawn == 60.0f && TimeToAppearance == 0);

	// Appear shake-off range 100 / power 200.
	assert(AppearShakeOffRange == 100.0f && AppearShakeOffPower == 200.0f && AppearShakeOffKey == 55);

	// Walk turn thresholds 60/40 disc. kingChappyState.cpp:53-117.
	assert(walkTurn(60.1f, 60.0f, 40.0f) == TurnDecision::Turn);
	assert(walkTurn(-60.1f, 60.0f, 40.0f) == TurnDecision::Turn);
	assert(walkTurn(50.0f, 60.0f, 40.0f) == TurnDecision::Walk);
	assert(walkTurn(40.0f, 60.0f, 40.0f) == TurnDecision::FinishTurn);
	assert(walkTurn(-39.9f, 60.0f, 40.0f) == TurnDecision::FinishTurn);
	assert(RequiredTurningAngleDeg == 60.0f && TurningEndAngleDeg == 40.0f);

	// Incubation 500 frames without a target. kingChappyState.cpp:53-117.
	assert(!walkGiveUp(500, 500, false));
	assert(walkGiveUp(501, 500, false));
	assert(walkGiveUp(0, 500, true));
	assert(PeriodOfIncubation == 500);

	// checkDead: WarCry only with death rate > roll (rate 0 disc -> never).
	assert(checkDead(0.0f, 0.0f) == DeadChoice::Dead);
	assert(checkDead(0.4f, 0.5f) == DeadChoice::WarCry);
	assert(checkDead(0.6f, 0.5f) == DeadChoice::Dead);
	assert(DeathRate == 0.0f);

	// checkFlick: WarCry p=0.5 under half HP, else Flick. kingChappy.cpp:2457-2474.
	assert(checkFlick(649.9f, 1300.0f, 0.49f) == WarCry);
	assert(checkFlick(649.9f, 1300.0f, 0.5f) == Flick);   // roll < rate strictly
	assert(checkFlick(650.0f, 1300.0f, 0.0f) == Flick);   // not under half HP
	assert(checkFlick(1300.0f, 1300.0f, 0.0f) == Flick);
	assert(FlickShoutRate == 0.5f);

	// Tongue arm/eat keys: key 3 arms Pikmin eating, key 6 allows bombs.
	assert(AttackArmKey == 40 && AttackBombKey == 92);
	assert(attackStep(3, true, false, true) == 1);
	assert(attackStep(3, true, true, true) == 1);    // bombs not allowed on key 3
	assert(attackStep(6, true, true, false) == 2);
	assert(attackStep(6, true, true, true) == 3);
	assert(attackStep(3, false, false, true) == 0);  // no free slot
	assert(attackStep(0, true, true, true) == 0);    // unarmed frame
	// Attack end routing.
	assert(attackEnd(1, 0) == Eat);
	assert(attackEnd(0, 2) == Swallow);
	assert(attackEnd(0, 0) == Walk);
	assert(attackEnd(2, 1) == Eat); // bombs take the Eat -> Damage route

	// Mouth slot math: 9 slots kamu1..9, radius 25 * scale; tongue tip radius 5.
	assert(MouthSlots == 9 && MouthSlotRadius == 25.0f && TongueTipRadius == 5.0f);
	assert(AttackDamage == 5.0f); // captains in any slot take 5 disc

	// Bomb rules: only BOMB_Wait eatable; 200 * count; 180 stun; external
	// quartered; beyond-80 targeting default on.
	assert(eatableBomb("BOMB_Wait"));
	assert(!eatableBomb("BOMB_Bomb") && !eatableBomb("BOMB_Set"));
	assert(bombDamage(1) == 200.0f && bombDamage(3) == 600.0f && bombDamage(0) == 0.0f);
	assert(BombDamageTime == 180);
	assert(ExternalBlastFactor == 0.25f);
	assert(canTargetBomb(80.1f, true));
	assert(!canTargetBomb(80.0f, true));
	assert(!canTargetBomb(100.0f, false));
	assert(InvisibleRange == 80.0f);
	assert(damageEnd(0.0f) == Dead && damageEnd(1.0f) == Walk);

	// Damage tiers. kingChappy.cpp:824-856.
	assert(damageTier(true, false, false, 0.0f, 0.0f) == 0.1f);           // petrified
	assert(damageTier(false, true, true, 0.0f, 0.0f) == 1.0f);            // stuck to part
	assert(damageTier(false, true, false, 0.0f, 0.0f) == 0.0f);           // part, not stuck
	assert(damageTier(false, false, false, 4.9f, 1599.0f) == 0.2f);       // ground, in range
	assert(damageTier(false, false, false, 4.9f, 1601.0f) == 0.0f);       // ground, out of range
	assert(damageTier(false, false, false, 5.0f, 0.0f) == 0.0f);          // above -> nothing
	assert(PetrifiedDamageFactor == 0.1f && GroundAttackFactor == 0.2f && GroundAttackRange == 40.0f);

	// Flick trample: captains flicked only if none pressed.
	const FlickStep none = flickStep(0, 0);
	assert(none.pressedPikmin == 0 && none.flickCaptains);
	const FlickStep some = flickStep(3, 1);
	assert(some.pressedPikmin == 3 && some.pressedCaptains == 1 && !some.flickCaptains);
	assert(TramplingRange == 45.0f && TrampleHeightBand == 30.0f && ShakeRange == 60.0f && FlickTrampleKey == 35);

	// WarCry cross-Emperor contract (two-Emperor scope).
	assert(crossEmperorTarget(HideWait) == Appear);
	assert(crossEmperorTarget(Walk) == WarCry);
	assert(crossEmperorTarget(Dead) == -1 && crossEmperorTarget(Attack) == -1);
	assert(CryCrossEmperorKey == 38 && CryAstonishKey == 65);
	assert(RoarEffectiveRange == 300.0f && RoarEffectiveAngleDeg == 180.0f);

	// Swallow poison: hardcoded 300; fp14 header 300 / disc 200 distinct.
	assert(SwallowPoisonDamage == 300.0f && WhitePikminParmHeader == 300.0f && WhitePikminParmDisc == 200.0f);

	// Big variant params. kingChappy.cpp:60-72, 148-158.
	assert(isBig(Variant::F03) && isBig(Variant::ForceBig) && !isBig(Variant::Default));
	const VariantInfo big = variantInfo(Variant::F03);
	assert(big.big && big.scale == 1.5f && big.health == 1800.0f && big.speed == 45.0f && big.floorOffset == 60.0f);
	const VariantInfo base = variantInfo(Variant::Default);
	assert(!base.big && base.scale == 1.0f && base.health == 1300.0f && base.floorOffset == 0.0f);
	assert(BigScale == 1.5f && BigHealth == 1800.0f && BigSpeed == 45.0f && BigFloorOffset == 60.0f);

	// Invalid numbers are rejected.
	bool threw = false;
	try {
		hidewaitWake(std::nanf(""), 1, 1.0f, 60.0f, 0);
	} catch (const std::runtime_error&) { threw = true; }
	assert(threw);
	threw = false;
	try {
		checkFlick(1.0f, 0.0f, 0.5f);
	} catch (const std::runtime_error&) { threw = true; }
	assert(threw);
	threw = false;
	try {
		walkGiveUp(-1, 500, false);
	} catch (const std::runtime_error&) { threw = true; }
	assert(threw);

	// P2_KING_ACTOR_1 strict config validation.
	const std::string clips = "P2_KING_ACTOR_1\n13\n"
	                          "53 attack 95 2 0 94\n53 cry 138 2 0 137\n53 damage 135 2 0 134\n53 dead 200 2 0 199\n"
	                          "53 dive 142 2 0 141\n53 flick 70 2 0 69\n53 move1 80 2 0 79\n53 type1 45 2 0 44\n"
	                          "53 type2 35 2 0 34\n53 type3 75 2 0 74\n53 wait2 40 2 0 39\n53 waitact1 50 2 0 49\n"
	                          "53 waitact2 60 2 0 59\n";
	auto parse = [](const std::string& s) {
		std::istringstream in(s);
		return readActorConfig(in);
	};
	{
		const std::string good = clips + "2\n230020 default 34 30 1896 0\n230021 f_03 150 30 1500 90\n"
		                         "2\n360001 40 30 1900 0\n360002 42 30 1892 1200\n";
		const ActorConfig cfg = parse(good);
		assert(cfg.clips.size() == 13 && cfg.placements.size() == 2 && cfg.bombs.size() == 2);
		assert(cfg.placements[0].variant == Variant::Default && cfg.placements[1].variant == Variant::F03);
		assert(cfg.bombs[0].externalBlastTick == 0 && cfg.bombs[1].externalBlastTick == 1200);
		assert(cfg.clip(53, "type3") && !cfg.clip(53, "carry") && !cfg.clip(30, "dead"));
		assert(cfg.clip(53, "damage")->index(94.0f) == 1);
	}
	{
		const std::string ok = clips + "1\n230020 force_big 0 30 0 0\n0\n";
		const ActorConfig cfg = parse(ok);
		assert(cfg.placements.size() == 1 && cfg.placements[0].variant == Variant::ForceBig && cfg.bombs.empty());
	}
	auto reject = [&](const std::string& s) {
		bool bad = false;
		try {
			parse(s);
		} catch (const std::runtime_error&) { bad = true; }
		assert(bad);
	};
	reject(clips + "1\n230020 default 0 0 0 0\n0\njunk");
	reject(clips + "2\n230020 default 0 0 0 0\n230020 default 1 1 1 1\n0\n"); // duplicate id
	reject(clips + "1\n4294967296 default 0 0 0 0\n0\n");                     // id overflow
	reject(clips + "1\n230020 x_99 0 0 0 0\n0\n");                            // unknown variant
	reject(clips + "1\n230020 default nan 0 0 0\n0\n");                       // non-finite xyz
	reject(clips + "1\n230020 default 100001 0 0 0\n0\n");                    // xyz bound
	reject(clips + "1\n230020 default 0 0 0 361\n0\n");                       // yaw bound
	reject(clips + "3\n1 default 0 0 0 0\n2 default 0 0 0 0\n3 default 0 0 0 0\n0\n"); // > 2 Emperors
	reject(clips + "1\n230020 default 0 0 0 0\n1\n230020 0 0 0 0\n");                  // bomb id reuse
	reject(clips + "1\n230020 default 0 0 0 0\n1\n360001 0 0 0 1000001\n");            // blast tick bound
	reject(clips + "0\n");                                                             // placement count 0
	reject(clips);                                                                     // missing sections
	// Missing King clips fail closed.
	reject("P2_KING_ACTOR_1\n1\n53 dead 200 2 0 199\n1\n230020 default 0 0 0 0\n0\n");
	reject("P2_KING_ACTOR_2\n1\n53 dead 200 2 0 199\n1\n230020 default 0 0 0 0\n0\n"); // wrong version
	reject(clips + std::string(""));                                                   // dup handled below
	reject("P2_KING_ACTOR_1\n2\n53 dead 200 2 0 199\n53 dead 200 2 0 199\n1\n230020 default 0 0 0 0\n0\n"); // dup clip
	reject("P2_KING_ACTOR_1\n1\n53 carry 40 2 0 39\n1\n230020 default 0 0 0 0\n0\n");                        // carry excluded
	reject("P2_KING_ACTOR_1\n1\n53 dead 200 2 199 0\n1\n230020 default 0 0 0 0\n0\n");                       // unsorted frames
	reject("P2_KING_ACTOR_1\n1\n53 dead 200 2 0 200\n1\n230020 default 0 0 0 0\n0\n");                       // frame overflow
	reject("P2_KING_ACTOR_1\n1\n30 dead 200 2 0 199\n1\n230020 default 0 0 0 0\n0\n");                       // wrong enemy id

	std::puts("pikmin2_king_policy PASS");
	return 0;
}
