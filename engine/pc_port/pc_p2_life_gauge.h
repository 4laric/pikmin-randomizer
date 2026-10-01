#pragma once
// Shared P2 life-gauge policy (health bars over campaign P2 enemies).
//
// Source: Pikmin 2 EnemyBase::doGetLifeGaugeParam (pikmin2-research
// src/plugProjectYamashitaU/enemyBase.cpp) places the gauge at
//   y = mPosition.y + getParms().mLifeMeterHeight()
// and mLifeMeterHeight is general parameter fp27 ("life height", include/Game/
// EnemyParmsBase.h, default 50). The retail value per species is in
// enemy/parm/enemyParms.szs <species>/enemyparm.txt on the US GPVE01 disc.
// The table below is that fp27 for every admitted P2 species, extracted with
// the disc reader in experimental/pikmin2_assets.py (root repo). Species 101
// (UmiMushiBlind) has no enemyparm of its own and reuses UmiMushi (71).
//
// Header-only and engine-free so tests/p2_life_gauge_test.cpp can check it.
namespace p2lifegauge {

struct Row {
    unsigned sourceId;
    float lifeMeterHeight; // retail fp27
};

// Sorted by source id is not required; lookups are linear over 45 rows.
static const Row kRows[] = {
    {44, 50.0f}, // BlueKochappy
    {54, 70.0f}, // Miulin
    {59, 75.0f}, // FireOtakara
    {60, 75.0f}, // WaterOtakara
    {61, 75.0f}, // GasOtakara
    {62, 75.0f}, // ElecOtakara
    {23, 50.0f}, // Sarai
    {79, 50.0f}, // Sokkuri
    {2, 90.0f}, // Chappy
    {33, 110.0f}, // FireChappy
    {35, 90.0f}, // KumaChappy
    {43, 90.0f}, // YellowChappy
    {53, 90.0f}, // KingChappy
    {67, 90.0f}, // LeafChappy
    {76, 50.0f}, // KumaKochappy
    {12, 50.0f}, // UjiA
    {13, 50.0f}, // UjiB
    {14, 50.0f}, // Tobi
    {28, 50.0f}, // ElecBug
    {94, 90.0f}, // DangoMushi
    {68, 50.0f}, // TamagoMushi
    {17, 70.0f}, // Frog
    {18, 70.0f}, // MaroFrog
    {24, 50.0f}, // Tank
    {75, 50.0f}, // Kabuto
    {56, 75.0f}, // Damagumo
    {63, 20.0f}, // Jigumo
    {69, 75.0f}, // BigFoot
    {66, 115.0f}, // Houdai (Man-at-Legs): enemyparm fp27 115, fp00 2800 (#1012)
    {34, 50.0f}, // SnakeCrow
    {70, 50.0f}, // SnakeWhole
    {65, 50.0f}, // Imomushi
    {71, 100.0f}, // UmiMushi
    {101, 100.0f}, // UmiMushiBlind
    {25, 50.0f}, // Wtank
    {15, 50.0f}, // Armor
    {78, 90.0f}, // MiniHoudai
    {73, 75.0f}, // BigTreasure
    {32, 50.0f}, // Demon
    {38, 45.0f}, // PanModoki
    {40, 45.0f}, // OoPanModoki
    {41, 50.0f}, // Fuefuki
    {58, 50.0f}, // BombSarai
    {57, 70.0f}, // Kurage
    {72, 10.0f}, // OniKurage
    {30, 50.0f}, // Queen
    {31, 50.0f}, // Baby (Bulborb Larva), fp27 from baby/enemyparm.txt (#1042)
    // Wave-3 mechanics species (claude/p2-wave3-mechanics, not yet in the pool).
    {26, 50.0f}, // Catfish
    {27, 50.0f}, // Tadpole (Wogpole)
    {84, 90.0f}, // Hana (Bulbmin flower)
    {93, 75.0f}, // BombOtakara
};

inline constexpr float kDefaultHeight = 50.0f; // EnemyParmsBase fp27 default

// Retail fp27 for a source id, or fallback when the species is not in the table.
inline float lifeMeterHeight(unsigned sourceId, float fallback)
{
    for (const Row& r : kRows)
        if (r.sourceId == sourceId) return r.lifeMeterHeight;
    return fallback;
}

// Species whose P1 host vehicle keeps TEKIOPT_LifeGaugeVisible cleared (audit:
// UjiA/UjiB/Tobi ride the Sheargrub host, whose option is off), so the wheel is
// driven from the targetable state instead: shown while the actor is Atari,
// hidden while it is underground (P2 UjiA hides with EB_Untargetable).
inline bool gaugeFollowsTargetable(unsigned sourceId)
{
    return sourceId == 12 || sourceId == 13 || sourceId == 14;
}

inline bool hasHeight(unsigned sourceId)
{
    for (const Row& r : kRows)
        if (r.sourceId == sourceId) return true;
    return false;
}

// P2 draws the gauge only for a live enemy that has been damaged
// (EB_LifegaugeVisible set on damage); P1's LifeGauge::updValue does the same
// (fade in when the health ratio drops below 1). Kept as a pure predicate so
// the audit marker and the test agree.
inline bool shouldShow(float health, float maxHealth, bool dead)
{
    return !dead && maxHealth > 0.0f && health > 0.0f && health < maxHealth;
}

} // namespace p2lifegauge
