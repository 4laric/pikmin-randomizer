# Lane 15 — DeepSeek handoff (fix1): real Honeywisp carried-Egg reward (#166)

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: DeepSeek (deepseek-v4-pro). This records ONE slice (real
carried-Egg reward) plus the follow-up review-fix control runs; it is not
full-lane or whole-family sign-off.

## Slice delivered

**Source ID owned: `EnemyID_Qurione` (16, Honeywisp).** Real carried-Egg reward
ownership. The integrated `pc_p2_qurione` module previously printed
`P2_QURIONE_EGG action=attach|drop` markers only. It now reuses the integrated
lane-20 `P2Egg` policy (`pc_p2_egg_hazard.*`) as a *consumer*:
- bind: `P2Egg::birth(false)` + `onStartCapture()` → real carried Egg;
- Drop: `onEndCapture()`;
- released Egg falls under bounded host gravity, `bounce()` on floor contact
  (health 0), then `P2Egg::update()` builds the source drop table and births real
  P1 items: single/double nectar via `itemMgr->birth(OBJTYPE_Water)` (ItemHoney
  HONEY_Y), pellets via `pelletMgr->newNumberPellet(...)`; mitites downgrade to
  nectar (no P1 Mitite manager); Spicy/Bitter unsupported (first-spray demo flag).
  Item spawn in now offset by `drop.positionOffsetY` (egg.cpp:249).

## Source IDs and files owned

- Native worktree `output/dsw/native-l15` (branch `deepseek/p2-l15-native`):
  - `pc_port/pc_p2_qurione.cpp` (only file changed). New markers:
    `P2_QURIONE_EGG_REAL born=1 drop_group=0`, `... released=1`,
    `P2_QURIONE_EGG_BOUNCE`, `P2_QURIONE_EGG_BREAK`, `P2_QURIONE_EGG_ITEM`.
- Root worktree `output/dsw/l15-root` (branch `deepseek/p2-l15`):
  - `experimental/pikmin2_qurione_lifecycle.py` (REWARD real markers; `transport_reward` partial;
    `movement_animation` real blocker; validator `passed_real` gate)
  - `experimental/pikmin2_qurione_runtime.py` (anchored `re.search` for egg markers)
  - `tests/test_pikmin2_qurione_lifecycle.py` (3 new assertions/tests → 18 tests)
  - `docs/PIKMIN2_QURIONE_LIFECYCLE.md`, `docs/PIKMIN2_LANE15_DEEPSEEK_HANDOFF.md`

No shared-file edits ship (the temporary NaN-localization instrumentation in
`src/plugPikiKando/creature.cpp` and `src/plugPikiNakata/tekibteki.cpp` was
reverted after capture). No hooks added or shared semantics changed.

## Ordered commits

