# Muse l64 Breadbug38 natural lifecycle handoff (#504)

Implementation owner: Codex through shared account 4laric. Executing
contributor: Muse Spark 1.3 Contributor via OpenCode
(opencode/muse-spark-1.3-contributor-free), lane muse-breadbug (l64),
session ses_f588f5ecbffewB4l1dbImg41Ak, generation 2.
Parent #220; wave #491; integration #437/#186.

## Scope

PanModoki source 38 only (P1 TEKI_Collec proxy 186081; control 186082
untouched sentinel). Natural death/corpse and cleanup/re-entry evidence first,
then movement. Lane-18 ownership/cargo-contest behavior preserved by
reference, never re-implemented. No giant variant, no generic cargo host, no
shared receipt edits. P2 FSM motion is absent by design (P1 locomotion stays
authoritative); this is stated in every movement claim, never disguised.

## Source IDs and files owned

- Concrete source enemy: **38 PanModoki** (small Breadbug), native
  `TEKI_Collec` (type 8), generator 186081 in the fresh private proxy arena.
- Root (this lane): `experimental/pikmin2_muse_breadbug.py` (observer: stage,
  build, run, parse, validate), `tests/test_pikmin2_muse_breadbug.py` (25
  focused regression tests), `docs/PIKMIN2_MUSE_BREADBUG_HANDOFF.md` (this
  file).
- Native (this lane): `pc_port/pc_p2_breadbug_actor.{h,cpp}` (additive
  FORGET/DEATH/REBIRTH markers, per-tick rebirth scan, read-only tracked
  queries), `native/tools/p2_muse_breadbug_fixture.cpp` (private
  replacement-main lifecycle fixture).
- Dependency reuse without edits: lane-18 contest bridge
  (`pc_p2_breadbug_contest_host`), lane-06/07 lifetime seams
  (`pc_p2_forget_teki`, `pc_p2_reset_all_teki`), reviewed #437 fixture
  builder already present at the pinned root base.

## Ordered commits

Root worktree `codex/muse-l64-breadbug`, base
`72a2c450d7b9040545de4a440c2c32e2173ea6fa`:

1. `b5b68959409e443698b625b3350e963175a7d78a` observer + 19-test regression
2. `87b8083ea19424cf2841abe55732d4892fb1331c` thrown-Pikmin kill path
   (free-mode ring dealt zero damage in 2400 ticks)
