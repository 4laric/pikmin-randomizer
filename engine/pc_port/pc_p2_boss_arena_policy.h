#pragma once
// P2 boss arenas (owner ruling 2026-09-29): P2 bosses are placed only in the
// P1 boss arenas and replace the P1 boss there. Engine-free policy table.
//
// The seed (root randomizer/p2_boss_arenas.py, docs/PIKMIN2_ADMITTED_PLACEMENT.json
// "arenas") binds a chosen arena's primary spawn uid to the P2 boss through the
// ordinary ENEMY_P2 line. This header carries what the wire cannot: the other
// day-file generators of the same encounter, re-keyed to the primary so the
// boss keeps one generator token (`alias`); the P1 boss generators that share
// an arena with the spawn generator and must stay empty while the arena holds
// a P2 boss (`suppress`); and the full
// arena generator set so the read-only clearance probe can measure every arena,
// including the protected ones (ship-part holders, goal boss) that are not yet
// eligible. tests/test_p2_boss_arenas.py pins this table against the root
// catalogue; keep the two in sync.
//
// Generator uids are the spawn-slot catalogue ids (crc32 of
// "pikrando-spawn/<stage>/<file>@<offset>", randomizer/spawn_data.py).
namespace p2bossarena {

struct Alias {
    unsigned uid;      // same encounter on another day file
    unsigned primary;  // arena primary spawn uid it is re-keyed to
};

// Impact Goolix: practice/{10..28}.gen@1764 are the 8.gen@1764 encounter on
// later even day files.
static const Alias kAlias[] = {
    {2380628347u, 4019261003u}, {2299547974u, 4019261003u}, {2215518465u, 4019261003u},
    {2163994940u, 4019261003u}, {2654126479u, 4019261003u}, {336062330u, 4019261003u},
    {284309319u, 4019261003u},  {502023936u, 4019261003u},  {421107517u, 4019261003u},
    {131114894u, 4019261003u},
};

struct Suppress {
    unsigned uid;      // P1 boss generator left empty
    unsigned primary;  // arena spawn generator whose binding empties it
};

// Hope snagret pit: 0-29.gen@3264 (BoxSnake) is the spawn generator (it sits on
// the carry-route graph); its pit mate 0-29.gen@3428 (Snake) stays empty while
// the pit holds a P2 boss.
static const Suppress kSuppress[] = {
    {2026735859u, 295337326u},
};

// Every P1 boss-arena generator (spawn, suppressed and protected), for the
// P2_BOSS_ARENA_PROBE clearance measurement. Not a placement permission.
static const unsigned kArenaUids[] = {
    // impact_goolix: GENBOSS_Slime, one generator per even day file (8..28.gen@1764)
    4019261003u, 2380628347u, 2299547974u, 2215518465u, 2163994940u, 2654126479u,
    336062330u, 284309319u, 502023936u, 421107517u, 131114894u,
    // hope_snagret_pit: 0-29.gen@3264 BoxSnake (spawn), 0-29.gen@3428 Snake (suppressed)
    295337326u, 2026735859u,
    // hope_snagret_part: init.gen@3974 BoxSnake holding a ship part (protected)
    4260179239u,
    // navel_beady_long_legs: init.gen@5307 Spider holding a ship part (protected)
    304372265u,
    // navel_puffstool: init.gen@5471 TEKI_Kinoko holding uf09 (protected)
    2974383966u,
    // spring_cannon_beetle: init.gen@4834 TEKI_Beatle holding ust1 (protected)
    2903640892u,
    // last_emperor: init.gen@976 King, ship part + Emperor goal (protected)
    3759070123u,
};

// Returns the arena primary uid `uid` is re-keyed to, or 0.
inline unsigned aliasPrimary(unsigned uid)
{
    for (const Alias& row : kAlias)
        if (row.uid == uid) return row.primary;
    return 0;
}

// Returns the arena spawn uid that suppresses `uid`, or 0.
inline unsigned suppressPrimary(unsigned uid)
{
    for (const Suppress& row : kSuppress)
        if (row.uid == uid) return row.primary;
    return 0;
}

inline bool isArenaUid(unsigned uid)
{
    for (unsigned value : kArenaUids)
        if (value == uid) return true;
    return false;
}

// Engine vehicle for a P2 boss born from a P1 boss generator. The P1 boss has
// no teki type to fall back on, so an identity without a static campaign host
// rides TEKI_Swallow (4), the vehicle every current P2 boss family uses
// (30 Queen, 73 BigTreasure, 94 DangoMushi, 66 Houdai).
template <typename HostFn>
inline int hostFor(unsigned source, HostFn hostType)
{
    const int host = hostType(source, -1, false);
    return host >= 0 ? host : 4;
}

} // namespace p2bossarena
