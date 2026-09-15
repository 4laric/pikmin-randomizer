# Lane 15 — DeepSeek handoff (fix2): NaN resolved — real Honeywisp carried-Egg reward (#166)

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: DeepSeek (deepseek-v4-pro). This records ONE slice (real
carried-Egg reward) plus the fix1/fix2 control runs that resolved and correctly
attributed the movement NaN. Not full-lane or whole-family sign-off.

## Slice delivered

**Source ID owned: `EnemyID_Qurione` (16, Honeywisp).** Real carried-Egg reward
ownership. The integrated `pc_p2_qurione` module now reuses the lane-20 `P2Egg`
policy (`pc_p2_egg_hazard.*`) as a *consumer*:
- bind: `P2Egg::birth(false)` + `onStartCapture()` → real carried Egg;
- Drop: `onEndCapture()`; released Egg falls under bounded host gravity, `bounce()`
  on floor contact, then `P2Egg::update()` births the source drop table as real P1
  items (nectar via `OBJTYPE_Water`, pellets via `pelletMgr`, mitites→nectar);
  Spicy/Bitter unsupported; item spawn offset by `drop.positionOffsetY`.

## Source IDs and files owned

- Native `output/dsw/native-l15` (branch `deepseek/p2-l15-native`):
  - `pc_port/pc_p2_qurione.cpp` (only file changed). Markers: `P2_QURIONE_EGG_REAL
    born=1 drop_group=0` / `released=1`, `P2_QURIONE_EGG_BOUNCE`,
    `P2_QURIONE_EGG_BREAK`, `P2_QURIONE_EGG_ITEM`.
- Root `output/dsw/l15-root` (branch `deepseek/p2-l15`):
  - `experimental/pikmin2_qurione_arena.py` (removed the invalid 203002 control)
  - `experimental/pikmin2_qurione_lifecycle.py` (real markers, partial/partial gate
    wording, `passed_real` + `no_movement_nan` gates)
  - `experimental/pikmin2_qurione_runtime.py` (anchored regex)
  - `tests/test_pikmin2_qurione_lifecycle.py` (20 tests)
  - `docs/PIKMIN2_QURIONE_LIFECYCLE.md`, `docs/PIKMIN2_LANE15_DEEPSEEK_HANDOFF.md`

No shared-file changes ship.

## Ordered commits

