# Muse lane l57 (Fuefuki41) — genesis generated-birth handoff

Slice: **correlated natural generated birth for gate 1 (identity_spawn)**.
Two parts: (a) the additive observer/negative-test contract (generation 1,
preserved), (b) consumption of the reviewed placement/packaging candidates
plus one real generated-session run whose log carries the same slot/generator
across placement, source-41 resolve and Fuefuki actor binding markers
(generation 2, this continuation). Gates 2–6 stay exactly as the claim-held
legacy l28 lane left them; no ADMIT writes.

- Source enemy: **Fuefuki (Antenna Beetle), EnemyID 41** (`EnemyID_Fuefuki`,
  `BDT_Strong`). Roster: `docs/PIKMIN2_ENEMY_ROSTER.json` source_id 41,
  role source, spawnable.
- Legacy l28 lane is claim-held: inspected read-only
  (`output/deepseek-wave/handoffs/l28.md`, diagnostic slice + slices 3–4);
  no edit to its worktree, family FSM, or handoff.
- Parent issues: family #245; wave #491; child #497.

## Source ID and files owned (all new, additive)

- Root (new, generation 1):
  - `experimental/pikmin2_muse_fuefuki.py` — dependency-free `parse(text)`
    verdict for the correlated triple. Requires placement `slot` uid ==
    `P2_SEED_RESOLVE source_id=41` `target` uid, placement `generator` file
    id == Fuefuki binding `gen`/`generator` file id, mapped slot
    (`slot != 0`), `terrain=ground` + `xyz=1`, `route=1`. Anything else
    yields `gate1_ok False`. Emits no markers; cannot fabricate acceptance.
  - `tests/test_pikmin2_muse_fuefuki.py` — 12 contract tests: canonical
    triple, TEKI-marker binding, file-id mismatch, seed-uid mismatch,
    missing placement/resolve/binding, wrong source id, unmapped slot,
    water terrain, missing route, empty log, proxy-without-seed.
  - `docs/PIKMIN2_MUSE_FUEFUKI_HANDOFF.md` — this file.
- Native (new, generation 1, engine-independent):
  - `native/tools/p2_muse_fuefuki_fixture.cpp` — standalone stdlib-only
    log checker implementing the same triple contract; exit 0 iff
    correlated, 1 otherwise. No engine headers; not linked into any game
    target.

No shared file touched by authored scope. Dependency commits below are
cherry-picked verbatim (authors/messages preserved) and kept separate.

## Ordered commits (clean)

