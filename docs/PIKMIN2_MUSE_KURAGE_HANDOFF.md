# Muse l58 — Kurage57 correlated natural generated birth (#498)

Parent #243; wave #491; integration #437/#186. Implementation owner: Codex
through shared account 4laric; executing contributor Muse Spark 1.3 via
OpenCode (lane muse-kurage, l58).

## Scope

Close gate 1 with the SAME real generated slot/generator appearing in
placement, source-ID resolve, and Kurage binding. Reviewed candidates from
muse-placement (l52/#492) and muse-packaging (l53/#493) were consumed after
their dependency-ready records; a real ENEMY_P2 generated session was run
and validated with both observers. The old 201001 sidecar auto-bind is never
passed off as a generated identity. Legacy l29 claim and capture/ingestion
modules are read-only; accepted gates 2-6 are unchanged (with new-run
corroboration noted on gates 4-5, not relabelled).

## What was added (reserved files only; dependencies consumed separately)

- `experimental/pikmin2_muse_kurage.py`: read-only log observer
  `validate_generated_birth()` correlating `P2_SEED_RESOLVE source_id=57`,
  `P2_GENERATED_PLACEMENT source_id=57 target=<uid> generator=<gen> bound=1`
  (reviewed l52 contract), `P2_KURAGE_TEKI_READY` and
  `P2_KURAGE_CORPSE_READY` via the triple chain (resolve target ==
  placement target == accepted slot `689702860`; placement generator ==
  teki generator == corpse receipt generator). Fail-closed on any missing
  marker, mismatch, non-accepted slot, `bound=0`, or injected/health_zero
  taint. Legacy 201001 auto-bind without generated markers is an explicit
  named FAIL.
- `tests/test_pikmin2_muse_kurage.py`: 16 tests — new-contract PASS,
  legacy-format PASS, distinct-generator chain PASS, plus negatives for
  auto-bind, missing placement/resolve, slot disagreement, slot-not-accepted,
  generator disagreement (both formats), `bound=0`, wrong source ID,
  injected taint, corpse-receipt mismatch, and empty log.
- `native/tools/p2_muse_kurage_fixture.cpp`: dependency-free C++ twin of the
  observer (reads a native.log path or stdin, exit 0 PASS / exit 1 FAIL).
  Links against nothing; NOT registered as an engine replacement-main
  target (shared-hook request to #491 deferred until the marker contract
  stabilizes across the four consumer lanes).
- This handoff doc with the identity-specific six-gate table.

## Consumed dependency candidates (not authored; preserved as-is)

Root branch `codex/muse-l58-kurage`, in order after own base work:

1. `406d2b8b` cherry-pick of reviewed `bd97334a` (l52/#492): candidate-only
   generated slots incl. `(57, 'Kurage', 689702860, 'Frog0')`, observer
   `experimental/pikmin2_muse_placement.py`, 16 sync tests. No conflicts.
2. `c0b64d3a` cherry-pick of reviewed `3131b76d` (l53/#493): candidate-only
   staging (`experimental/pikmin2_muse_packaging.py`, 57 via sidecar path)
   plus 58 family binding. No conflicts.
3. `465496d5` cherry-pick of reviewed `f82171d4` (l53/#493 handoff doc).
   No conflicts.

Native branch `codex/muse-l58-kurage-native`:

1. `558d12af` cherry-pick of reviewed `4765885b` (l52/#492 native): case
   41/57/58/78 bind recording the (actor, source, target, generator)
   triple and emitting the accepted-slot `P2_GENERATED_PLACEMENT` marker;
   returns false so the family sidecar owns behavior. No conflicts.

Ancestry was inspected first (`merge-base --is-ancestor` false on all four
before consuming); the broad wave was not merged.

## Interfaces / hooks touched

None by this lane. No shared file edited; dependency files arrived via the
reviewed cherry-picks above. Outstanding shared-hook request (to #491):
register `tools/p2_muse_kurage_fixture.cpp` as a standalone (non-engine)
CMake target once the marker contract stabilizes.

## Build evidence (leased runner, real protected process)

- `output/muse-wave/l58/build-1789523215792674600.log`
  (sha256 `61071d59840ef487b438625d8a57a28f3df27c115a18eb76704d2f94fcd1ca73`):
  configure + `pikmin_pc` 616/616 link + `ninja -n` -> `ninja: no work to do.`
- Native head `1a75fc3732a0c2a65da260e8d70ef41c188923fa`, dirty empty;
  build dir `output/msw/native-l58-build`;
  exe `bin/nectar.exe` sha256
  `29ffb4a79a43028be3a73e455c00916800aa4e6aee48177dab5a3aa6dbdea774`.
- The run below used exactly that executable.

## Runtime evidence (private run, natural generated birth)

Fresh arena staged with the current overlay into NEW private dir
`output/muse-wave/l58/kurage-genesis/430c465ce7ae4838a9e57b2921197afc`
via `experimental/pikmin2_kurage_teki_stage.py --generator 689702860`
(Frog0 vehicle record id 689702860, sidecar `P2_KURAGE_TEKI_1 1 689702860 0`,
cargo Pod `p2-pod.txt`, no `p2-cargo-free.txt`), plus run inputs
`p2-placement-slots.txt` (`P2_PLACEMENT_SLOTS_1`, `689702860 689702860`,
the reviewed slot join) and `p2-genesis-seed.txt` (minimal `ENEMY_P2 1
<roster-revision> 1` binding `689702860 57`).

Launch (cwd = run dir):
`bin/nectar.exe --experimental-pikmin2-room --randomizer-seed p2-genesis-seed.txt`
with `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1`, MinGW DLLs on PATH;
150 s harness deadline reached (TIMEOUT, expected). Log `run.log` sha256
`0e76d0a319e6b08ad5aa908f9071632b4e078e26936876a952a6d120148cecec`.

- Fixture adoption: `:14` 960x540 windowed and centered; `:248`
  `P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1` (live 20-red
  starting squad); no immediate extinction; staged squad/captain positions
  are the overlay defaults plus the engineered Frog0 record near the squad
  (documented in the stager).
- Birth correlation (all natural, no injected markers anywhere in the log):
  `:592 P2_SEED_RESOLVE source_id=57 target=689702860`,
  `:593 P2_GENERATED_PLACEMENT ... bound=1`,
  `:594 P2_PLACEMENT_SLOT generator=689702860 slot=689702860 ... terrain=ground route=1`,
  `:730 P2_KURAGE_TEKI_READY generator=689702860`,
  `:731 P2_KURAGE_CORPSE_READY ... receipt=corpse:kurage:689702860`.
- The same generated actor then died naturally and paid out:
  `:809 P2_KURAGE_TEKI_DEAD generator=689702860`,
  `:858 P2_POD_RECEIPT id=corpse:kurage:689702860 value=2 new=1 pokos=2 seeds=0`.
- Observers on the real log: Python `validate_generated_birth` PASS;
  C++ fixture exit 0 `KURAGE_GENERATED_BIRTH_PASS`; l52
  `observe_identity(57)` correlated=true bound on accepted slot.

## Test evidence

- `tests/test_pikmin2_muse_kurage.py`: **16 passed** (new contract).
- Adjacent suites: `test_pikmin2_muse_placement.py` 16 passed;
  `test_pikmin2_muse_packaging.py` + `test_pikmin2_family_install.py` +
  `test_pikmin2_install_binding.py` + `test_pikmin2_bombsarai_install.py`
  all pass; kurage `rewards`/`runtime`/`pod_receipt` suites pass
  (37 passed with the new 16 counted separately).
- `scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_KURAGE_HANDOFF.md`:
  exit 0, no refused PASS rows.
- C++ fixture: `g++ -fsyntax-only` exit 0; linked standalone; exit 0 on the
  new-contract sample and the real run log, exit 1 on auto-bind and
  wrong-slot samples.

## Concrete source ID

- Source ID: 57 `Kurage`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/muse-wave/l58/kurage-genesis/430c465ce7ae4838a9e57b2921197afc/run.log:592 P2_SEED_RESOLVE source_id=57 target=689702860; :593 P2_GENERATED_PLACEMENT bound=1; :730 P2_KURAGE_TEKI_READY generator=689702860; :731 CORPSE_READY receipt=corpse:kurage:689702860 | natural |
| 2. Autonomous movement and animation | PASS (natural, inherited) | docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md slice 4; output/dsw/l29-out/kurage-arena/b7439430e78b48b6ad2c9400f50f4b02/run.log:764 P2_KURAGE_MOVE 136 samples states 1/2/4/9 | natural source FSM; body stand-in labelled in l29 |
| 3. Attacks and receivers | PASS (natural, inherited) | docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md slice 4; output/dsw/l29-out/kurage-arena/b7439430e78b48b6ad2c9400f50f4b02/run.log:793 P2_KURAGE_RECEIVER_HIT, :794 ATTACH stick_before=0 stick_after=1, :852 KILL alive_after=0 | natural receiver on live Pikmin |
| 4. Death and corpse | PASS (natural, inherited + corroborated) | docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md slice 3 run.log:808 P2_KURAGE_TEKI_DEAD; corroborated on generated slot output/muse-wave/l58/kurage-genesis/430c465ce7ae4838a9e57b2921197afc/run.log:809 P2_KURAGE_TEKI_DEAD generator=689702860 | natural |
| 5. Actual transport and reward | PASS (natural, inherited + corroborated) | docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md slice 3 run.log:855 P2_POD_RECEIPT id=corpse:kurage:201001; corroborated on generated slot output/muse-wave/l58/kurage-genesis/430c465ce7ae4838a9e57b2921197afc/run.log:858 P2_POD_RECEIPT id=corpse:kurage:689702860 value=2 new=1 pokos=2 seeds=0 | natural |
| 6. Cleanup and re-entry | PASS (natural, inherited) | docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md slice 4; output/dsw/l29-out/kurage-reentry-run/stdout.log:766 FORGET, :770 RESET, :774 REENTRY_PASS stale_bound=0 rebound=1 | natural forget/reset seam |

Gates 2-6 remain owned by the read-only l29 slices (no relabelling of
their concessions: P1 type-0 stand-in body, corpse credit as a stand-in
for the source number-pellet reward per `Kurage.cpp:36`). The new run adds
a same-slot natural birth/death/receipt corroboration for gates 1/4/5.

## Reproduction

```
py -3.12 -m pytest -q tests/test_pikmin2_muse_kurage.py
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_KURAGE_HANDOFF.md
py -3.12 -m experimental.pikmin2_kurage_teki_stage --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --converted C:/Users/alari/pikmin-randomizer/output/pikmin2-room105 --output <new-dir> --generator 689702860
# add p2-placement-slots.txt + p2-genesis-seed.txt per this handoff, then in the run dir:
# bin/nectar.exe --experimental-pikmin2-room --randomizer-seed p2-genesis-seed.txt  (PIKMIN_P2_ROOM_WINDOW=960x540)
py -3.12 -c "from experimental.pikmin2_muse_kurage import validate_generated_birth; print(validate_generated_birth(open('<run>/run.log').read()))"
```

## Remaining work

1. Integrator review of this ADMISSION CANDIDATE (no ADMIT writes by this
   lane; allowlists untouched).
2. Shared-hook request to #491: register
   `native/tools/p2_muse_kurage_fixture.cpp` as a standalone (non-engine)
   CMake target once the four-lane marker contract stabilizes.
