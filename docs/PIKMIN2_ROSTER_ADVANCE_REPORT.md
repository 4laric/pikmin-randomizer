# P2 roster advance report (dry run)

Deny-by-default admission dry-run across every lane handoff on
`claude/p2-deepseek-wave`. Per identity: the gates the handoff(s) would
advance, the PASSes refused and why (`uncited` / `injected` / `shared table`),
and the gates still blocking `admission_requirements`. Nothing is admitted and
nothing is written (dry run).

Regenerate with:

    py -3.12 scripts/generate_p2_advance_report.py --branch claude/p2-deepseek-wave

## Handoffs read

- PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md: 2 Chappy, 9 Kogane, 10 Wealthy, 11 Fart, 12 UjiA, 13 UjiB, 15 Armor, 16 Qurione, 17 Frog, 18 MaroFrog, 19 Rock, 23 Sarai, 24 Tank, 26 Catfish, 27 Tadpole, 28 ElecBug, 30 Queen, 32 Demon, 34 SnakeCrow, 38 PanModoki, 40 OoPanModoki, 41 Fuefuki, 44 BlueKochappy, 45 YellowKochappy, 53 KingChappy, 54 Miulin, 55 Hanachirashi, 56 Damagumo, 57 Kurage, 58 BombSarai, 59 FireOtakara, 60 WaterOtakara, 61 GasOtakara, 62 ElecOtakara, 63 Jigumo, 65 Imomushi, 66 Houdai, 68 TamagoMushi, 69 BigFoot, 70 SnakeWhole, 72 OniKurage, 73 BigTreasure, 75 Kabuto, 78 MiniHoudai, 79 Sokkuri, 84 Hana, 93 BombOtakara, 94 DangoMushi, 95 Rkabuto, 96 Fkabuto, 97 FminiHoudai, 98 Tyre, 99 BlackMan, 101 UmiMushiBlind
- PIKMIN2_LANE03_DEEPSEEK_HANDOFF.md: 44 BlueKochappy
- PIKMIN2_LANE04_DEEPSEEK_HANDOFF.md: 44 BlueKochappy, 45 YellowKochappy
- PIKMIN2_LANE05_DEEPSEEK_HANDOFF.md: 44 BlueKochappy, 45 YellowKochappy
- PIKMIN2_LANE06_DEEPSEEK_HANDOFF.md: 44 BlueKochappy, 99 BlackMan
- PIKMIN2_LANE07_DEEPSEEK_HANDOFF.md: 44 BlueKochappy, 79 Sokkuri
- PIKMIN2_LANE08_DEEPSEEK_HANDOFF.md: 84 Hana
- PIKMIN2_LANE09_DEEPSEEK_HANDOFF.md: 17 Frog, 30 Queen
- PIKMIN2_LANE10_DEEPSEEK_HANDOFF.md: 20 Hiba, 21 GasHiba, 22 ElecHiba
- PIKMIN2_LANE11_DEEPSEEK_HANDOFF.md: 67 LeafChappy
- PIKMIN2_LANE12_DEEPSEEK_HANDOFF.md: 72 OniKurage
- PIKMIN2_LANE13_DEEPSEEK_HANDOFF.md: 44 BlueKochappy
- PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md: 15 Armor, 28 ElecBug, 65 Imomushi, 68 TamagoMushi, 79 Sokkuri, 84 Hana
- PIKMIN2_LANE15_DEEPSEEK_HANDOFF.md: 16 Qurione, 37 Egg
- PIKMIN2_LANE16_DEEPSEEK_HANDOFF.md: 17 Frog, 18 MaroFrog, 26 Catfish, 27 Tadpole, 63 Jigumo, 71 UmiMushi, 101 UmiMushiBlind
- PIKMIN2_LANE17_DEEPSEEK_HANDOFF.md: 9 Kogane, 10 Wealthy
- PIKMIN2_LANE18_DEEPSEEK_HANDOFF.md: 38 PanModoki
- PIKMIN2_LANE19_DEEPSEEK_HANDOFF.md: 54 Miulin
- PIKMIN2_LANE20_DEEPSEEK_HANDOFF.md: 19 Rock, 36 Bomb, 37 Egg, 74 Stone, 75 Kabuto, 95 Rkabuto, 96 Fkabuto
- PIKMIN2_LANE21_DEEPSEEK_HANDOFF.md: 78 MiniHoudai, 97 FminiHoudai
- PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md: 59 FireOtakara, 60 WaterOtakara, 61 GasOtakara, 62 ElecOtakara, 93 BombOtakara
- PIKMIN2_LANE23_DEEPSEEK_HANDOFF.md: 3 BluePom, 4 RedPom, 5 YellowPom, 6 BlackPom, 7 WhitePom, 8 RandPom
- PIKMIN2_LANE24_DEEPSEEK_HANDOFF.md: 30 Queen, 53 KingChappy
- PIKMIN2_LANE25_DEEPSEEK_HANDOFF.md: 34 SnakeCrow, 70 SnakeWhole, 94 DangoMushi
- PIKMIN2_LANE26_DEEPSEEK_HANDOFF.md: 56 Damagumo, 66 Houdai, 69 BigFoot
- PIKMIN2_LANE27_DEEPSEEK_HANDOFF.md: 36 Bomb, 58 BombSarai
- PIKMIN2_LANE28_DEEPSEEK_HANDOFF.md: 41 Fuefuki
- PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md: 57 Kurage, 72 OniKurage
- PIKMIN2_LANE30_DEEPSEEK_HANDOFF.md: 23 Sarai
- PIKMIN2_LANE31_DEEPSEEK_HANDOFF.md: 98 Tyre, 99 BlackMan
- PIKMIN2_LANE32_DEEPSEEK_HANDOFF.md: 73 BigTreasure
- PIKMIN2_LANE33_DEEPSEEK_HANDOFF.md: 38 PanModoki, 44 BlueKochappy, 45 YellowKochappy, 54 Miulin, 59 FireOtakara

