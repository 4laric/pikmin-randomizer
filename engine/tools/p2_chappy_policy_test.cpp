// Isolated fixtures for pc_p2_chappy_policy.h (Chappy family, inst-chappy #871).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_chappy_policy_test.cpp -o p2_chappy_policy_test.exe
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include "pc_p2_chappy_policy.h"

using namespace p2chappy;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_chappy_policy_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}
static bool near(float a, float b, float eps = 1e-4f) { return a > b - eps && a < b + eps; }

int main()
{
    // --- retail-audited family table (US GPVE01 enemyparm.txt) ---
    require(sizeof(kSpecies) / sizeof(kSpecies[0]) == 7, "seven Chappy-family species");
    const SpeciesParams* red = speciesForSource(2);
    require(red && red->health == 750.0f, "Chappy retail life 750");
    require(red && red->host == 4, "Chappy rides the adult Spotty vehicle");
    require(speciesForSource(33)->health == 1400.0f, "FireChappy retail life 1400");
    require(speciesForSource(35)->health == 1200.0f, "KumaChappy retail life 1200");
    require(speciesForSource(43)->health == 650.0f, "YellowChappy retail life 650");
    require(speciesForSource(53)->health == 1300.0f, "KingChappy retail life 1300");
    require(speciesForSource(67)->health == 300.0f, "LeafChappy retail life 300");
    require(speciesForSource(76)->health == 500.0f, "KumaKochappy retail life 500");
    require(speciesForSource(67)->host == 3, "LeafChappy rides the dwarf vehicle");
    require(speciesForSource(76)->host == 31, "KumaKochappy rides the dwarf Bulbear vehicle");
    require(speciesForSource(35)->host == 32, "KumaChappy rides the Spotty Bulbear vehicle");
    require(speciesForSource(999) == nullptr, "unknown source has no row");
    require(speciesForEnum("Chappy") == red, "enum lookup agrees with source lookup");
    require(speciesForEnum("Bogus") == nullptr, "unknown enum has no row");
    // Every row carries a positive health, speed, sight and attack envelope.
    for (const auto& row : kSpecies) {
        require(row.health > 0.0f && row.moveSpeed > 0.0f && row.sight > 0.0f, "positive body parms");
        require(row.attackRange > 0.0f && row.attackDamage >= 0.0f, "sane attack envelope");
        require(row.host == 3 || row.host == 4 || row.host == 31 || row.host == 32, "known vehicle");
    }

    // --- per-species movement/sight/attack envelopes (runtime FSM inputs) ---
    {
        const SpeciesParams* fire = speciesForSource(33);
        require(fire && near(fire->moveSpeed, 110.0f) && near(fire->sight, 500.0f), "fire move/sight");
        require(near(fire->attackRange, 75.0f) && near(fire->attackDamage, 10.0f), "fire attack envelope");
        const SpeciesParams* kuma = speciesForSource(35);
        require(kuma && near(kuma->moveSpeed, 100.0f) && near(kuma->sight, 500.0f), "kuma move/sight");
        const SpeciesParams* yellow = speciesForSource(43);
        require(yellow && near(yellow->moveSpeed, 90.0f), "yellow move speed");
        const SpeciesParams* king = speciesForSource(53);
        require(king && near(king->moveSpeed, 45.0f) && near(king->attackRange, 130.0f), "king slow wide attack");
        require(near(king->attackAngle, 30.0f), "king attack angle");
        const SpeciesParams* leaf = speciesForSource(67);
        require(leaf && near(leaf->sight, 300.0f) && near(leaf->attackRange, 40.0f), "leaf short sight/range");
        const SpeciesParams* kumako = speciesForSource(76);
        require(kumako && near(kumako->sight, 150.0f) && near(kumako->attackRange, 35.0f), "kumako dwarf envelope");
        require(near(kumako->attackHitRange, 38.0f), "kumako hit range");
        // Poison (white-pikmin) proper values per family block.
        require(near(red->poisonDamage, 750.0f) && near(fire->poisonDamage, 300.0f), "adult poison proper");
        require(near(king->poisonDamage, 200.0f) && near(leaf->poisonDamage, 500.0f), "king/leaf poison proper");
    }

    // --- source StateID orders (runtime FSM states) ---
    {
        require(ADULT_TURN == 0 && ADULT_DEAD == 1 && ADULT_FLICK == 2 && ADULT_WALK == 3, "adult turn/dead/flick/walk");
        require(ADULT_ATTACK == 4 && ADULT_TURN_TO_HOME == 5 && ADULT_GO_HOME == 6 && ADULT_SLEEP == 7, "adult attack/home/sleep");
        require(ADULT_COUNT == 8, "adult state count");
    }

    // --- adult attack event frames (chappy/enemyanimmgr.txt) ---
    require(AttackBiteFrame == 10, "bite frame 10");
    require(AttackSwallowFrame == 33, "swallow frame 33");
    require(AttackEndFrame == 40, "end frame 40");
    require(DwarfAttackEatFrame == 8 && DwarfAttackSwallowFrame == 88, "dwarf eat/swallow frames");

    // --- sidecar policy parse (P2_CHAPPY_POLICY_1) ---
    {
        Params out;
        std::istringstream bad("P2_CHAPPY_POLICY_0 health 750");
        require(!parseConfig(bad, out), "wrong magic rejected");
        std::istringstream good("P2_CHAPPY_POLICY_1 health 750");
        require(parseConfig(good, out) && near(out.health, 750.0f), "health parses");
        std::istringstream dup("P2_CHAPPY_POLICY_1 health 750 health 750");
        require(!parseConfig(dup, out), "duplicate key rejected");
        std::istringstream unknown("P2_CHAPPY_POLICY_1 speed 10");
        require(!parseConfig(unknown, out), "unknown key rejected");
        std::istringstream zero("P2_CHAPPY_POLICY_1 health 0");
        require(!parseConfig(zero, out), "non-positive health rejected");
        std::istringstream empty("P2_CHAPPY_POLICY_1");
        require(parseConfig(empty, out) && near(out.health, 750.0f), "empty config keeps retail default");
    }

    // --- per-actor health registry ---
    {
        Health health;
        int a, b;
        require(!health.contains(&a), "unbound actor absent");
        require(health.life(&a, 11.0f) == 11.0f, "unbound actor falls back");
        require(health.bind(&a, 750.0f), "bind succeeds");
        require(!health.bind(&a, 750.0f), "double bind refused");
        require(!health.bind(&b, -1.0f), "non-positive health refused");
        require(health.bind(&b, 1400.0f), "second actor binds its own health");
        require(health.life(&a, 0.0f) == 750.0f, "per-actor health stored");
        require(health.life(&b, 0.0f) == 1400.0f, "second actor keeps its own health");
        require(!health.isDead(&a), "fresh actor alive");
        require(health.markDead(&a), "first death marks");
        require(!health.markDead(&a), "second death mark refused");
        require(health.isDead(&a) && !health.isDead(&b), "death is per-actor");
        health.forget(&a);
        require(!health.contains(&a) && !health.isDead(&a), "forget clears binding and death");
    }

    std::printf("PASS p2_chappy_policy_test checks=%d\n", gChecks);
    return 0;
}
