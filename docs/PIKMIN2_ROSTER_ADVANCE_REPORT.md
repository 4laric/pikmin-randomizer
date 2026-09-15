# P2 roster advance report (dry run)

Deny-by-default admission dry-run across every lane handoff on
`claude/p2-deepseek-wave`. Per identity: the gates the handoff(s) would
advance, the PASSes refused and why (`uncited` / `injected` / `shared table`),
and the gates still blocking `admission_requirements`. Nothing is admitted and
nothing is written (dry run).

Regenerate with:

    py -3.12 scripts/generate_p2_advance_report.py

## Gates-away summary

| Gates away from admission | Identities |
|---:|---:|
| 0 | 0 |
| 1 | 0 |
| 2 | 0 |
| 3 | 0 |
| 4 | 0 |
| 5 | 0 |
| 6 | 15 |

Seedable (`source`/`variant`) identities named across handoffs: 15

## Per-identity detail

### 15 Armor (source) — shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 41 Fuefuki (source) — shared table, excluded
- handoffs: PIKMIN2_LANE28_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 44 BlueKochappy (source) — shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE04_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE06_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE07_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE33_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 45 YellowKochappy (source) — shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE04_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 57 Kurage (source)
- handoffs: PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 58 BombSarai (source)
- handoffs: PIKMIN2_LANE27_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 59 FireOtakara (source)
- handoffs: PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md
- advances: (none)
- refused: attacks_receivers=uncited, identity_spawn=uncited, movement_animation=uncited
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 60 WaterOtakara (source) — shared table, excluded
- handoffs: PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 61 GasOtakara (source) — shared table, excluded
- handoffs: PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 62 ElecOtakara (source) — shared table, excluded
- handoffs: PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 72 OniKurage (source) — shared table, excluded
- handoffs: PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 79 Sokkuri (source) — shared table, excluded
- handoffs: PIKMIN2_LANE02_DEEPSEEK_HANDOFF.md, PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 84 Hana (source)
- handoffs: PIKMIN2_LANE08_DEEPSEEK_HANDOFF.md
- advances: (none)
- refused: attacks_receivers=injected, identity_spawn=uncited, movement_animation=uncited
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 93 BombOtakara (source) — shared table, excluded
- handoffs: PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md
- advances: (none)
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry

### 99 BlackMan (source)
- handoffs: PIKMIN2_LANE31_DEEPSEEK_HANDOFF.md
- advances: (none)
- refused: attacks_receivers=uncited, cleanup_reentry=uncited, death_corpse=uncited, identity_spawn=injected, movement_animation=injected
- blocking: identity_spawn, movement_animation, attacks_receivers, death_corpse, transport_reward, cleanup_reentry
