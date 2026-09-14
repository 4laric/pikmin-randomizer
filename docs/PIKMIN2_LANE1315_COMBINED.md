# Lane 13/15 — three-identity combined native candidate and mixed scene

One native head carrying all three lane-13/15 native modules, plus a
three-identity scene run. Probe only; not a generated-session admission.

## 1. Combined native candidate

- Native branch `opencode/p2-lane13-15-combined-native` @ `27c560e6` (private,
  **not** pushed), base approved native `f14c6851`. Merges the lane-13 Dwarf
  Orange candidate (`opencode/p2-lane13-orange-native`) into the lane-15
  combined candidate (`opencode/p2-lane15-combined-native`: Qurione + Shijimi).
- Conflicts in `include/teki.h`, `tekibteki.cpp` and `tekimgr.cpp` resolved
  additively: the `TPF_Life` chain is now
  `pc_p2_dwarf_orange_max_health(pc_p2_kochappy_max_health(pc_p2_snow_max_health(pc_p2_qurione_param_f(…Kogane/Sokkuri/Armor/shijimi…))))`;
  all three `draw`/`update`/`suppress_ai`/`reset`/`forget` hooks coexist.
- Build `output/native-lane15-qurione-r2-build`, `[107/107]` relink, `ninja -n`
  no work. `nectar.exe` SHA-256
  `2656A875584798203C1409814D40AB5BFCCE233CA057D9BD6251155EFBC3BF97`.

This is the single artifact to hand to lane 01 for the lane-13/15 cohort; it
supersedes the three separate candidates listed in
`docs/PIKMIN2_LANE13_15_HANDOFF.md`.

## 2. Three-identity scene

`output/p2-lane1315-mixed-arena/bdea1ad3bd21473ab8d555c535abc4f1/mixed3/`
(centred 960x540, 20-red squad, one timer-terminated direct run):

```text
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 … health=250.0 max_health=250.0 behavior=P1 purple_stun=bluekochappy_5s
P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000
P2_QURIONE_BIND generator=203001 source_id=16 visual_only=0
P2_SHIJIMI_BIND generator=204001 source_id=77 visual_only=0
P2_SHIJIMI_BIND generator=204002 source_id=77 visual_only=0
P2_DWARF_ORANGE_DRAW corpse=0
P2_QURIONE_DRAW corpse=0
P2_SHIJIMI_DRAW corpse=0
```

All checks PASS (`tests/test_pikmin2_lane1315_mixed_runtime.py`); no extinction.

## 3. Gates / limitations

- Three independently implemented identities bind, load and draw together in one
  scene on the approved baseline: PASS at probe level.
- Combined performance budget UNTESTED (no `[PC tick]` budget recorded).
- Generated-session admission BLOCKED (lane 02/03/05); rewards/transport and
  cleanup/re-entry BLOCKED (lane 06 / #397).
- Dwarf Orange behavior is still the host P1 AI (`behavior=P1`); the source
  `KochappyBase` FSM is not ported.
- Private fixture arena, not a randomized session; lane 01 owns export.
