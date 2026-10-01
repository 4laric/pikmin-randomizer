# Long Legs source-FSM host on the approved native line (#173 / #312)

Lane 26 bounded slice. Implementation owner: Codex via shared account `4laric`.
Executing session: opencode (deepseek-v4.1-flash), 2026-09-14.

Base: root `3851d4b` (`codex/p2-main-review`, draft #432); approved native
`f14c6851473ac1161be56c8b98f4f905232f3635`. Private native worktree
`output/native-lane26-host`, branch `opencode/p2-lane26-host`, head `0d7af4d9`.
Patches `native-candidates/lane26-longlegs-host/0001..0005-*.patch`.

## Why this slice

Two pending lane candidates, `opencode/p2-longlegs-fsm` @ `ad4dcd6e` (FSM host)
and `dbff3a4b` (foot-crush InteractFlick), were based on merge-base `086ed858`.
The approved native line `f14c6851` carries the Long Legs policy and shell-pool
bound (`fb7fee46`) but not the host. `PIKMIN2_WAVE3_REVIEW_437.md` asked lane 26
to review target lifetime/receiver behavior on the approved line. This slice
ports the host to `f14c6851` and applies the review fix.

## What changed

`pc_port/pc_p2_long_legs.cpp`:

- Ticks `pc_p2_long_legs_fsm` per registered actor. Revision `0d7af4d9` moves
  the tick off the draw path into `BTeki::update()` via a one-line additive hook
  in `src/plugPikiNakata/tekibteki.cpp` (beside `pc_p2_snow_update`), so
  off-camera actors advance instead of freezing; `pc_p2_long_legs_draw` is now
  render-only. Dead actors are skipped via `isAlive()`, preserving the corpse
  guard. Landing/flick key edges are synthesized from the audit frame times at
  30 fps; inputs are nearest target within `privateRadius`, accumulating-Pikmin
  census, health and a host roll. Emitted state/foot/shell intents are logged.
- The landing key-2 press is applied as an `InteractFlick` (knockback 100,
  source `pressDamage`) to alive Pikmin inside the documented 60-unit port
  radius. `Stay` remains bitter-immune; actors become damageable after key 2.
- **Review fix:** the FSM only advances when `corpse == false`. Previously a
  corpse draw could re-enter the policy and emit a foot-crush from a dead
  registration. `pc_p2_long_legs_forget()` already erases the per-actor state,
  so no stale `ActorState`/`P2LongLegsFsm` survives a teardown.
- **Death wiring (`bb4a1bf7`):** the host now maps engine death of the placement
  vehicle to the policy `killed` input with one terminal tick, so the source
  death output fires (`P2_LONG_LEGS_DROP` with a held treasure, else
  `P2_LONG_LEGS_BIRTH` children). Previously the host never sent `killed`, so the
  policy `Dead` branch was unreachable at runtime. Treasure/children objects are
  lane 06/14/15/20, so the intents are logged, not spawned here.
- **Damage edge (`6fcfaa11`):** the host feeds a health decrease as the policy
  `damageTaken` input, which resets the Houdai shot cooldown (Houdai.cpp). The
  input was previously never set.
- Preserves the approved-line `#397` accessors `pc_p2_long_legs_count()` /
  `pc_p2_long_legs_registered()` that the pending candidate lacked.

`CMakeLists.txt`:

- Registers `p2_long_legs_fsm_test` and `p2_snagret_fsm_test`. Both test sources
  already existed on the approved line but only `p2_dangomushi_hazard_test` was
  wired to ctest, so the Long Legs and Snagret policies had no integrated gate.
- Registers the remaining unwired lane-27 hard-lane policy gates:
  `p2_fuefuki_{binding,fsm,interference_policy,suspend_fallback}_test` and
  `p2_bigtreasure{,_fsm,_attacks,_fsmhost,_host,_motion}_test` (the BigTreasure
  suite links the shared `pc_p2_bigtreasure*` policy sources).
- Registers `p2_bombsarai_{fsm,bomb,blast,clock,hover,terrain,induction}_test`
  for lane 27; their sources also shipped unwired. `p2_bombsarai_induction_test`
  previously hung: it performed state transitions inside `assert()`, and the
  Release `-DNDEBUG` build compiled those out, leaving an unbounded
  `while(!induce())` loop. It is fixed and now gates.
- Activates the assertions in all nine engine-free policy test units
  (`#undef NDEBUG` before `<cassert>`). Without this, wiring them to Release
  ctest produced vacuous PASSes because their state changes live inside
  `assert()`. The induction test's loop is additionally bounded.

## Evidence

- Private build `output/native-lane26-host-build` (Ninja Release, MinGW,
  `PIKMIN_NATIVE_JAUDIO=ON`): `pikmin_pc` PASS; `ninja -n` -> `no work to do`.
- Executable `output/native-lane26-host-build/bin/nectar.exe` SHA-256
  `8EC3882B30902ED6FA4D9275DF618B588185E2F77D7B3B732B49B40EF6071276`.
- `ctest -R 'p2_(long_legs_fsm|snagret_fsm|dangomushi_hazard)_test'` -> 3/3
  passed (`PASS LONG_LEGS_FSM`, `PASS SNAGRET_FSM`, `PASS DANGOMUSHI_HAZARD`).
- `ctest -R 'p2_'` -> 20/20 passed with assertions active (long_legs/snagret/
  dangomushi, 7 BombSarai, 4 Fuefuki, 6 BigTreasure).

## Runtime smoke (real GL) on the approved line

Head revision `6fcfaa11` (update-hook tick + death wiring + damage edge)
re-validated: exe `926D674C…C38184`, run `output/p2-lane26-host-run`,
`stdout3.log` SHA-256
`080FD400161025744811340CDBCC35899C0DE586D6CB4F6DECDD9749C6B45F06`:

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered ...
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_LONG_LEGS_BIND ... native_fsm=implemented
P2_LONG_LEGS_STATE ... BigFoot ... Land / Wait / Flick
P2_LONG_LEGS_FOOT  species=BigFoot generator=312002
P2_LONG_LEGS_BIRTH species=BigFoot generator=312002 count=30
P2_LONG_LEGS_STATE ... BigFoot ... state=Dead
P2_LONG_LEGS_STATE ... Houdai ... Land / Wait / Flick / Shot
```

BigFoot's engine death produces the source death output (`BIRTH count=30`) and
the policy then stays `Dead` with no further advance. Houdai advanced
`Land/Wait/Flick/Shot` — the off-draw-path tick and the damage-edge wiring work.
(`CRUSH=0`: the squad did not stand inside the 60-unit foot radius.)

The earlier draw-tick revision `6610a9dc` smoke is kept below.

Private build exe `8EC3882B...71276`, launched as
`nectar.exe --experimental-pikmin2-room` with `PIKMIN_P2_ROOM_WINDOW=960x540`
from `output/p2-lane26-host-run` (a new private copy of the lane-26 staged arena;
see the adoption note below). `stdout.log` SHA-256
`FAA5398CF7FE960B5E6155DBFC9061AB3D5B71E329703FCE2B49F480356958E7`.

Observed, in order:

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered ...
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_LONG_LEGS_BIND generator=312001 species=Houdai pose=bind visual_only=0 native_fsm=implemented
P2_LONG_LEGS_BIND generator=312002 species=BigFoot pose=bind visual_only=0 native_fsm=implemented
P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Land
P2_LONG_LEGS_FOOT  species=BigFoot generator=312002
P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Shot
P2_LONG_LEGS_DRAW  corpse=1 species=BigFoot pose=bind
```

- 20 live reds start; no extinction marker.
- Houdai reached `Shot` only after a `Flick` (source ordering), BigFoot cycled
  `Wait`/`Flick`; one `Land ->` foot intent fired.
- `P2_LONG_LEGS_CRUSH` = 0: the squad spawned ~190 units from BigFoot, so no
  Pikmin were inside the 60-unit foot radius (same placement limit as the
  pre-integration run).
- **Corpse guard confirmed:** BigFoot drew as a corpse and no `P2_LONG_LEGS_STATE`
  / `FOOT` / `SHELL` line follows it, so a dead registration no longer advances
  the policy or emits a crush.
- GL concurrency disclosure: a separate `fixture` process was present on the host
  for part of this window; the lane-26 markers above are unaffected but the run
  was not exclusive.

### Fixture baseline adoption

| Field | Value |
|---|---|
| Lane / owner | 26 / Codex via shared `4laric` (executing: opencode deepseek-v4.1-flash) |
| Native | `opencode/p2-lane26-host` @ `6610a9dc`, private build `output/native-lane26-host-build` |
| Window | `960x540`; marker `Experimental preview window set to 960x540 windowed and centered` |
| Squad | `P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`, no immediate extinction |
| Run | `output/p2-lane26-host-run`; `default.gen` SHA-256 `4D171671BBB62991677D7CF68C2BCDEAA7166463C3A66A625A64DDFF2E9B37AA` |
| Arena provenance | **Reused** the lane-26 staged arena (already 20-red overlay), copied to a new private dir. Not re-imported: the Long Legs source `.mod` import is not present locally in this pass. |
| Executable | SHA-256 `8EC3882B30902ED6FA4D9275DF618B588185E2F77D7B3B732B49B40EF6071276` |

## Six-gate status for this commit

| Gate | Status | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PARTIAL | placement vehicle; BIND `native_fsm=implemented` for 312001/312002; no source actor |
| 2. Autonomous movement and animation | PARTIAL | schedule observed (`Land/Wait/Flick/Shot`); no IK movement, draw-path tick only |
| 3. Attacks and receivers | PARTIAL | foot intent observed; `InteractFlick` path compiled, 0 hits (placement); weak-point/leg-tube damage host-side |
| 4. Death and corpse | PARTIAL | engine death now signals the policy `killed`; `DROP`/`BIRTH` intents log (objects owned by lane 06/14/15/20); no corpse/re-entry host |
| 5. Actual transport and reward | UNTESTED | depends on lane 06 |
| 6. Cleanup and re-entry | PARTIAL | `forget()` + corpse guard verified; full scene/day lifecycle not run |

## Remaining blockers and next slices

1. **IK body.** Without `IKSystemMgr` there is no Walk translation or real
   foot-plant collision; the draw-path tick freezes off-camera. Largest blocker
   for gates 2-4.
2. **Animation events.** key edges are synthesized; the authoritative sampled
   clock (lane 08) should drive them.
3. **Man-at-Legs shells.** `fireShell` is only logged; lane 20's projectile
   contract must consume it (source pool of 10).
4. **Natural death.** The proxy is a P1 `Chappy`; real death/re-entry needs a
   source actor. (The corpse guard was exercised because the proxy died during
   the run; that is engine death of the proxy, not source Long Legs death.)
5. **Arena re-import.** The runtime reused the staged lane-26 arena because the
   source `.mod` import is not available locally; a fresh overlay regeneration
   should accompany the next placement where Pikmin start under a foot.

Source-mechanics/host increment with a real-GL smoke. Not playable and not
family-complete evidence.
