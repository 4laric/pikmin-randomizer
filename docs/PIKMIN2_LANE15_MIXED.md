# Lane 15 — two-identity mixed scene: Qurione (16) + ShijimiChou (77)

Fan-out lane 15 (`#166`/`#186`). Two **independently implemented** lane-15 native
identities on one build and one stage. This is a probe, not a generated-session
admission.

## 1. Identities and scene

| generator | host type | identity | source id | module |
|---|---|---|---|---|
| 203001 | `TEKI_Qurione` | Honeywisp | 16 | `pc_p2_qurione` (source FSM) |
| 204001 | `TEKI_Chappy` | Unmarked Spectralids (leader) | 77 | `pc_p2_shijimi` (source FSM) |
| 204002 | `TEKI_Chappy` | Unmarked Spectralids (follower) | 77 | `pc_p2_shijimi` |
| — | `TEKI_Chappy` | ordinary P1 Chappy control | — | unmodified host |

plus the overlay 20-red starting squad. The Qurione row is lifted from the
audited Qurione arena and re-positioned to `(-50, 30, 1750)`; the Shijimi rows
and control come from the audited Shijimi arena. No enemy state is injected.

## 2. Combined native candidate

- Native branch `opencode/p2-lane15-combined-native` @ `e2b49b90` (private,
  **not** pushed), base approved native `f14c6851`; merges the ported Qurione
  candidate (`opencode/p2-lane15-qurione-r2`) and the ShijimiChou candidate
  (`opencode/p2-lane15-shijimi-native`). Conflicts in `include/teki.h` /
  `tekibteki.cpp` were resolved additively (both `param_f` chains and both
  `suppress_ai`/update/draw/reset hooks coexist).
- Build `output/native-lane15-qurione-r2-build`, Ninja/MinGW Release, JAudio ON;
  `[106/106]` relink, `ninja -n` no work. `nectar.exe` SHA-256
  `B7313A15D7CB8A6C29088A5CD6BC7621AE40292DC5DC5ECAE498E6552573818B`.
- Arena `output/p2-lane15-mixed-arena/5619907cddf14bec832ed02cbf7da2c7`;
  evidence `…/mixed/` (`native.log`, `evidence.json`). One real-GL run,
  centred `960x540`, timer-terminated after 40 s.

## 3. Witness (natural)

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_QURIONE_BIND generator=203001 source_id=16 visual_only=0
P2_ENEMY_READY species=Qurione native_family=Qurione generator=203001 … behavior=native source_FSM=implemented reward=P2_Egg
P2_SHIJIMI_BIND generator=204001 source_id=77 visual_only=0
P2_ENEMY_READY species=ShijimiChou native_family=Chappy generator=204001 … behavior=native source_FSM=implemented attack=none reward=P1_nectar source=plants leader=1 group_count=2
P2_SHIJIMI_DRAW corpse=0
P2_QURIONE_DRAW corpse=0
```

Qurione states observed: `appear → move → drop → dead` (Egg attach/drop). All
evidence checks PASS; no extinction.

## 4. Gates

| Item | Status |
|---|---|
| Both identities bind/ready from ordinary spawn | PASS |
| Both drawn in the same scene | PASS |
| Centred 960x540, 20-red squad, no extinction | PASS |
| Qurione source FSM states in-scene | PASS |
| Combined performance budget | UNTESTED (no `[PC tick]` budget recorded) |
| Generated-session admission / randomizer eligibility | BLOCKED (lane 02/03/05) |
| Rewards/transport, cleanup/re-entry | BLOCKED (lane 06 / #397) |

## 5. Limitations

- Private fixture arena, not a generated/randomized session; no roster/admission
  integration.
- One timer-terminated run; no combined frame-time budget recorded.
- Both native candidates are off the maintained line; lane 01 owns export.
- Rewards (P2 Egg / nectar) and cleanup remain lane 06 / #397.

## 6. Tests

`tests/test_pikmin2_lane15_mixed_runtime.py` — all-pass witness, missing
identity/draw rejection, extinction rejection, generator constants.
