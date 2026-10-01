#include "pc_p2_egg_hazard.h"

#include <cassert>
#include <cmath>
#include <limits>

namespace {
constexpr float kPi = 3.14159265358979323846f;

struct Script {
    float f[8] = {};
    int fcount = 0;
    int fpos = 0;
    int i[8] = {};
    int icount = 0;
    int ipos = 0;

    void addF(float v) { f[fcount++] = v; }
    void addI(int v) { i[icount++] = v; }
};

float randFloat(void* opaque)
{
    Script& s = *static_cast<Script*>(opaque);
    return s.f[s.fpos++];
}

int randInt(void* opaque, int count)
{
    Script& s = *static_cast<Script*>(opaque);
    const int v = s.i[s.ipos++];
    return count > 0 ? (v % count) : 0;
}

bool near(float actual, float expected, float epsilon = 0.001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

P2EggConfig discConfig()
{
    P2EggConfig config;
    config.singleNectarChance = 0.5f;  // fp01 disc
    config.doubleNectarChance = 0.35f; // fp02 disc
    config.mititesChance = 0.05f;      // fp03 disc
    config.spicyChance = 0.05f;        // fp04 disc
    config.bitterChance = 0.05f;       // fp05 disc
    config.checkHasSpray = false;
    config.health = 50.0f;             // general fp00 disc
    return config;
}

P2Egg breakEgg(const P2EggConfig& config, Script& script)
{
    P2Egg egg;
    egg.reset(config);
    assert(egg.birth(true));
    egg.damage(config.health);
    assert(egg.update(randFloat, &script, randInt, &script));
    return egg;
}

P2EggDropType typeForRoll(float roll, bool checkSpray = false, int forced = 0,
                          bool firstSpicy = false, bool firstBitter = false)
{
    P2EggConfig config = discConfig();
    config.checkHasSpray = checkSpray;
    config.forcedDropType = forced;
    config.firstSpicySprayMade = firstSpicy;
    config.firstBitterSprayMade = firstBitter;
    Script script;
    script.addF(roll);
    script.addF(0.0f); // double-nectar angle / mitite face dir
    script.addI(1);    // pellet colour
    P2Egg egg = breakEgg(config, script);
    return egg.drop().type;
}

void testTypeSelection()
{
    assert(typeForRoll(0.10f) == P2EggDropType::SingleNectar);
    assert(typeForRoll(0.60f) == P2EggDropType::DoubleNectar);
    assert(typeForRoll(0.88f) == P2EggDropType::Mitites);
    assert(typeForRoll(0.92f) == P2EggDropType::Spicy);
    assert(typeForRoll(0.97f) == P2EggDropType::Bitter);
    // Disc chances sum to 1.0, so the top band still catches the highest roll.
    assert(typeForRoll(0.9999f) == P2EggDropType::Bitter);
    // Cumulative bands below 1.0 fall through to the source default.
    P2EggConfig sparse = discConfig();
    sparse.singleNectarChance = 0.1f;
    sparse.doubleNectarChance = 0.0f;
    sparse.mititesChance = 0.0f;
    sparse.spicyChance = 0.0f;
    sparse.bitterChance = 0.0f;
    Script script;
    script.addF(0.5f);
    P2Egg egg = breakEgg(sparse, script);
    assert(egg.drop().type == P2EggDropType::SingleNectar);
}

void testSpawnCommands()
{
    // One pellet, colour from randInt(3), base velocity.
    {
        P2EggConfig config = discConfig();
        config.forcedDropType = 1;
        Script script;
        script.addF(0.0f);
        script.addI(2);
        P2Egg egg = breakEgg(config, script);
        const P2EggDrop& d = egg.drop();
        assert(d.type == P2EggDropType::OnePellets);
        assert(d.itemCount == 1);
        assert(d.items[0].kind == P2EggSpawnKind::PelletOne);
        assert(d.items[0].pelletColor == 2);
        assert(near(d.items[0].velocity.y, 250.0f));
        assert(near(d.positionOffsetY, 2.0f));
    }
    // Five pellets.
    {
        P2EggConfig config = discConfig();
        config.forcedDropType = 2;
        Script script;
        script.addF(0.0f);
        script.addI(0);
        P2Egg egg = breakEgg(config, script);
        assert(egg.drop().items[0].kind == P2EggSpawnKind::PelletFive);
    }
    // Single nectar.
    {
        P2EggConfig config = discConfig();
        config.forcedDropType = 3;
        Script script;
        script.addF(0.0f);
        P2Egg egg = breakEgg(config, script);
        const P2EggDrop& d = egg.drop();
        assert(d.type == P2EggDropType::SingleNectar);
        assert(d.items[0].kind == P2EggSpawnKind::Nectar);
        assert(near(d.items[0].velocity.x, 0.0f) && near(d.items[0].velocity.y, 250.0f)
               && near(d.items[0].velocity.z, 0.0f));
    }
    // Double nectar: two items at theta 0 and PI for angle 0.
    {
        P2EggConfig config = discConfig();
        config.forcedDropType = 4;
        Script script;
        script.addF(0.0f); // angle = TAU * 0
        P2Egg egg = breakEgg(config, script);
        const P2EggDrop& d = egg.drop();
        assert(d.type == P2EggDropType::DoubleNectar);
        assert(d.itemCount == 2);
        assert(near(d.items[0].velocity.x, 0.0f) && near(d.items[0].velocity.z, 50.0f));
        assert(near(d.items[1].velocity.x, 0.0f) && near(d.items[1].velocity.z, -50.0f));
    }
    // Mitites: group of 10 with y=200, nectar fallback flagged; face-dir roll consumed.
    {
        P2EggConfig config = discConfig();
        config.forcedDropType = 5;
        Script script;
        script.addF(0.0f /*roll*/);
        script.addF(0.25f /*face dir*/);
        P2Egg egg = breakEgg(config, script);
        const P2EggDrop& d = egg.drop();
        assert(d.type == P2EggDropType::Mitites);
        assert(d.items[0].kind == P2EggSpawnKind::MititeGroup);
        assert(d.items[0].mititeCount == 10);
        assert(near(d.items[0].velocity.y, 200.0f));
        assert(d.mititeFallbackToNectar);
    }
    // Spicy / Bitter sprays.
    {
        P2EggConfig config = discConfig();
        config.forcedDropType = 6; // EGGDROP_Spicy
        config.checkHasSpray = false;
        Script script;
        script.addF(0.0f);
        P2Egg spicy = breakEgg(config, script);
        assert(spicy.drop().items[0].kind == P2EggSpawnKind::Spicy);

        config.forcedDropType = 7; // EGGDROP_Bitter
        Script script2;
        script2.addF(0.0f);
        P2Egg bitter = breakEgg(config, script2);
        assert(bitter.drop().items[0].kind == P2EggSpawnKind::Bitter);
    }
}

void testForcedAndSprayGate()
{
    // Forced override bypasses the roll.
    assert(typeForRoll(0.10f, false, 1) == P2EggDropType::OnePellets);
    assert(typeForRoll(0.9999f, false, 2) == P2EggDropType::FivePellets);
    // Spicy gated on the first-spray demo flag.
    assert(typeForRoll(0.0f, true, 6, false, false) == P2EggDropType::SingleNectar);
    assert(typeForRoll(0.0f, true, 6, true, false) == P2EggDropType::Spicy);
    // Bitter uses its own flag.
    assert(typeForRoll(0.0f, true, 7, false, false) == P2EggDropType::SingleNectar);
    assert(typeForRoll(0.0f, true, 7, false, true) == P2EggDropType::Bitter);
}

void testBounce()
{
    // Non-falling, non-drop-group Egg ignores a floor bounce.
    P2Egg grounded;
    grounded.reset(discConfig());
    assert(grounded.birth(false));
    assert(!grounded.bounce());
    assert(near(grounded.health(), 50.0f));
    assert(!grounded.lifegaugeVisible());

    // Released capture (mIsFalling) zeroes health and exposes the gauge.
    assert(grounded.damage(0.0f) == 50.0f);
    grounded.onEndCapture();
    assert(grounded.falling());
    assert(grounded.bounce());
    assert(near(grounded.health(), 0.0f));
    assert(grounded.lifegaugeVisible());

    // Drop-group Egg breaks on first floor contact.
    P2Egg dropGroup;
    dropGroup.reset(discConfig());
    assert(dropGroup.birth(true));
    assert(dropGroup.bounce());
    assert(near(dropGroup.health(), 0.0f));
}

void testContact()
{
    P2Egg egg;
    egg.reset(discConfig());
    assert(egg.birth(true));

    // Teki contact does not break the Egg.
    assert(!egg.contact(false, true));
    assert(near(egg.health(), 50.0f));
    // Null colliding creature is ignored.
    assert(!egg.contact(true, false));
    // Non-Teki, non-null contact breaks it.
    assert(egg.contact(false, false));
    assert(near(egg.health(), 0.0f));
    assert(egg.lifegaugeVisible());

    // Non-drop-group Egg is not broken by contact.
    P2Egg normal;
    normal.reset(discConfig());
    assert(normal.birth(false));
    assert(!normal.contact(false, false));
    assert(near(normal.health(), 50.0f));
}

void testCaptureFlags()
{
    P2Egg egg;
    egg.reset(discConfig());
    assert(egg.birth(true));
    egg.onStartCapture();
    assert(egg.constrained() && egg.invulnerable() && !egg.cullable());
    egg.onEndCapture();
    assert(!egg.constrained() && egg.falling() && egg.cullable());
}

void testDestruction()
{
    P2Egg egg;
    egg.reset(discConfig());
    assert(egg.birth(true));
    assert(egg.phase() == P2EggPhase::Wait);

    // Health above zero: no break.
    Script script;
    script.addF(0.1f);
    assert(!egg.update(randFloat, &script, randInt, &script));
    assert(egg.phase() == P2EggPhase::Wait);

    // Damage to zero then a single break with a drop.
    assert(near(egg.damage(20.0f), 30.0f));
    assert(near(egg.damage(40.0f), -10.0f));
    assert(!egg.hasDrop());
    assert(egg.update(randFloat, &script, randInt, &script));
    assert(egg.phase() == P2EggPhase::Broken);
    assert(egg.hasDrop());
    assert(egg.drop().type == P2EggDropType::SingleNectar);
    // Break is exactly once.
    assert(!egg.update(randFloat, &script, randInt, &script));
    assert(!egg.isAlive());
}

void testInvalidInput()
{
    P2EggConfig badHealth = discConfig();
    badHealth.health = 0.0f;
    P2Egg egg;
    egg.reset(badHealth);
    assert(!egg.birth(true));

    P2EggConfig badForce = discConfig();
    badForce.forcedDropType = 8;
    P2Egg egg2;
    egg2.reset(badForce);
    assert(!egg2.birth(true));

    P2EggConfig badChance = discConfig();
    badChance.spicyChance = std::numeric_limits<float>::quiet_NaN();
    P2Egg egg3;
    egg3.reset(badChance);
    assert(!egg3.birth(true));
}
} // namespace

int main()
{
    testTypeSelection();
    testSpawnCommands();
    testForcedAndSprayGate();
    testBounce();
    testContact();
    testCaptureFlags();
    testDestruction();
    testInvalidInput();
    return 0;
}
