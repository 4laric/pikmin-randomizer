# Muse Tadpole handoff - natural death/corpse + re-entry observer (shard, #374)

Worker: Muse Spark 1.3 (`opencode-go/muse-spark-1.3-contributor`, lane
shard-enemies-6-tadpole27-observer, generation 3). Implementation owner: Codex
through shared GitHub account `4laric`. Parent #167; family lane #374.
Source ID 27 Tadpole (Wogpole) is the slice target.

## Scope result

Gates 4 (`death_corpse`) and 6 (`cleanup_reentry`) are closed with a real
thrown-Pikmin / player-controller event path on a live bound actor, following
the merged armor15 observer precedent. The legacy batch-1 acceptance used an
injected `mHealth=0` kill; this run removes that substitute: one staged
captain position parked 400 units east of the TARGET birth anchor (outside
every actor attack reach; captain guard #632 active, never tripped), genuine
`Navi::throwPiki` throw-release events (18 throws, HP trail 200.0 -> 0 logged
per throw), ballistic flight plus the Pikmin own engagement, and latched
stick attacks draining the native 200-HP pool through the untouched family
FSM, which raises TADPOLE_DEAD itself and calls `actor->die()`. The port
suppresses doAI for family actors so the engine dieSoon funnel never runs
alone (proven: dead actor lingered); the fragment drives the PUBLIC funnel
helper `pcEscapeNow()` once (`P2_TADPOLE_FUNNEL_DROVE`, no state written by
the fixture) and the real funnel spawns a bound corpse pellet. No
family-module change was needed. Gates 1/2 are preserved family PASS; gates
3/5 are preserved source-backed N/A; none are relabelled.

## Source ID

```
Source ID: 27 `Tadpole`
```

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | family `P2_TADPOLE_BIND generator=374002 source_id=27`; `P2_ENEMY_READY species=Tadpole native_family=Otama`; birth `native.log:1238`; preserved, not relabelled | natural |
| 2. Movement and animation | PASS (natural) | states wait/move/amaze/escape/leap, 77.6 XZ spread; docs/PIKMIN2_TADPOLE_NATIVE.md gate table; preserved, not relabelled | natural |
| 3. Attacks and receivers | PASS (source-backed N/A) | fp24=0 zero attack, no receiver raised; docs/PIKMIN2_TADPOLE_NATIVE.md attack row; preserved | source-backed N/A (harmless) |
| 4. Death and corpse | PASS (natural) | `native.log:1331` `P2_TADPOLE_DEAD`, `:1332` NATURAL_DEATH (18 throws), `:1333` DEATH_POS on floor, `:1335` FUNNEL_DROVE, `:1336` CORPSE_PRESENT | natural combat + engine funnel; zero substitutes |
| 5. Transport and reward | PASS (source-backed N/A) | no verified source loot drop per docs/PIKMIN2_TADPOLE_NATIVE.md; corpse pellet carrying not exercised; preserved | source-backed N/A |
| 6. Cleanup and re-entry | PASS (natural stage boundary) | pass2 `native.log:1242` REBOUND stale/fresh pointers differ + single re-bind `:734` | natural rebirth |

Gate detail (pass1 `death-run1/pass1/<uuid>/native.log`, 1338 lines; pass2
`death-run1/pass2/<uuid>/native.log`, 1243 lines):

- Gate 4: staged captain once (`:1242`, 400 east of birth, outside attack
  reach), 18 genuine throw-release events (`:1243`-`:1327`, HP trail 200.0 down to
  65.0 to 0), family `P2_TADPOLE_DEAD` at `:1331`, `NATURAL_DEATH` at `:1332`
  (tick 216, throws=18), death position on the arena floor at `:1333`
  (y=5.19 vs ground=4.56; fall deaths are machine-rejected), driven funnel at
  `:1335`, engine-born corpse pellet at `:1336`, `PASS` at `:1338` with exit 0.
  A legacy forced-kill log (DEAD row, no throws) is rejected by the validator
  (unit-tested).
- Gate 6: fresh process over the same arena definition; exactly one family
  re-bind (`:734`); `REBOUND` at `:1242` proves the fresh pointer differs from
  the pass-1 stale pointer; families reset/forget seams run on the stage load;
  `PASS` at `:1243` with exit 0.
- Honesty notes: the squad waits rather than forcing when no throwable Pikmin
  is ready (`THROW_SKIP` rows with Normal/throwable census); other roster
  actors (Catfish/Jigumo/UmiMushi) wander free; the corpse pellet was observed
  bound to the dead actor but never carried (gate 5 stays N/A); no mHealth/HP
  write exists anywhere in the fixture (machine-audited: single
  `resetPosition`, no `startAction`/`mMode`/`mHealth=`/holders); the captain
  guard never tripped (no CAPTAIN_DOWN).

## Source IDs and files owned

- Source IDs: 27 Tadpole (slice target).
- Native (worktree `output/workflow/autofill/planning-shards/enemies-6/prepared/tadpole27-observer-native`,
  branch `codex/shard-enemies-6-tadpole27-observer-native`):
  `tools/p2_muse_tadpole_fixture.cpp` (new, owned). `pc_port/pc_p2_tadpole.*`
  inspected, not modified (no defect reproduced; funnel uses the public
  `pcEscapeNow` helper).
- Root (worktree `.../prepared/tadpole27-observer`,
  branch `codex/shard-enemies-6-tadpole27-observer`):
  `experimental/pikmin2_muse_tadpole.py` (new),
  `tests/test_pikmin2_muse_tadpole.py` (new),
  `docs/PIKMIN2_MUSE_TADPOLE_HANDOFF.md` (this file).

## Ordered commits (dirty: clean on both)

Root (`codex/shard-enemies-6-tadpole27-observer`, base `8ff3001e4e469cf9d33430e0ff769c15738270e3`):
- TBD1 observer fixture/runner/tests/doc + death-pass evidence
- TBD2 funnel drive + captain guard #632 + rebirth evidence

Native (`codex/shard-enemies-6-tadpole27-observer-native`, base `6a87eb2994b66355b05ce40bf3a8823884236299`):
- TBD3 observer fixture fragment (+ funnel drive + captain guard)

Heads: root 585e75a418df7a8c7d08baa0e2940926e3ef62db (code), native 2d094d0f0f4baee0bf0721e9b958fff3a9fd05e; handoff head is this doc commit.

## Interfaces / hooks touched

- None in shared engine code. The fixture drives two public engine APIs
  exactly as the throw state machine does on `KEY_Action0`
  (`Piki::mFSM->transit(p, PIKISTATE_Flying)` + `Navi::throwPiki(p, aim)`
  after direct idle-Pikmin selection, the merged breadbug precedent), plus the
  public `pcEscapeNow()` death-funnel helper. Death travels the family FSM
  (`mHealth<=0` -> TADPOLE_DEAD -> `actor->die()` -> funnel), unchanged.
- One staged captain `Navi::resetPosition` at tick 1 (reported staging, not
  gameplay); everything else is engine AI/physics. Captain guard
  `p2_fixture_require_captain` (canonical `scripts/p2_fixture_captain_guard.h`
  sha256 `d2f678c9...3474`, vendored) runs before every pause/movie return and
  observed tick.

## Build evidence

- Private build dir `output/tadpole27-build`, native `6a87eb2994b66355b05ce40bf3a8823884236299`
  (dirty: only the new untracked fixture file); `pikmin_pc` linked, `ninja:
  no work to do.` dry run. Log `output/workflow/autofill/planning-shards/enemies-6/prepared/tadpole27-observer-output/build-1789579787826271900.log`.
  Production exe `bin/nectar.exe` sha256
  `e29055155c582c108d1f55ee44835e1934fe78a1d964a08883a6b0055421e037`.
- Fixture `tadpole27-fx9` provenance `built` for expected head `f2d094d0f0f4baee0bf0721e9b958fff3a9fd05e`;
  `fixture.exe` sha256
  `405968a4128270db4a3c7298b0b6fa624edf0629d0f776d8bb2badff46e80e51`
  -- the binary that ran both acceptance passes.

## Fixture baseline adoption

```text
Fixture baseline adoption
Child issue / lane / implementation owner: #374 / shard-enemies-6-tadpole27-observer (gen 3) / Codex through shared 4laric; contributor Muse Spark 1.3
Root commit + dirty state / overlay source: 585e75a418df7a8c7d08baa0e2940926e3ef62db clean / scripts/preview_pikmin2_room.py overlay() with ensure_pikmin_squad (present)
Native commit + dirty state / worktree / private build directory: f2d094d0f0f4baee0bf0721e9b958fff3a9fd05e clean / tadpole27-observer-native / output/tadpole27-build
Squad change present / window change present (ancestry or source evidence): overlay squad helper present in worktree source; 960x540 centred-window default confirmed at runtime (see below)
Fresh arena command / run directory / asset and config hashes: py -3.12 -m experimental.pikmin2_muse_tadpole run --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --bank C:/Users/alari/pikmin-randomizer/output/dsw/l08-out --output .../death-run1 --exe .../tadpole27-fx9/fixture.exe / death-run1/pass1+pass2 / arena.json 7e21ddb2-
Executable SHA-256 / fixture provenance status if applicable: 405968a4...46e80e51 / built (expected head f2d094d0f0f4baee0bf0721e9b958fff3a9fd05e)
Window setting / observed size and centring evidence: PIKMIN_P2_ROOM_WINDOW=960x540 / native.log:2 SDL window 960x540, :7 preview window set to 960x540 windowed and centered (both passes)
Live starting Pikmin / active gameplay / no immediate extinction evidence: :1268 SQUAD pikis=20; throws/death/rebirth sequence; `:1338/:1243 PASS with exit 0; no extinction screen
Captain guard #632 adoption: vendored canonical guard (sha256 d2f678c9...3474); parked 400 east outside attack reach; never tripped (no CAPTAIN_DOWN in either log)
PASS, FAIL, or BLOCKED; remaining work: PASS for gates 4+6; Catfish26, Jigumo63, UmiMushi71/101 remain; admission still denied
```

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_muse_tadpole.py -q` -> 17 passed
  (validator accept/reject incl. injected-death-log discrimination,
  proxy-corpse/fall-death/duplicate-rebirth rejection, funnel requirement,
  CAPTAIN_DOWN blocked mapping, fixture audit).
- Runtime validators on the real logs: 13/13 death checks + 3/3 rebirth
  checks (`runtime-evidence.json` in each stage dir).

## Gate-check output

```
$ py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_TADPOLE_HANDOFF.md
27 Tadpole (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    accepted [PASS]
```

## Exact reproduction

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
$env:PYTHONPATH='C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards\enemies-6\prepared\tadpole27-observer'
py -3.12 C:/Users/alari/pikmin-randomizer/output/muse-wave/control/leased_run.py --lane-file C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards\enemies-6\prepared\tadpole27-observer-output/lane.json --configure
py -3.12 C:/Users/alari/pikmin-randomizer/output/muse-wave/control/leased_run.py --lane-file C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards\enemies-6\prepared\tadpole27-observer-output/lane.json -- py -3.12 -m experimental.pikmin2_muse_tadpole build --native <native> --build-dir C:\Users\alari\pikmin-randomizer\output\tadpole27-build --output C:\Users\alari\pikmin-randomizer\output\tadpole27-fx9 --head 6a87eb2994b66355b05ce40bf3a8823884236299
py -3.12 -m experimental.pikmin2_muse_tadpole run --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --bank C:/Users/alari/pikmin-randomizer/output/dsw/l08-out --output <run-dir> --exe C:/Users/alari/pikmin-randomizer/output/tadpole27-fx9/fixture.exe
```

Bank note: the visual/sidecar bank is the batch-1 validated install output
(`output/dsw/l08-out/aquatic`), consumed read-only (sidecar sha256 TBD as
staged); no other lane worktree, claim or verdict was edited.