Root (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):
1. `a89996b` lane15: grade real carried-Egg reward in Qurione lifecycle contract (#166)
2. `9924fbc` lane15: record carried-Egg reward handoff and gate-5 update (#166)
3. `0d24fe0` lane15: review fixes - partial gate wording, anchored runtime regex, passed_real gate (#166)
4. `abaf3d2` lane15: review-fix1 handoff, NaN localization, partial gate wording (#166)
5. `c2094cd` lane15: review fixes 2 - drop 203002 control, NaN resolved (#166)

Native (base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`):
1. `d1a579f3` lane15: Qurione carries real Egg reward via lane-20 P2Egg policy (#166)
2. `7fa5eb01` lane15: review fix - apply egg drop positionOffsetY to birthed items (#166)

## Interfaces / hooks touched

None new. Consumes lane-20 `P2Egg` + P1 `itemMgr`/`pelletMgr`. **Request to
lane 20:** extract a shared `pc_p2_egg_birth_items()` helper (the birth mapping
is duplicated in `pc_p2_projectiles.cpp` and `qurioneEggBirthItems`).

## Build evidence (`output/dsw/l15-build-evidence.txt`)

- **Lane build** (Ninja + MinGW g++ 16.2.0, Release, JAUDIO ON): native head
  `7fa5eb01232f58bb45e32bb56417861c87e58ef2`, dirty=no, exe SHA-256
  `ae91120369957fd58035032ce3508489ab5e3d7930293f9f9a6714638648012c`, `ninja -n`
  no-work.
- **Base build** (unmodified `b805d9c6`, separate worktree
  `output/dsw/native-l15-base` + build dir `native-l15-base-build`): 603/603, exe
  SHA-256 `0a9e500a8c0343dd006e0096c4642b268aedf43c6d631122744f2c34017236a1`,
  `ninja -n` no-work; evidence line pinned to
  `b805d9c626e4f4558c95aef7cac311a5d9a2068f`.

## Root cause and control runs

The movement NaN is **lane 15's own arena bug**, not shared code. The private
arena `experimental/pikmin2_qurione_arena.py` staged a second, un-suppressed
`TEKI_Qurione` actor (203002 "P1 Honeywisp") by cloning the Chappy `iket` enemy
template and forcing byte 80 to 6 — a Frankensteined Honeywisp with a Chappy
personality running ordinary P1 TaiMizinko AI. Its P1 state drove the registered
wisp's position to NaN. Control runs (all logged under `output/dsw/l15-out/`):

| Run | Build | Arena (203002) | Outcome |
|---|---|---|---|
| `04f345…/qurione-run.log` (fix1) | lane | present | `mSRT.t` NaN, stuck Stay |
| `4b23ece…/base-run.log` | **unmodified base `b805d9c6`** | **removed** | finite `stay→appear→move`, **no EGG_REAL line**, 0 `=nan` |
| `4b23ece…/lane-run.log` | lane `7fa5eb01` (clean) | **removed** | finite `stay→appear→move`, `born=1`, 0 `=nan` |

The base log contains no `P2_QURIONE_EGG_REAL` (that marker only exists on the
lane build), confirming the base build is genuine. Removing 203002 is the only
variable; both builds then fly finite. Owning lane: **15** (this arena), not
lane 07. The fix1 `isnan(mSRT.t)` `moveNew` probes were a red herring: the first
NaN was observed *after* the normal `moveNew` pass because the actor entered that
pass with a non-finite `mVelocity`, which originated in the neighboring
un-suppressed 203002 actor's P1 state — the trace probes never implicated shared
code, and the code in question is byte-identical to the working `f14c6851`
lineage.

## `14a94a2a` (flight-height hold) — reverted

During fix1 I hypothesised the NaN was the hidden wisp sitting at ground altitude
and committed `14a94a2a` (snap wisp to flight height in Stay). It did **not**
resolve the NaN (wrong mechanism), so it was reverted (`git reset --hard
7fa5eb01`) and is no longer on the branch. With 203002 removed the wisp flies to
flight height naturally via the Move-state pitch bob, so the hold is unnecessary.

## Six-gate table (natural vs injected)

| Gate | Result | Evidence |
|---|---|---|
| 1 identity/spawn | **PASS** | `source_id=16`, matched XYZ, `P2_QURIONE_EGG_REAL born=1` |
| 2 movement/animation | **PARTIAL** | finite `stay→appear→move` flight once 203002 removed; disappear/drop legs not yet captured |
| 3 attacks/receivers | source-backed N/A | no attack; contact trigger is flyCollisionCallBack |
| 4 death/corpse | **UNTESTED** | drop→dead needs a Pikmin drop trigger |
| 5 transport/reward | **PARTIAL** | attach + real Egg born observed live; release/break/item-birth contract-only |
| 6 cleanup/re-entry | **UNTESTED** | requires a death path |

Injected state: none. All observations are natural engine execution.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_qurione_lifecycle.py -q` → **20 passed**
(adds `passed_real` and `no_movement_nan` regression guards). Full flying-family
suite remains green (79 passed + 14 subtests across the other files).

## Subagent usage

Three subagents spawned in parallel at the start of fix2:
1. `explore` — TaiMizinko/Qurione bind-state audit (which fields are finite at
   birth, which runtime path can NaN). **Used as-is**; confirmed birth init is
   finite and that the suppressed path's only NaN writer is the Move-state
   moveFaceDir analogue, which pointed the investigation at the neighboring
   203002 actor rather than shared init code.
2. `explore` — diffed the two known-good mixed arenas today against this arena.
   **Used as-is (decisive)**: the working arenas use Chappy controls and a minimal
   `room.mod` roster, while this arena added the un-suppressed 203002 TEKI_Qurione
   control — the exact row whose removal fixed the NaN.
3. `general` — added the `P2_QURIONE_POS … <nan>` regression guard to the
   validator + two pytest cases (20 pass). **Used as-is.**
Net effect: the arena-diff subagent saved the biggest step (pinpointing 203002);
the audit saved re-deriving the finite-birth facts. No subagent built, ran a
fixture, committed, or touched native/shared sources.

## Assumptions

- Reusing lane-20 `P2Egg` is a legitimate consumer; P2 Eggs break on floor impact
  (not hauled), so a policy object with real item births is the correct host.
- Host gravity/terminal fall are bounded approximations (documented constants).

## Remaining work

Finite movement is restored; the natural reward chain still needs a Pikmin drop
trigger in this arena (the idle 20-red squad never touches the wisp within
`HIT_RADIUS`, and the practice-stage terrain slows the Move leg) to capture
`drop → dead → Egg release → break → item birth` and the disappear/stay leg.
That is the next bounded slice, not a blocker on shared code.

## Exact reproduction command

```powershell
# lane build already configured (JAUDIO ON) and built at 7fa5eb01
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l15

# bank + arena (203002 removed) [root worktree]
$env:PYTHONUTF8='1'
py -3.12 -m experimental.pikmin2_qurione_assets --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l15-out/qurione-bank" --pose-limit 4
py -3.12 -m experimental.pikmin2_qurione_arena --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --bank "C:/Users/alari/pikmin-randomizer/output/dsw/l15-out/qurione-bank" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l15-out/arena-runs" --source-sha256 "86ac5aa8f1d2a110badc15e01e2f7264a972fc1d35f0159277628c5d93903934"

# runtime (GL slot, 75 s)
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l15 -- py -3.12 run_fixture.py "C:/Users/alari/pikmin-randomizer/output/dsw/native-l15-build/bin/nectar.exe" "<arena-run-dir>" "<arena-run-dir>/qurione-run.log" 75
```

Notes: `run_fixture.py` (in `output/dsw/l15-out/`) sets `PIKMIN_P2_ROOM_WINDOW=960x540`,
`PYTHONUTF8=1`, and prepends the MinGW bin to PATH. The arena stages a read-only
junction `native/pikmin2-research` → the shared decomp checkout for the asset
extractor.