## Gates-away summary

| Gates away from admission | Identities |
|---:|---:|
| 0 | 6 |
| 1 | 5 |
| 2 | 6 |
| 3 | 4 |
| 4 | 4 |
| 5 | 5 |
| 6 | 24 |

Seedable (`source`/`variant`) identities named across handoffs: 54

## Per-identity detail

### 2 Chappy (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 9 Kogane (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE17_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, death_corpse, transport_reward, cleanup_reentry
- blocking: attacks_receivers

### 10 Wealthy (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE17_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 11 Fart (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 12 UjiA (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 13 UjiB (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 15 Armor (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md
- advances: identity_spawn
- blocking: movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 16 Qurione (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE15_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, death_corpse, cleanup_reentry
- blocking: movement_animation, attacks_receivers, transport_reward

### 17 Frog (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE09_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE16_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation
- blocking: attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 18 MaroFrog (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE16_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation
- blocking: attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 23 Sarai (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE30_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry
- blocking: (none)

### 24 Tank (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 26 Catfish (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE16_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 27 Tadpole (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE16_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 28 ElecBug (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers, death_corpse
- blocking: transport_reward, cleanup_reentry

### 30 Queen (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE09_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE24_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry
- blocking: transport_reward

### 32 Demon (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 34 SnakeCrow (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE25_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 38 PanModoki (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE18_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE33_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, attacks_receivers, transport_reward
- blocking: movement_animation, death_corpse, cleanup_reentry

### 40 OoPanModoki (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 41 Fuefuki (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE28_DEEPSEEK_HANDOFF.md
- advances: movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry
- blocking: identity_spawn

### 44 BlueKochappy (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE03_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE04_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE05_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE06_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE07_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE13_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE33_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry
- blocking: (none)

### 45 YellowKochappy (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE04_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE05_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE33_DEEPSEEK_HANDOFF.md
- advances: identity_spawn
- blocking: movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 53 KingChappy (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE24_DEEPSEEK_HANDOFF.md
- advances: attacks_receivers, death_corpse, transport_reward
- blocking: identity_spawn, movement_animation, cleanup_reentry

### 54 Miulin (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE19_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE33_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward
- blocking: cleanup_reentry

### 55 Hanachirashi (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 56 Damagumo (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE26_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 57 Kurage (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md
- advances: death_corpse, transport_reward
- blocking: identity_spawn, movement_animation, attacks_receivers, cleanup_reentry

### 58 BombSarai (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE27_DEEPSEEK_HANDOFF.md
- advances: death_corpse, transport_reward
- blocking: identity_spawn, movement_animation, attacks_receivers, cleanup_reentry

### 59 FireOtakara (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE33_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry
- blocking: (none)

### 60 WaterOtakara (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry
- blocking: (none)

### 61 GasOtakara (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry
- blocking: (none)

### 62 ElecOtakara (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry
- blocking: (none)

### 63 Jigumo (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE16_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 65 Imomushi (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md
- advances: identity_spawn
- blocking: movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 66 Houdai (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE26_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, attacks_receivers, death_corpse, cleanup_reentry
- blocking: movement_animation, transport_reward

### 67 LeafChappy (source)
- handoffs: PIKMIN2_LANE11_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 68 TamagoMushi (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers
- blocking: death_corpse, transport_reward, cleanup_reentry

### 69 BigFoot (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE26_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, attacks_receivers, death_corpse, cleanup_reentry
- blocking: movement_animation, transport_reward

### 70 SnakeWhole (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE25_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 71 UmiMushi (variant)
- handoffs: PIKMIN2_LANE16_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 72 OniKurage (source) - shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE12_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 73 BigTreasure (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE32_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 75 Kabuto (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE20_DEEPSEEK_HANDOFF.md
- advances: attacks_receivers
- blocking: identity_spawn, movement_animation, death_corpse, transport_reward, cleanup_reentry

### 78 MiniHoudai (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE21_DEEPSEEK_HANDOFF.md
- advances: movement_animation, attacks_receivers, death_corpse, transport_reward
- blocking: identity_spawn, cleanup_reentry

### 79 Sokkuri (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE07_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md
- advances: identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry
- blocking: transport_reward

### 84 Hana (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE08_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md
- advances: identity_spawn
- refused: attacks_receivers=injected, identity_spawn=uncited, movement_animation=uncited
- blocking: movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 93 BombOtakara (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md
- advances: movement_animation, death_corpse, transport_reward, cleanup_reentry
- blocking: identity_spawn, attacks_receivers

### 94 DangoMushi (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE25_DEEPSEEK_HANDOFF.md
- advances: (none)
- refused: attacks_receivers=injected, identity_spawn=uncited, movement_animation=uncited
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 95 Rkabuto (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE20_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 96 Fkabuto (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE20_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 97 FminiHoudai (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE21_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 99 BlackMan (source)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE06_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE31_DEEPSEEK_HANDOFF.md
- advances: attacks_receivers, death_corpse, transport_reward, cleanup_reentry
- blocking: identity_spawn, movement_animation

### 101 UmiMushiBlind (variant)
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE16_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry
