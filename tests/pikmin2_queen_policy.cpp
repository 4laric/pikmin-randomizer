// Standalone Empress Bulblax (Queen) actor policy test (#256, parent #172).
// Compile with MinGW strict flags:
//   g++ -std=c++17 -Wall -Wextra -Werror -I <native>/pc_port tests/pikmin2_queen_policy.cpp -o queen_policy.exe
// Mirrors tests/test_pikmin2_bulblax_behavior.py against the #227 reference.
#include "pc_p2_queen_policy.h"
#include <cassert>
#include <cmath>
#include <sstream>
#include <cstdio>
using namespace p2queen;

int main() {
	// State IDs, Queen.h:26-34.
	static_assert(Dead == 0 && Sleep == 1 && Wait == 2 && Damage == 3 && Flick == 4 && Rolling == 5 && Born == 6,
	              "state IDs");

	// Entry state, Queen.cpp:62-66.
	assert(entryState(true) == Wait);
	assert(entryState(false) == Sleep);

	// Disc key frames per clip.
	assert(clipKeys("sleep").frames == 210 && clipKeys("sleep").keys[0] == 59 && clipKeys("sleep").keys[1] == 118
	       && clipKeys("sleep").keys[2] == 120);
	assert(clipKeys("wait1").frames == 30 && clipKeys("wait1").keys[1] == 29);
	assert(clipKeys("damage").frames == 50 && clipKeys("damage").keys[0] == 10);
	assert(clipKeys("flick").frames == 60 && clipKeys("flick").keys[0] == 40);
	assert(clipKeys("rolling_l").frames == 110 && clipKeys("rolling_l").keys[0] == 20
	       && clipKeys("rolling_l").keys[1] == 67 && clipKeys("rolling_l").keys[2] == 69);
	assert(clipKeys("rolling_r").frames == 110);
	assert(clipKeys("born").frames == 28 && clipKeys("born").keys[0] == 24);
	assert(clipKeys("dead").frames == 140 && clipKeys("dead").keys[0] == 60 && clipKeys("dead").keys[1] == 73
	       && clipKeys("dead").keys[2] == 86 && clipKeys("dead").keys[3] == 99);
	assert(clipKeys("carry").frames == 0); // carry stays P1-authoritative

	// Sleep deferred next state (clip end), QueenState.cpp:89-103.
	assert(sleepNext(100.0f, false, false, false, false) == -1);
	assert(sleepNext(100.0f, false, true, false, false) == Wait);
	assert(sleepNext(100.0f, false, true, false, true) == Damage);
	assert(sleepNext(100.0f, true, false, true, false) == Flick);
	assert(sleepNext(0.0f, false, false, true, false) == Dead);

	// Wait override order: Sleep, Damage, Born, Flick, Dead. QueenState.cpp:153-173.
	assert(waitNext(false, 0.0f, false, false, 100.0f) == -1);
	assert(waitNext(false, 30.1f, false, false, 100.0f) == Sleep);
	assert(waitNext(true, 99.0f, false, false, 100.0f) == Born); // larva due suppresses idle sleep
	assert(waitNext(false, 31.0f, true, false, 100.0f) == Damage);
	assert(waitNext(false, 0.0f, true, true, 100.0f) == Flick);
	assert(waitNext(false, 0.0f, false, true, 0.0f) == Dead);

	// Damage: Born, Wait when unstuck, Flick, Dead. QueenState.cpp:219-237.
	assert(damageNext(false, true, false, 100.0f) == -1);
	assert(damageNext(false, false, false, 100.0f) == Wait);
	assert(damageNext(true, false, false, 100.0f) == Wait);
	assert(damageNext(false, false, true, 100.0f) == Flick);
	assert(damageNext(false, true, false, 0.0f) == Dead);

	// Flick end: Dead else Rolling with alternating side. QueenState.cpp:281-293.
	assert(flickEnd(0.0f, true).first == Dead);
	assert((flickEnd(5.0f, true) == std::pair<int, bool>(Rolling, true)));
	assert((flickEnd(5.0f, false) == std::pair<int, bool>(Rolling, false)));

	// Roll alternation off anim index 6 (rolling_r). QueenState.cpp:441-447.
	assert(nextRollIsLeft(QueenAnimRollingR));
	assert(!nextRollIsLeft(5));
	assert(QueenAnimRollingR == 6);

	// Roll pass: crash at territory-50, timed end near home. QueenState.cpp:405-433.
	assert(rollPass(0.0f, 0.0f, 3.5f, 25.0f, 200.0f, 100.0f) == RollOutcome::Continue);
	assert(rollPass(151.0f, 0.0f, 3.5f, 25.0f, 200.0f, 100.0f) == RollOutcome::Crash);
	assert(rollPass(150.0f, 0.0f, 3.5f, 25.0f, 200.0f, 100.0f) == RollOutcome::Continue);
	assert(rollPass(10.0f, 3.6f, 3.5f, 25.0f, 200.0f, 100.0f) == RollOutcome::Wait);
	assert(rollPass(60.0f, 3.6f, 3.5f, 25.0f, 200.0f, 100.0f) == RollOutcome::Continue);
	assert(RollingTimeSec == 3.5f && TerritoryRadius == 200.0f && TerritoryCrashMargin == 50.0f);

	// Damage coefficients, Queen.cpp:184-198 + audit 104-105.
	assert(damageFactor(Sleep, Attacker::PikminPart) == 0.1f);
	assert(damageFactor(Flick, Attacker::PikminPart) == 0.2f);
	assert(damageFactor(Wait, Attacker::PikminPart) == 1.0f);
	assert(damageFactor(Rolling, Attacker::PikminPart, true) == 0.25f);
	assert(damageFactor(Wait, Attacker::CaptainPunch) == 0.0f);
	assert(damageFactor(Sleep, Attacker::CaptainPunch) == 0.0f); // punch is a no-op even asleep
	assert(damageFactor(Wait, Attacker::Earthquake) == 0.0f);    // purple quake immune

	// Hit counter rise forces Damage through wait/sleep transitions (above),
	// flick joint routing, Queen.cpp:324-345.
	assert(flickEffect(Part::Nose) == FlickEffect::Flick);
	assert(flickEffect(Part::Head) == FlickEffect::Flick);
	assert(flickEffect(Part::Bod1) == FlickEffect::Flick);
	assert(flickEffect(Part::Bod5) == FlickEffect::FlickReversed);
	assert(flickEffect(Part::Other) == FlickEffect::ShakeOff);
	assert(ShakeKnockback == 300.0f && ShakeDamage == 1.0f);

	// Shake-off thresholds blows 30/35/45/50, sticking 5/10/15.
	assert(isStartFlick(30, 0, 0) && !isStartFlick(29, 0, 0));
	assert(isStartFlick(0, 5, 0) && !isStartFlick(0, 4, 0));
	assert(isStartFlick(35, 0, 1) && !isStartFlick(34, 0, 1));
	assert(isStartFlick(0, 10, 1));
	assert(isStartFlick(45, 0, 2) && isStartFlick(0, 15, 2));
	assert(isStartFlick(50, 0, 3) && !isStartFlick(49, 0, 3));
	assert(isStartFlick(50, 0, 9)); // tier clamps at the top row

	// Pool hysteresis 50/25, Queen.cpp:469-479.
	assert(!larvaRoom(50, true));
	assert(larvaRoom(25, false));
	assert(larvaRoom(37, true));
	assert(!larvaRoom(37, false));
	assert(MaxBirths == 50 && MinBirths == 25 && LarvaPoolMax == 50);

	// Birth interval 2.0 s disc.
	assert(birthDue(true, true, 2.1f, BirthIntervalSec));
	assert(!birthDue(true, true, 2.0f, BirthIntervalSec));
	assert(!birthDue(false, true, 9.0f, BirthIntervalSec));
	assert(!birthDue(true, false, 9.0f, BirthIntervalSec));
	assert(BirthIntervalSec == 2.0f && LaunchSpeed == 50.0f);

	// Variants: f_01 no larvae + HP 3300 + easy first roll; l_02 crash rocks
	// recorded (disabled downstream). Queen.cpp:85-105, 355-410.
	const VariantInfo f01 = variantInfo(Variant::F01);
	assert(f01.noLarvae && f01.easyFirstRoll && f01.health == 3300.0f);
	const VariantInfo l02 = variantInfo(Variant::L02);
	assert(!l02.noLarvae && l02.crashRocks == 7 && l02.rockLifetimeSec == 30.0f);
	const VariantInfo base = variantInfo(Variant::Default);
	assert(!base.noLarvae && base.health == 5000.0f);
	assert(variantInfo(Variant::Default, true).noLarvae); // zukan mode

	// yaw 0 faces +z; left roll goes +x, right roll goes -x.
	assert(easyRollLeft(0.0f, -1.0f, 0.5f));  // captain to -x: rolling left (+x) moves away
	assert(!easyRollLeft(0.0f, 1.0f, 0.5f));  // captain to +x: rolling right (-x) moves away

	// Rolling press geometry constants, Queen.cpp:287-318.
	assert(AttackRadius == 150.0f && AttackHitAngleDeg == 25.0f && PressDamage == 10.0f && PressHeightBand == 50.0f);

	// Baby minimal slice.
	assert(babyPressKills(3, false) && babyPressKills(4, false));
	assert(!babyPressKills(2, false) && !babyPressKills(3, true));
	assert((babyMoveStep(10.0f, 45.0f, 40.0f, 100.0f, 30.0f, true) == std::pair<float, bool>(40.0f, false)));
	assert(babyMoveStep(90.0f, 45.0f, 40.0f, 100.0f, 30.0f, true).first == 10.0f); // quarter speed turning
	assert(babyMoveStep(10.0f, 45.0f, 40.0f, 25.0f, 30.0f, true).second);
	assert(babyMoveStep(0.0f, 45.0f, 40.0f, 10.0f, 30.0f, false).first == 0.0f);
	assert(babyBornNext(false, 5.0f) == -1);
	assert(babyBornNext(true, 5.0f) == 3);
	assert(babyBornNext(true, 0.0f) == 0);
	assert(BabyHealth == 5.0f && BabySpeed == 40.0f && BabySight == 800.0f);

	// Invalid numbers are rejected.
	bool threw = false;
	try {
		sleepNext(std::nanf(""), false, false, false, false);
	} catch (const std::runtime_error&) { threw = true; }
	assert(threw);
	threw = false;
	try {
		larvaRoom(-1, true);
	} catch (const std::runtime_error&) { threw = true; }
	assert(threw);

	// P2_QUEEN_ACTOR_1 strict config validation.
	const std::string clips = "P2_QUEEN_ACTOR_1\n11\n"
	                          "30 dead 140 2 0 139\n30 sleep 210 2 0 209\n30 wait1 30 2 0 29\n30 damage 50 2 0 49\n"
	                          "30 flick 60 2 0 59\n30 rolling_l 110 2 0 109\n30 rolling_r 110 2 0 109\n30 born 28 2 0 27\n"
	                          "31 born 35 2 0 34\n31 move 12 2 0 11\n31 dead 100 2 0 99\n";
	auto parse = [](const std::string& s) {
		std::istringstream in(s);
		return readActorConfig(in);
	};
	{
		const std::string good = clips + "2\n230010 default 1 -120 30 1800 0\n230011 f_01 0 150 30 1500 90\n";
		const ActorConfig cfg = parse(good);
		assert(cfg.clips.size() == 11 && cfg.placements.size() == 2);
		assert(cfg.placements[0].larvae && cfg.placements[0].variant == Variant::Default);
		assert(cfg.placements[1].variant == Variant::F01 && !cfg.placements[1].larvae);
		assert(cfg.clip(30, "rolling_l") && cfg.clip(31, "move") && !cfg.clip(31, "attack"));
		assert(cfg.clip(30, "sleep")->index(118.0f) == 1);
	}
	auto reject = [&](const std::string& s) {
		bool bad = false;
		try {
			parse(s);
		} catch (const std::runtime_error&) { bad = true; }
		assert(bad);
	};
	reject(clips + "1\n230010 default 1 0 0 0 0\njunk");
	reject(clips + "1\n230010 default 1 0 0 0 0\n230010 default 1 0 0 0 0\n"); // trailing garbage
	reject(clips + "2\n230010 default 1 0 0 0 0\n230010 default 1 1 1 1 1\n"); // duplicate id
	reject(clips + "1\n4294967296 default 1 0 0 0 0\n");                        // id overflow
	reject(clips + "1\n230010 f_01 1 0 0 0 0\n");                               // f_01 forbids larvae
	reject(clips + "1\n230010 x_99 1 0 0 0 0\n");                               // unknown variant
	reject(clips + "1\n230010 default 2 0 0 0 0\n");                            // larvae flag not 0/1
	reject(clips + "1\n230010 default 1 nan 0 0 0\n");                          // non-finite xyz
	reject(clips + "1\n230010 default 1 100001 0 0 0\n");                       // xyz bound
	reject(clips + "1\n230010 default 1 0 0 0 361\n");                          // yaw bound
	// Larvae placements require the Baby clip set.
	{
		const std::string nobaby = "P2_QUEEN_ACTOR_1\n8\n"
		                           "30 dead 140 2 0 139\n30 sleep 210 2 0 209\n30 wait1 30 2 0 29\n30 damage 50 2 0 49\n"
		                           "30 flick 60 2 0 59\n30 rolling_l 110 2 0 109\n30 rolling_r 110 2 0 109\n30 born 28 2 0 27\n";
		reject(nobaby + "1\n230010 default 1 0 0 0 0\n");
		const ActorConfig ok = parse(nobaby + "1\n230010 default 0 0 0 0 0\n");
		assert(ok.placements.size() == 1 && !ok.placements[0].larvae);
	}
	// Missing Queen clips fail closed.
	reject("P2_QUEEN_ACTOR_1\n1\n30 dead 140 2 0 139\n1\n230010 default 0 0 0 0 0\n");
	reject("P2_QUEEN_ACTOR_2\n1\n30 dead 140 2 0 139\n1\n230010 default 0 0 0 0 0\n"); // wrong version
	reject("P2_QUEEN_ACTOR_1\n2\n30 dead 140 2 0 139\n30 dead 140 2 0 139\n1\n230010 default 0 0 0 0 0\n"); // dup clip
	reject("P2_QUEEN_ACTOR_1\n1\n30 carry 40 2 0 39\n1\n230010 default 0 0 0 0 0\n");                     // carry excluded
	reject("P2_QUEEN_ACTOR_1\n1\n30 dead 140 2 139 0\n1\n230010 default 0 0 0 0 0\n");                    // unsorted frames
	reject("P2_QUEEN_ACTOR_1\n1\n30 dead 140 2 0 140\n1\n230010 default 0 0 0 0 0\n");                    // frame overflow

	std::puts("pikmin2_queen_policy PASS");
	return 0;
}