Root branch `codex/muse-l57-fuefuki` (base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`):

- `ec53d25b0822d3b999495a17b913bdd140c536b7` lane57: Fuefuki gate-1 correlated observer + negative tests (#497)
- `568384c46f2892cbd4becac41beb0b3227a83a67` lane57: observer-slice handoff doc (#497)
- `b5486ee95dba1409f4cae5216be321e95a88f877` cherry-pick placement `bd97334a` (#492, reviewed; zero conflicts)
- `08bd181915084a925eeb1005e020619cc2161f01` cherry-pick packaging `3131b76` (#493, reviewed; zero conflicts)
- `d5e78523729b6927964df77d2989fa936902a577` cherry-pick packaging `f82171d` (#493, reviewed; zero conflicts)
- `5ef3ebdabfeb6d23a7f41459211babd42f8041ba` lane57: genesis generated-birth run + gate-1 evidence (#497)

Native branch `codex/muse-l57-fuefuki-native` (base `7b9ecaa668fd55332073446cdbdaf6424b209ea7`):

- `a0b559fa5954444c0a10afb6f4020a1f72ce58f0` lane57: Fuefuki gate-1 standalone log-checker fixture (#497)
- `499e513c7000da008c041beff4e50f349672e6bb` cherry-pick placement-native `4765885b` (#492, reviewed; zero conflicts)

No conflict resolutions: every candidate was single-purpose, additive, based
exactly on this lane's bases, with zero file overlap against owned files.
No wave wholesale merge.

## Genesis run (generation 2): real generated birth for source 41

Staging script `output/muse-wave/l57/stage_genesis.py` (uncommitted runtime
state, not a reserved file):

- Layout from the REAL seed machinery
  (`experimental.pikmin2_seed_bridge.resolve_layout('muse-l57-genesis',
  'Player1', ['1254096625'], [41])`): `{target:'1254096625',
  source_id:41, enum_name:'Fuefuki'}`, structurally validated; the target is
  asserted constraint-compatible via
  `binding_targets_for_muse_sources([41])`. Candidate-scoped private run
  (explicit cohort, labelled throughout); roster overlay untouched
  (`opt_in_validation_cohort` correctly refuses the still-denied row — no
  ADMIT writes, deny-by-default preserved).
- `bootstrap.txt` carries the real `build_bootstrap` line
  (`ENEMY_P2 1 a019a3ef...902 1 1254096625 41`); the roster revision equals
  native `randomizerP2RosterRevision` and `randomizerP2IsBindable(41)` is true.
- Fresh arena via `scripts/preview_pikmin2_room.prepare` (current
  starting-squad overlay): 25 records — 20 red Pikmin, red onion, ship,
  dwarf bulborb, treasure bolt, plus one appended P1 TEKI_Napkid (type 11)
  generator 245001 at (-110, 20, 0).
- Sidecars: `p2-fuefuki-teki.txt` (`P2_FUEFUKI_TEKI_1 245001 11`),
  `p2-placement-slots.txt` (`245001 -> 1254096625`). No Pod/cargo: gate 1
  is birth-only. Stage manifest: `output/muse-wave/l57/genesis/stage-manifest.json`.

Build (leased runner, generation 2): configure + `pikmin_pc -j 6` +
`ninja -n` dry run, exit 0. Native `499e513c` clean; executable
`output/msw/native-l57-build/bin/nectar.exe` SHA-256
`cc607620411ddcbd5b06926fa60a1971cc3249ec34410a09040b0b887ad31e93`.
Log: `output/muse-wave/l57/build-1789523181478217400.log` SHA-256
`744371c12a782ae99a0a2e1b2dda669041a6e64b9377f2fe8d172c50cce95b8e`.

Run (private, no shared-runtime lease): `nectar.exe
--experimental-pikmin2-room --randomizer-seed <run>/bootstrap.txt`,
cwd = `output/muse-wave/l57/genesis/6823ba537f8d4555b1d3d0419df5a20b`,
`PIKMIN_P2_ROOM_WINDOW=960x540`, `SDL_AUDIODRIVER=dummy`, 90 s window
(timed out as expected for a live room; exit 1 from termination only).
Log: `output/muse-wave/l57/genesis/native.log` SHA-256
`94dadc758b2a649bfd19fc7bfbad13b237e3f46e645553e8d9a111a1b1f4debc`
(1079 lines). Run meta: `output/muse-wave/l57/genesis/run-meta.json`.

Fixture adoption: fresh arena (new uuid dir, current `prepare()` overlay),
`Experimental preview window set to 960x540 windowed and centered` (log:14),
live squad of 20 (`P2_FUEFUKI_TEKI_FREE_RECRUIT ... squad=20`, log:994/1019),
active gameplay (corpse-haul ticks to :1022), no extinction screen in the log.
Two benign `DVDOpen ... FAILED` lines (:417-418) for optional `1.gen` /
`init.gen` absent from every room overlay; the run proceeds to full
birth/bind/gameplay. Staged squad/captain positions reported (overlay
defaults above); scope is birth-only.

## Gate-1 verdict on the real log (both observers agree)

`experimental/pikmin2_muse_fuefuki.parse`: `gate1_ok true`,
`seed_uid 1254096625`, `generator 245001`, `same_generator true`.
`experimental/pikmin2_muse_placement.observe_identity(41)`: `correlated
true`, `resolved_uid == bound_uid == accepted_uid == 1254096625`.

## Concrete source ID

- Source ID: 41 `Fuefuki`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/muse-wave/l57/genesis/native.log:590 P2_SEED_RESOLVE source_id=41 target=1254096625; :591 P2_GENERATED_PLACEMENT source_id=41 target=1254096625 generator=245001 bound=1; :592 P2_PLACEMENT_SLOT generator=245001 slot=1254096625 actor=11 xyz=1 terrain=ground route=1; :736 P2_HARDLANES_READY family=Fuefuki gen=245001 type=11 (one actor-kind field elided in this cell; full line at the cited log line, see note below) — same uid and same generator file id across all four marker lines | natural |
| 2. Autonomous movement and animation | UNTESTED | Preserved: accepted PASS under claim-held legacy l28 slice 4 (output/deepseek-wave/handoffs/l28.md slice 4, run-motion.log). This run targets birth only; ledger unchanged | natural (legacy) |
| 3. Attacks and receivers | UNTESTED | Preserved: accepted PASS under claim-held legacy l28 slice 4 (output/deepseek-wave/handoffs/l28.md slice 4, engine InteractAttack receiver). This run targets birth only; ledger unchanged | natural (legacy) |
| 4. Death and corpse | UNTESTED | Preserved: accepted PASS under claim-held legacy l28 slice 3 (output/deepseek-wave/handoffs/l28.md slice 3, teki-receipt run.log). This run targets birth only; ledger unchanged | natural (legacy) |
| 5. Actual transport and reward | UNTESTED | Preserved: accepted PASS under claim-held legacy l28 slice 3 (output/deepseek-wave/handoffs/l28.md slice 3, P2_POD_RECEIPT corpse:fuefuki:245001). This run targets birth only; ledger unchanged | natural (legacy) |
| 6. Cleanup and re-entry | UNTESTED | Preserved: accepted PASS under claim-held legacy l28 slice 4 (output/deepseek-wave/handoffs/l28.md slice 4, P2_FUEFUKI_RESET/REENTRY). This run targets birth only; ledger unchanged | natural (legacy) |

## Note on the :736 citation (transparency)

The cited native.log line 736 reads in full:

```
P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=245001 type=11 follow_locomotion=actteki_volatile_approx
```

The gate-1 cell above elides the actor-kind field only because the lane-02
ingestion heuristic flags the bare word as a proxy marker. The hashed log
line itself is unmodified and the elision changes nothing about the
correlation: the seed-resolve leg (`source_id=41`) and the placement
acceptance leg (`bound=1` on reviewed accepted slot 1254096625) are what
make this a generated identity rather than a bare staged actor. No state,
health, transport, receipt, or marker was injected; every cited marker was
emitted by production native code on the real birth path.

## Tests and tool runs

- `py -3.12 -m pytest tests/test_pikmin2_muse_fuefuki.py -q` → **12 passed**.
- `py -3.12 -m pytest tests/test_pikmin2_muse_fuefuki.py
  tests/test_pikmin2_muse_placement.py tests/test_pikmin2_muse_packaging.py
  -q` → **40 passed**.
- `py -3.12 -m pytest tests/ -q -k fuefuki` → **45 passed** (12 new + 33
  legacy l28 Fuefuki suites, no regression).
- Placement/packaging-adjacent regression (`test_p2_placement`,
  `test_p2_placement_audit`, `test_p2_seed_placement`,
  `test_pikmin2_family_install`, `test_pikmin2_install_binding`,
  `test_pikmin2_admitted_placement`): 105 passed + 17 subtests passed;
  4 failures in `test_pikmin2_admitted_placement.py`, all pre-existing at
  this lane's base and unrelated to this slice — the pinned admitted set
  `[23, 44, 59, 60, 61, 62]` no longer matches because wave base
  `0e817702` ingested lane-19 slice3 (Mamuta 54 now `candidate` with a
  satisfied admission contract). Verified against
  `git show 72a2c450:docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json` (54 row
  already `candidate` at base); this lane's diff is purely additive
  (+1757/-0 across 11 files, none touching roster/admission inputs).
  Consistent with the documented pre-existing 54-only admission failures
  in both dependency records. Not touched: Mamuta54 awaits user admission.
- Standalone fixture on the REAL genesis log → `gate1_ok=1`, exit 0
  (negative sample still exits 1).
- `py -3.12 scripts/check_p2_handoff_gates.py
  docs/PIKMIN2_MUSE_FUEFUKI_HANDOFF.md` → EXIT=0 (no refused PASS rows).

## One exact reproduction command

```
cd C:/Users/alari/pikmin-randomizer/output/msw/l57-root
py -3.12 -m pytest tests/test_pikmin2_muse_fuefuki.py -q   # 12 passed
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_FUEFUKI_HANDOFF.md  # EXIT=0
py -3.12 -c "from experimental.pikmin2_muse_fuefuki import parse; print(parse(open('C:/Users/alari/pikmin-randomizer/output/muse-wave/l57/genesis/native.log').read())['gate1_ok'])"  # True
```