3. `92c9d0cb48895463142b248d6eff3841c463ca39` validator mirrors proven run
   shape (this handoff's observer state)
4. (this handoff commit) six-gate handoff doc

Root HEAD (see handoff.json), clean.

Native worktree `codex/muse-l64-breadbug-native`, base
`7b9ecaa668fd55332073446cdbdaf6424b209ea7`:

1. `6ab0b1aa1c294dc0c2608cc5c8c8e7b8158ad7c1` markers + fixture skeleton
2. `006278b0eed23c9bc368befe1e23e5d4e68dbccd` wantedIds build fix
3. `44cbb62dcb53cbdff8311adc951ecf65a6ac8637` captain-thrown assault
4. `8015b784b6a06f21540cdcd859eb8b1652282cd6` mDeadState==2 corpse timing
5. `1aba5b0454b7aeff4ce15f735e37247ad542e40a` rebirth scan counts live
   bindings

Native HEAD `1aba5b0454b7aeff4ce15f735e37247ad542e40a`, clean.

## Interfaces / hooks touched and why

- `pc_p2_breadbug_actor.cpp` only (family module): FORGET marker
  (`had_handle`, honest `dead_state`), residual DEATH marker (`corpse` from
  `mPellet`, `held` from pre-release pointer), REBIRTH re-registration scan
  (live-binding count gate, stale dead same-id erase with `replaced_stale`),
  read-only `tracked_count`/`is_tracked` probes. No edits to `teki.h`,
  `tekibteki.cpp`, `tekimgr.cpp`, `gameCoreSection.cpp`, `pc_p2_preview.cpp`,
  the contest bridge, or any other family module.
- Root: observer + tests + this doc. No shared-script edits; the reviewed
  #437 response-file-capable builder at the pinned base was used as-is.

## Build evidence

- Leased private build, generation 2:
  `output/muse-wave/l64/build-1789528456422843500.log`, exit 0, native head
  `1aba5b0454b7aeff4ce15f735e37247ad542e40a`, dirty empty,
  `bin/nectar.exe` sha256
  `68074f77bc8b8f2164051f55ee7f49d5828815705e1e1d460c4e12f73d0ed1f2`,
  `ninja: no work to do.` dry run in the same log.
- Fixture provenance: `output/muse-wave/l64/fixture-1aba5b04/baseline/provenance.json`
  status `built` (expected/observed head `1aba5b04…`, clean);
  artifact `baseline/fixture.exe` sha256
  `5fe318ba2ab0f19f604b7b61f6b81ea7b8ac40189f6eca5bf051c5aa6b203348`.

## Fixture adoption evidence

Full record: `output/muse-wave/l64/adoption-1aba5b04.md`. Fresh arena
`output/muse-wave/l64/stage-1aba5b04` from current `overlay()` (20-red
starting squad, valid terrain); accepted run `output/muse-wave/l64/run-1aba5b04b`
(supplement `run-1aba5b04`); `PIKMIN_P2_ROOM_WINDOW=960x540`, silent audio;
observed 960x540 centered window, live squad, active gameplay, no extinction.

## Runtime evidence (private real-GL, 960x540)

Accepted run `output/muse-wave/l64/run-1aba5b04b/host.log` (sha256
`2e9ada21838d0d903d0926fe6f6bcb1db56c178af40722a14716376f57c1ee04`;
log-line citations below are into this file):

- `:7` standard centered-window line; `:236` live 20-red squad.
- `:706` `P2_BREADBUG_ACTOR_READY generator=186081 native_type=8
  xyz=-150.000000,30.000000,1850.000000` — exactly one READY in the log (no
  manager recreation).
- `:758` live visual delegation; `:759` `P2_MUSE_BREADBUG_MOVED
  displacement=15.849366 moving=15` (P1 locomotion sample).
- `:760-:1114` 286 captain-thrown reds (`Navi::throwPiki`, staged throw-range
  captain positions); health `5000.0` → first fall at `:1051` → `200.0` at
  `:1107` → `0.0` at `:1111`. Zero fixture health writes, no `die()` call,
  no injected damage (no `P2_MUSE_BREADBUG_INJECTED` marker exists).
- `:1117` `P2_MUSE_BREADBUG_KILL_NATURAL`; `:1118` residual DEATH;
  `:1122` `P2_MUSE_BREADBUG_CORPSE bodies=1 via_mpellet=1` (dieSoon product
  at `mDeadState==2` plus pelletMgr `mPelletView` scan).
- No `P2_BREADBUG_ACTOR_FORGET` anywhere: for a LeaveCorpse death the engine
  never reaches `BTeki::doKill` (`tekibteki.cpp:734-735` takes the
  `becomeCorpse()` branch instead of `kill(false)`), so no per-actor funnel
  marker exists. The dead family entry persists (bounded staleness, cleared
  on rebirth or stage reset — `pc_p2_breadbug_actor_reset()`).
- `:1123` rebirth wait begins; no natural generator respawn within 600 ticks
  (the preview room never respawns on its own), so one staged
  `mGenType->init` rebirth on the captured generator (groink/fuefuki
  rehearsal precedent; honestly marked in-log). The re-REGISTRATION is fully
  natural: `:1155` `P2_BREADBUG_ACTOR_REBIRTH ... replaced_stale=1` from the
  family per-tick scan with no reset/setup call, `:1160` recycled=0,
  validator confirms exactly one live binding and still exactly one READY.
- Repeat run `run-1aba5b04/host.log`: kill tick 2136, corpse 1/1, rebirth
  `replaced_stale=1`, recycled=0 — same shape, second consecutive natural
  lifecycle.
- Negative results kept: free-mode ring (lane-19 recipe) dealt zero damage
  in 2400 ticks (`stage-006278b0/host.log`: health pinned `5000.0`,
  `FAIL ... natural kill did not complete`); early corpse read at
  `mDeadState==1` yields `bodies=0 via_mpellet=0` (timing fixed by waiting
  for `mDeadState==2`).

## Six-gate table (ingest contract)

## Concrete source ID

- Source ID: 38 `PanModoki`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_MUSE_BREADBUG_HANDOFF.md output/muse-wave/l64/run-1aba5b04b/result.json | natural |
| 2. Autonomous movement and animation | PASS (natural, P1 locomotion) | docs/PIKMIN2_MUSE_BREADBUG_HANDOFF.md output/muse-wave/l64/run-1aba5b04b/result.json | natural |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_MUSE_BREADBUG_HANDOFF.md output/muse-wave/l64/run-1aba5b04b/result.json | natural |
| 4. Death and corpse | PASS (natural) | docs/PIKMIN2_MUSE_BREADBUG_HANDOFF.md output/muse-wave/l64/run-1aba5b04b/result.json | natural |
| 5. Actual transport and reward | PASS (natural, lane-18 acceptance preserved) | docs/PIKMIN2_LANE18_DEEPSEEK_HANDOFF.md | natural |
| 6. Cleanup and re-entry | PASS (natural, staged rebirth timing) | docs/PIKMIN2_MUSE_BREADBUG_HANDOFF.md output/muse-wave/l64/run-1aba5b04b/result.json | natural |

Row notes (kept out of the machine-read cells): gate 1 corroborates the
lane-18 accepted spawn (single READY, native_type=8, birth XYZ). Gate 2 is P1
locomotion only — the DRAW marker itself records `no_P2_FSM`; no P2 motion is
claimed. Gate 3 evidence is the thrown-red receiver series starting at the
cited line (5000 down to 200 across the following RING lines) plus the
lane-18 accepted contest path, which is preserved untouched. Gate 5 is not
re-proven here: the lane-18 exactly-once contest grant plus ordinary Onion
delivery acceptance stands, cited as-is. Gate 6: re-registration is natural
(family scan, no reset/setup, exactly one live binding, control actor
untouched); the rebirth *timing* was staged (one generator init after 600
idle ticks, marked in-log) because the preview room never respawns alone;
per-actor forget is absent for LeaveCorpse deaths (see Runtime evidence) and
is therefore documented, not claimed.

## Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_muse_breadbug.py -q` → **25
  passed** (synthetic-log regression incl. negative tests for injection,
  vacuous movement, duplicate death, manager recreation, and slot-reuse
  misread as funnel). Log: `output/muse-wave/l64/checks-1aba5b04.log`.
- Real-log validation of both runs through
  `experimental.pikmin2_muse_breadbug validate` → passed all five internal
  gates, funnel reported absent, zero injected markers (same checks log).
- Native production build + `ninja -n` dry run: exit 0 (leased build log
  above). No native CTest touched (no engine-free unit added; the bridge
  consumer test is lane-18 owned).

## Assumptions and remaining work

- The staged captain throw positions are reported engine teleportation for
  camera/range staging; all damage flows through the real throw/latch
  receiver chain. Squad/captain staging and the bait-free scope limit are
  stated here.
- Actor visuals reuse lane-18 validated conversions hash-verified
  (stage-1aba5b04/breadbug-arena.json); no new conversion is claimed.
- Remaining: natural generator-respawn timing in a live room (provider:
  encounter scheduling, lane 04/01); P2 FSM motion (out of scope by design —
  proxy); transport reward re-proof under this fixture (lane-18 acceptance
  preserved, not re-run); human/integrator review of the gate-6 funnel
  documentation.

## Exact reproduction

```powershell
$env:PATH = 'C:/msys64/mingw64/bin;' + $env:PATH
$env:PYTHONUTF8 = '1'
$env:PIKMIN_P2_ROOM_WINDOW = '960x540'
$env:SDL_AUDIODRIVER = 'dummy'
# production build (leased):
py -3.12 C:/Users/alari/pikmin-randomizer/output/muse-wave/control/leased_run.py --lane-file C:\Users\alari\pikmin-randomizer\output\muse-wave\l64/lane.json
# fixture (leased), stage, run:
py -3.12 C:/Users/alari/pikmin-randomizer/output/muse-wave/control/leased_run.py --lane-file C:\Users\alari\pikmin-randomizer\output\muse-wave\l64/lane.json -- py -3.12 -m experimental.pikmin2_muse_breadbug build --native C:\Users\alari\pikmin-randomizer\output\msw\native-l64 --build-dir C:\Users\alari\pikmin-randomizer\output\msw\native-l64-build --output <NEW_OUT> --head 1aba5b0454b7aeff4ce15f735e37247ad542e40a
py -3.12 C:/Users/alari/pikmin-randomizer/output/muse-wave/l64/stage_arena.py
py -3.12 -m experimental.pikmin2_muse_breadbug run --stage <STAGE> --exe <FIXTURE_EXE> --output <RUN_OUT> --timeout 300
py -3.12 -m experimental.pikmin2_muse_breadbug validate --log <RUN_OUT>/host.log
```