Root (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):
1. `a89996b` lane15: grade real carried-Egg reward in Qurione lifecycle contract (#166)
2. `9924fbc` lane15: record carried-Egg reward handoff and gate-5 update (#166)
3. `0d24fe0` lane15: review fixes - partial gate wording, anchored runtime regex, passed_real gate (#166)
4. `(HEAD)`  lane15: review-fix1 handoff + NaN localization documentation (#166)

Native (base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`):
1. `d1a579f3` lane15: Qurione carries real Egg reward via lane-20 P2Egg policy (#166)
2. `7fa5eb01` lane15: review fix - apply egg drop positionOffsetY to birthed items (#166)

Both worktrees clean at handoff.

## Interfaces / hooks touched

None new. Consumes lane-20 `P2Egg` and the P1 `itemMgr`/`pelletMgr` birth
interfaces. **Request to lane 20:** extract a shared `pc_p2_egg_birth_items()`
helper (the birth mapping is duplicated in `pc_p2_projectiles.cpp::birthEggDrop`
and lane-15 `qurioneEggBirthItems`); lane 15 will consume it rather than fork
further.

## Build evidence (`output/dsw/l15-build-evidence.txt`)

- Ninja + MinGW g++ 16.2.0, Release, `-DPIKMIN_NATIVE_JAUDIO=ON`.
- Native head `7fa5eb01232f58bb45e32bb56417861c87e58ef2`, dirty=no.
- `nectar.exe` SHA-256 `ae91120369957fd58035032ce3508489ab5e3d7930293f9f9a6714638648012c`.
- `cmake --build ... --target pikmin_pc -- -n` → `ninja: no work to do.`

## Review-fix1 control runs (A) and NaN localization (B)

Control runs, both logged under `output/dsw/l15-out/arena-runs/`:

| Run | Build | Wisp position | `mSRT.t` outcome |
|---|---|---|---|
| (1) `04f345bfff0b…/qurione-run.log` | **unmodified base `b805d9c6`** (worktree `native-l15-base`, 603/603) | (-150, 30, 1850) | **NaN** within ~1 s, still Stay |
| (2) `1b5a120775db…/qurione-run.log` | lane build `d1a579f3` | (-50, 30, 1750) | **NaN** within ~1 s, still Stay |

Both reproduce → **not placement-local** and **not introduced by the Egg slice**
(the base build reproduces it). Not the lane-02 mixed run's (-50,30,1750),
because that ran on base `f14c6851`, an earlier ancestor without the regression.

Localization (temporary `isnan(mSRT.t)` probes after each `moveNew` pass in
`Creature::update` and after each hook in `BTeki::update`, then reverted):

```text
[PC_L15_TRACE] f=0 p1 nan=0 x=-150.00 y=30.00 z=1850.00   (source, frame 0)
[PC_L15_TRACE] f=1 p1 nan=0 x=149.94 y=148.84 z=1549.34     (P1 control flying)
[PC_L15_TRACE] f=2 p1 nan=0 x=-150.00 y=30.00 z=1850.00     (source, finite after volatile pass)
[PC_L15_TRACE] f=2 p2 nan=1 x=nan y=nan z=nan               (first NaN after normal pass)
```

**First NaN writer:** the normal `moveNew(deltaTime)` pass — `creature.cpp:801`
— whose only position writer is `MapMgr::traceMove` (`creatureMove.cpp:232
mSRT.t = trace.mPosition` → `mapMgr.cpp:2339 traceMove` / `:2156 recTraceMove`).
It is NOT any `pc_p2_*` hook (the `after Creature::update` probe already sees NaN
for generator 203001) and NOT the Egg slice. The P1 control (un-suppressed
Mizinko AI, flown to y≈148) stays finite, so the trigger is specific to the
FSM-held wisp at spawn altitude with the current trace code. `MapMgr` was not
touched.

## Six-gate table (natural vs injected)

| Gate | Result | Evidence |
|---|---|---|
| 1 identity/spawn | **PASS** (natural) | `source_id=16`, birth XYZ matched, `P2_QURIONE_EGG_REAL born=1` |
| 2 movement/animation | **BLOCKED** | wisp `mSRT.t`→NaN on the normal moveNew pass (regardless of -150/-50), never leaves Stay |
| 3 attacks/receivers | source-backed N/A | no attack; contact trigger is `flyCollisionCallBack` |
| 4 death/corpse | **UNTESTED** | drop→dead unreachable while movement blocked |
| 5 transport/reward | **PARTIAL** | attach + real Egg born observed live; release/break/item-birth contract-only |
| 6 cleanup/re-entry | **UNTESTED** | requires a death path (#2/#4) |

Injected state: none. All observations are natural engine execution.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_qurione_lifecycle.py -q` → **18 passed**
(added `passed_real` assertions + full-chain regression test). Full flying suite:
79 passed, 14 subtests (unchanged apart from the lifecycle file).

## Subagent usage

Three subagents were spawned in parallel at the start of this slice:
1. `explore` — source audit of Qurione + Egg (states, keyevents, parms, drop
   table). **Used as-is**; corrected my assumption that Egg fp01..fp05 disc values
   are visible — they are header defaults 1.0, and the 0.5/0.35/0.05/0.05/0.05
   figures come from the lane-20 projectiles doc, which the P2Egg test also uses.
2. `explore` — existing-candidate inventory (root + native). **Used as-is**;
   confirmed all marker strings and hook line numbers, and listed the runner/doc
   surfaces referenced in the handoff.
3. `general` — extended the lifecycle pytest for the `passed_real` gate and ran it
   (18 passed). **Used as-is** (added the requested assertions verbatim).
Net effect: saved roughly one full rebuild/test confidence pass and made the
handoff citations auditable; no subagent built, ran a fixture, committed, or
touched native/shared sources.

## Assumptions

- Reusing lane-20 `P2Egg` as a policy object is a legitimate consumer (the module
  header states "a future host integration owns capture/fall physics, the
  item/pellet births").
- Because the P1 engine has no physical Egg creature, the released Egg is a policy
  object; P2 Eggs break on floor impact, not hauled.
- Host gravity/terminal fall are bounded approximations (documented constants).

## Remaining blockers (provider lane)

1. **First NaN writer localized to `creature.cpp:801` (normal `moveNew` pass) →
   `MapMgr::traceMove`/`recTraceMove` (shared).** Owning lane **07** (shared
   lifetime/fixture + Teki update-order infrastructure). Reproducible on the
   unmodified base `b805d9c6` with control-run evidence above; the wisp's natural
   appear→move→drop→dead→Egg-break chain cannot run until this is fixed.
2. Cleanup/re-entry still tied to the shared #397 lifetime seam once movement is fixed.

## Exact reproduction command

```powershell
# native worktree already configured (JAUDIO ON) and built at 7fa5eb01
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l15

# bank + arena (root worktree)
$env:PYTHONUTF8='1'
py -3.12 -m experimental.pikmin2_qurione_assets --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l15-out/qurione-bank" --pose-limit 4
py -3.12 -m experimental.pikmin2_qurione_arena --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --bank "C:/Users/alari/pikmin-randomizer/output/dsw/l15-out/qurione-bank" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l15-out/arena-runs" --source-sha256 "86ac5aa8f1d2a110badc15e01e2f7264a972fc1d35f0159277628c5d93903934"

# runtime (GL slot, 60 s)
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l15 -- py -3.12 run_fixture.py "C:/Users/alari/pikmin-randomizer/output/dsw/native-l15-build/bin/nectar.exe" "<arena-run-dir>" "<arena-run-dir>/qurione-run.log" 60
```

Notes: `run_fixture.py` (in `output/dsw/l15-out/`) sets `PIKMIN_P2_ROOM_WINDOW=960x540`,
`PYTHONUTF8=1`, and prepends the MinGW bin to PATH. `run_fixture.py` + the arena
stage `native/pikmin2-research` read-only junction → the shared decomp checkout.
