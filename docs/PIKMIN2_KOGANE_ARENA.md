# Beetle lane batch 2 — install + arena (#219)

Follows batch 1 (#212, commit `6adc65c`; audit in
[PIKMIN2_KOGANE_AUDIT.md](PIKMIN2_KOGANE_AUDIT.md)). Codex, shared 4laric.
Scope: IDs 9 Kogane, 10 Wealthy, 11 Fart. Evidence level advanced to
**native display placement** for the shared visual bank; behavior gates remain
blocked on native-track registration (see below).

## Install (hash-bound)

Module: `experimental/pikmin2_kogane_install.py` (follows the
`pikmin2_dwarf_bear_install.py` pattern; no shared-file edits).

- Binds the batch-1 `beetles.json` manifest: schema/family identity, species
  IDs 9/10/11, the exact damage-clip event frames (drop must fire at frame 7),
  and per-pose SHA-256 — any drift, tampering or partial bank is refused
  **before** any mutation.
- Installs canonical-LF exact-byte configs into a private run:
  `p2-kogane-profile.txt` (species/drop/gas contract tokens),
  `p2-kogane-bank.txt` (clip/frame/event/pose listing),
  `p2-kogane-actors.txt` (`P2_KOGANE_ACTORS_1` + generator IDs), receipt
  `kogane-install.json`, and the 9 pose `.mod` files (prefixed `kogane_`) into
  `assets/dataDir/courses/pikmin2room/`.
- Optional visual bank is all-or-nothing; absent `.mod` files preserve the
  baseline (`visuals='absent_baseline_preserved'`). Sibling `P2_*` actor
  bindings are scanned for generator-ID overlap.

Real install evidence (private): `output/p2-kogane-batch2/stages/<id>/` —
9/9 pose files installed; every installed file's SHA-256 equals the receipt
AND the generated batch-1 bank (installed == generated hash compare: True).
Conflicting reinstall on the same run is refused.

## Arena staging

Module: `experimental/pikmin2_kogane_arena.py` per
[the arena contract](PIKMIN2_ENEMY_ARENA.md).

- Original Impact Site (practice) map/collision/routes preserved byte-identical
  (per-file SHA-256 verified after overlay); stage slot `chal0`.
- Roster: one actor per species plus one P1 control — generators
  219001 kogane / 219002 wealthy / 219003 fart / 219004 P1 Chappy at
  (-150,30,1850) / (-50,30,1850) / (50,30,1850) / (150,30,1550). IDs checked
  against actual stage records at staging time; no overlap with known
  allocations (60000–61009 sheargrub, 186001/2 kochappy, 186081/2 breadbug,
  186151–153 tank, 201001–4 frog, 211001/2 dwarf orange, 211101/2 dwarf bear).
- Generator position + offset is translation only (zero offset, validated);
  source yaw unapplied (`source_yaw=None`). Scatter circle zeroed via the
  deterministic fixture override — engineered choice, not production placement
  evidence.
- The beetle rows reuse the audited one-actor enemy template framing as a
  **placement vehicle only**; no P1 proxy species is decided (the family has
  no Pikmin 1 counterpart — batch-1 audit §6).

## Native runtime acceptance (fixture probe)

Module: `experimental/pikmin2_kogane_runtime.py` (frog-lane fixture pattern:
private instrumented `tools/preview_p2_room.cpp` RoomApp + tutorial auto-A
replacement, private objects only; no production native source changed).

- Fixture: `output/p2-kogane-batch2/fixture01/fixture.exe`, SHA-256
  `3ead46a568d3fa4d6a8165dd2bac13a15212481fd45066558929b4f44c06343e`; native
  HEAD `b602d8c43dc6a1132821f787b99a28097c3c7521` (existing tracked edits in
  `creatureCollision.cpp`/`goalItem.cpp` snapshotted; freshness checks passed;
  native state unchanged after the private link).
- Run: `output/p2-kogane-batch2/validation02/stages/86abc94516b64f83991dfb26414daecd`
  (native.log, runtime-evidence.json). Result: **PASS** — all four generator
  IDs birthed exactly once at the expected XYZ (within 0.02; generator and
  stored birth both checked), all four alive after 300 active observations,
  clean exit 0. Spawned native type 3 = the template's P1 placement-vehicle
  type; **beetle identity is not claimed**.
- First attempt (validation01, no tutorial auto-A) stalled in the tutorial
  window and timed out — recorded as a failed attempt; the tutorial
  instrumentation fixed startup progression only.

### Gate table

| Gate | Result | Evidence / limits |
|---|---|---|
| Spawn at exact XYZ, stage/configs load | PASS (placement vehicle) | validation02 runtime-evidence.json; beetle identity NOT established |
| Control actor undisturbed | PASS | all 4 actors alive at observation 300 |
| Installed artifact loadability | PASS (host-side) | installed == generated hash compare; receipt hashes |
| Flip/drop cycle (frame 7) | BLOCKED | P2-only FSM; no pc_p2_kogane registration |
| Fart gas cloud | BLOCKED | P2-only InteractGas emitter; needs native registration |
| Forced escape after 3 flips | BLOCKED | P2-only FSM; needs native registration |
| Unlooted cave relocation | BLOCKED | requires `Cave::randMapMgr`; P2 caves not in the P1 engine |
| Reload/cleanup | UNTESTED | — |

## Native hook request (flagged per boundary, not implemented here)

Behavior gates need the native track to register a `pc_p2_kogane` module:
actor registration reading `P2_KOGANE_ACTORS_1`, visual bank binding
(`kogane_*.mod` + per-species karada k-color from `p2-kogane-profile.txt`),
the shared 5-state beetle FSM (Appear/Move/Wait/Press/Disappear) with
frame-7 `createItem` drops, Fart's timed gas emitter, 3-flip forced escape,
and — only if P2 cave relocation is in scope — a `randMapMgr` analog. Tracked
on #219 / integration #186.

