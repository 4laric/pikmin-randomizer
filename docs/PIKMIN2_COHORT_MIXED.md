# Cohort mixed scene: Dwarf Orange + Snow + Qurione + ShijimiChou

Four native identities staged together: two lane-13 (Dwarf Orange, plus the
maintained Snow Bulborb) and two lane-15 (Qurione, ShijimiChou). Probe only; not
a generated-session admission.

## 1. Scene

Built by extending the lane-13 mixed run (which already stages Dwarf Orange,
Snow, the Pod anchor, the P1 control and a 20-red squad) with the lane-15
Qurione and ShijimiChou identities and their audited configs/banks.

| generator | identity | module | behavior |
|---|---|---|---|
| 211001 | Dwarf Orange Bulborb | `pc_p2_dwarf_orange` | host P1 AI (FSM opt-in) |
| 5001 | Snow Bulborb | `pc_p2_enemy` | P1 AI |
| 203001 | Honeywisp | `pc_p2_qurione` | native source FSM |
| 204001/204002 | Unmarked Spectralids | `pc_p2_shijimi` | native source FSM |

## 2. Evidence

Native combined head `opencode/p2-lane13-15-combined-native` @ `d9ea68c9`
(private; base `f14c6851`), `nectar.exe` SHA-256
`508F78E15182CB90278786EAE99B64CD9E242D57543C5AF02E7A1BC102688B63`.
Arena `output/p2-cohort-mixed-arena/4a4626c5a6844c4884e4a40224c6caa4`;
evidence `…/cohort/`; one timer-terminated direct run, centred 960x540.

```text
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_ENEMY_READY species=YellowKochappy native_family=Chappy generator=5001 behavior=P1
P2_ENEMY_READY species=BlueKochappy source_id=44 generator=211001 … health=250.0 behavior=P1 purple_stun=bluekochappy_5s
P2_ENEMY_READY species=Qurione generator=203001 … behavior=native source_FSM=implemented reward=P2_Egg
P2_ENEMY_READY species=ShijimiChou generator=204001 … behavior=native source_FSM=implemented
P2_DWARF_ORANGE_DRAW corpse=0 / P2_SNOW_DRAW corpse=0 / P2_QURIONE_DRAW corpse=0 / P2_SHIJIMI_DRAW corpse=0
```

All checks PASS; no extinction. Measured `[PC tick]` steady state: mean ~5.5 ms,
p95 ~10.1 ms, budget 16.7 ms, startup worst 221.8 ms (measured, not an accepted
budget).

## 3. Gates / limits

- Four identities bind, load and draw together: PASS at probe level.
- Dwarf Orange and Snow run the host P1 AI (`behavior=P1`); the opt-in
  `pc_p2_kochappy_fsm` is default OFF.
- Generated-session admission BLOCKED (lane 02/03/05); rewards/transport and
  cleanup/re-entry BLOCKED (lane 06 / #397).
- Private fixture arena; lane 01 owns export.