## Tests

- `tests/test_pikmin2_kogane_install.py` (12 tests): exact-byte config writes,
  installed==generated byte equality, receipt hash verification, reinstall
  refusal, tampered/partial bank refusal before mutation, baseline
  preservation, sibling overlap refusal, ID/manifest/event drift rejection,
  non-junction room refusal.
- `tests/test_pikmin2_kogane_arena.py` (7 tests): roster uniqueness and
  species order, translation-only XYZ, generator-ID collision, nonfinite
  position rejection, runtime log validator accept/reject paths.
- Batch-1 `tests/test_pikmin2_kogane_assets.py` (15 tests) still passes.

## Batch 3 — binding validation against native unblock (7faa644 / root f9f0839)

The native track integrated the beetle binding (#228 handoff): native commit
`7faa64475176658af85e2f558858c6d660cd4d20`, root `f9f0839`, fixed check bundle
`output/p2-root-integration/output/kogane228/runtime/stages/f0bb11777d6040f5a68e7be3768dbc95/`
(`Check.cmd` / `BindingCheck.exe`, SHA-256 `5385bd99…8baa36`).

Independent lane re-run (direct exe invocation with the Check.cmd environment,
`SDL_AUDIODRIVER=dummy`, MinGW64 PATH; exit 0 in 31 s; log
`kimi-binding-run.log` inside the fixed stage dir; lane record
`output/p2-kogane-batch2/binding-validation.json`):

- Typed source IDs: `219001→9`, `219002→10`, `219003→11`, control `219004→-1`
  with `control=1` (`P2_KOGANE_ID` lines).
- Exact birth XYZ for all four actors, matching this lane's arena roster
  (`P2_KOGANE_BIRTH` lines, ±0.000 after formatting).
- Imported draw binds: `P2_KOGANE_DRAW corpse=0` present; capture
  `kogane-binding.png` shows the three imported models plus ordinary control
  (shared black/silver approximation — species texture fidelity NOT claimed).
- PASS marker `behavior=P1_visual_binding_source_FSM_pending`: **P1 host AI
  remains; no P2 FSM/drop/gas claim**.
- Host-side bundle verification (`verify_fixed_run`): every file in
  `fixed-manifest.json` re-hashes clean, recorded evidence passed, and the
  binding consumed this lane's installed configs **unchanged** (profile/bank/
  actors hashes equal the batch-2 `kogane-install.json` receipt).

New validators in `experimental/pikmin2_kogane_runtime.py`:
`validate_binding` (typed mapping, control flag, exact XYZ, draw, host-AI
disclaimer, exit code) and `verify_fixed_run` (fixed-bundle re-hash, evidence
gate, lane-config consumption proof). Tests:
`tests/test_pikmin2_kogane_binding.py` (11 tests — clean-log acceptance,
wrong source ID, control-as-species, XYZ drift, missing draw/PASS, tampered
bundle file, failed evidence, lane-config drift, bad schema).

## Open

- All behavior gates above (native track / integration lead).
- Visual fidelity (materials/TEV approximation, change-texture + k-color
  identity per species) unverified in-scene; needs native visual binding first.
- Parallel lanes (#220 Breadbug, #221 Mamuta) untouched; no shared-file needs
  arose in this batch.

## Maintained-line fixture adoption + cleanup/re-entry (lane 17, 2026-09-14)

The batch-4 behavior fixture was previously only on the lane branch; the
maintained root (`codex/p2-main-review`) carried the older placement-only
`experimental/pikmin2_kogane_runtime.py` plus the split
`pikmin2_kogane_binding_runtime.py`. This slice ports the parameterized runtime
and behavior module onto the maintained line and adds the reload gate.

- `pc_port/pc_p2_kogane.cpp`/`.h` at native maintained `9735870c` are
  byte-identical to the `kogane-b4@fe780120` candidate; **no native change** was
  needed for this slice.
- Ported: `pikmin2_kogane_runtime.py` `instrument(source, app=APP)`,
  `build(..., app=None)`, `run(..., sidecar=None, validator=None)`;
  `experimental/pikmin2_kogane_behavior.py`; `tests/test_pikmin2_kogane_behavior.py`.
- **Cleanup/re-entry gate**: at observation 50 the fixture calls the public
  `pc_p2_kogane_reset()` and checks `pc_p2_kogane_source_id()` returns -1 for
  all three actors (stale registration rejected), then calls
  `pc_p2_kogane_setup()` and checks the three bindings rebuild.
  Marker: `P2_KOGANE_CLEANUP registered_before=3 cleared=3 reentry=3`.
- Fixture baseline adopted: `ensure_pikmin_squad` 20-red overlay, 960x540
  centred window log line present, live squad, no extinction screen.

### Acceptance (private build, fresh integration baseline)

- Native source/HEAD: `output/p2-main-review/native` @
  `9735870cea769169446c524b6ae0cbdb07ed920e` (clean); build
  `output/p2-upstream433-build` (`ninja -n pikmin_pc`: no work to do).
- Fixture `output/lane17-kogane-behavior/fixture2/fixture.exe` SHA-256
  `9216f82254171c52d5164dd24ef4922bd891e974361da426e72f16f089e17dba`.
- Run `output/lane17-kogane-behavior/run2/stages/108e9f0f503c440297426a47d62977c6`:
  **PASS** (11/11 checks; census pellets=4 nectar=14 pikis=19).
- Remaining gaps: material/texture fidelity, treasure override, cave
  relocation, and full scene/day reload (only manager reset/re-entry is covered).
