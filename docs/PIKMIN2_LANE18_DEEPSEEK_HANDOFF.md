# Lane 18 DeepSeek handoff — fix1: small-Breadbug cargo-contest consumer (#220)

Implementation owner: Codex through shared account 4laric. Executing agent:
DeepSeek session, lane 18 (Breadbugs/nests). This is the **fix1** revision of the
lane-18 handoff (review note: NOT merged; the previous slice was a near-verbatim
clone of lane 06's ordinary-receipt fixture and made no progress on the real
lane-18 goal). This revision replaces that clone with the cargo-contest
**consumer** binding and relabels the gate evidence honestly.

## What changed (review fixes applied)

1. Deleted `scripts/p2_breadbug_ordinary_fixture.cpp`; parameterised the shared
   lane-06 fixture `scripts/p2_ordinary_receipt_fixture.cpp` (`--enemy-type`,
   `--check`) and upstreamed the phase-4 toast-stall exit fix (separately
   labelled commit `d4225ed`). `scripts/p2_breadbug_ordinary_runtime.py` now
   drives it with `--enemy-type 8 --check "Bestiary: Deliver Breadbug"`.
2. **Real slice:** bound the small Breadbug (`pc_port/pc_p2_breadbug_actor.cpp`
   TEKI_Collec proxy) to lane 06's `pc_port/pc_p2_cargo_contest.h`
   (`P2CargoContest`) through a new engine-free bridge
   (`pc_port/pc_p2_breadbug_contest_host.{h,cpp}`), which also owns the durable
   ordinary receipt ledger (`P2Receipt::FileReceiptPersistence`) and uses lane
   06's `pc_p2_delivery.h` `onion:p2:<id>:<stage>` identity keys.
3. Dropped the two tautological tests (`test_pikmin2_breadbug_ordinary.py`
   kept only the catalog/seed wiring tests 1-2).
4. Relabelled gate 3 (attack injected **before** START_READY, not "natural
   damage/FSM path"; the death driver uses a labelled `mHealth=0` injection) and
   gate 6 (exactly-once proof is the driver's `len(lines2)==0` / duplicate grant,
   not the fixture PASS line).

## Source IDs and files owned

- Concrete source enemy: **38 PanModoki** (small Breadbug), native `TEKI_Collec`
  (type 8), generator 186081 in the private proxy arena.
- Native (new/changed): `pc_port/pc_p2_breadbug_contest_host.{h,cpp}` (bridge),
  `pc_port/pc_p2_delivery.h` (ported lane-06 provider header),
  `pc_port/pc_p2_breadbug_actor.{h,cpp}` (consumer binding + probe hooks),
  `tools/p2_breadbug_contest_consumer_test.cpp`, `CMakeLists.txt`
  (source + CTest registration — shared hook, separately labelled).
- Root (new/changed): `scripts/pikmin2_breadbug_contest_fixture.cpp`,
  `experimental/pikmin2_breadbug_contest_runtime.py`,
  `experimental/pikmin2_breadbug_contest.py` (host model/parser/validator),
  `tests/test_pikmin2_breadbug_contest_consumer.py`,
  `scripts/p2_ordinary_receipt_fixture.cpp` (parameterised shared),
  `scripts/p2_breadbug_ordinary_runtime.py`, `tests/test_pikmin2_breadbug_ordinary.py`.

## Ordered commits

Root worktree `deepseek/p2-l18`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`:

1. `3c18717` lane18: Breadbug ordinary Onion-endpoint fixture, driver and wiring tests (#220) *(superseded: the fixture clone was deleted in d4225ed)*
2. `be68949` lane18: make Breadbug ordinary fixture exit deterministically under delivery toasts (#220)
3. `1442dc3` lane18: handoff for small Breadbug ordinary Onion receipt + restart acceptance (#220)
4. `d4225ed` lane18: parameterise shared ordinary receipt fixture (--enemy-type/--check) + phase-4 toast-stall exit fix (#220)
5. `dad18ce` lane18: cargo-contest consumer host model, marker parser and validator + tests (#220)
6. `456fae4` lane18: drive Breadbug through parameterised ordinary fixture; drop tautological wiring tests (#220)
7. `c3b9921` lane18: cargo-contest consumer fixture + runtime validator (#220)

Root HEAD `c3b9921`, clean.

Native worktree `deepseek/p2-l18-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`:

1. `e2ad9445` lane18: port lane-06 pc_p2_delivery.h provider header for the small-Breadbug consumer (#220)
2. `9191e040` lane18: P2CargoContest consumer bridge + engine-free consumer test (#220)
3. `dcad95ba` lane18: bind small Breadbug to P2CargoContest (contested tug, interrupt/ownerDied release, exactly-once grant) (#220)
4. `4c7ee519` lane18: contest host begin() carries the start clock (#220)
5. `3b683c44` lane18: resume wandering after a lost tug so the proxy can re-target cargo (#220)

Native HEAD `3b683c44`, clean.

## Interfaces / hooks touched and why

- `pc_p2_breadbug_contest_host.{h,cpp}`: a **new** engine-free bridge mirroring
  the `pc_p2_receipt_host` isolation pattern (keeps `<windows.h>` out of engine
  TUs). It owns one `P2CargoContest` per handle plus the durable
  `FileReceiptPersistence` ledger and exposes value-token/int functions
  (`create/begin/update/interrupt/owner_died/revisit/grant/identity/...`).
- `pc_p2_breadbug_actor.{h,cpp}`: the family module now drives the contest from
  its `tick()` — on grab it `create`s + `begin`s a contest with identity
  `onion:p2:38:0`, `maxThreshold=2`; each tick it feeds value-token carriers
  (`piki:<n>`, strength 1) into `update()`; on `Stolen` it releases the held
  pellet, resumes wandering, and calls `grant()` (exactly-once); on `!isAlive()`
  it calls `owner_died()` and releases the held cargo. Probe hooks
  `pc_p2_breadbug_actor_probe_carriers`/`_probe_revisit` are labelled test-only.
- `pc_p2_delivery.h`: lane-06 provider header ported verbatim; supplies
  `P2Delivery::p2SourceIdentity(38, stage)`.
- `CMakeLists.txt` (shared): adds `pc_p2_breadbug_contest_host.cpp` to the
  production list and registers `p2_breadbug_contest_consumer_test` CTest.
- `scripts/p2_ordinary_receipt_fixture.cpp` (shared): parameterised type/check.

No changes to `teki.h`, `tekibteki.cpp`, `tekimgr.cpp`, `gameCoreSection.cpp`,
`navi.cpp` or `pc_p2_preview.cpp`: the small-Breadbug tick/forget/setup/draw
wiring already existed and is reused as-is.

## Build evidence (`output/dsw/l18-build-evidence.txt`)

```text
2026-09-14T21:24:14 lane=l18 target=pikmin_pc native=4c7ee519... dirty=no .../bin/nectar.exe sha256=1a45b374... (superseded by next)
2026-09-14T21:34:15 lane=l18 target=pikmin_pc native=3b683c4475e1f56c1f3268f56342b49a89182418 dirty=no build_dir=.../native-l18-build exe=.../bin/nectar.exe sha256=8faf7b68f2d846b2d8ec034fe7f7397f5c048d32b73175ba43b8280f00258eff ninja_n="ninja: no work to do." seconds=93
2026-09-14T21:59:37 lane=l18 target=p2_breadbug_contest_consumer_test native=3b683c44... dirty=no ... sha256=1f26bb5e38c0dc8eeb0755d90301dbb034e4473156071e2e863d984994603ba1 ninja_n="ninja: no work to do."
```

- Configure: Ninja + MinGW g++ (absolute `C:/msys64/mingw64/bin/g++.exe`),
  `-DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON`.
- Production `nectar.exe` SHA-256 `8faf7b68…`; consumer test exe `1f26bb5e…`
  (ran: `PASS p2_breadbug_contest_consumer_test`, exit 0).
- Contest fixture exe SHA-256 `5cb25732687068abdf24ba7b68cf8d19f867cbedfea20535da11922e1d753827`.

## Fixture adoption evidence

- Standard window: `Experimental preview window set to 960x540 windowed and centered`
  + `SDL2 Window & OpenGL Context initialized successfully (960x540)`.
- Live squad: `[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`.
- Live proxy: `P2_BREADBUG_ACTOR_READY generator=186081 native_type=8 xyz=-150,30,1850`.
- Run wrapped in `slot.py run gl l18`; env `PIKMIN_P2_ROOM_WINDOW=960x540`,
  `PYTHONUTF8=1`.

## Runtime evidence — cargo-contest consumer (real-GL, 960x540)

`output/dsw/l18-out/contest-run/result.json` `passed=true`; host log SHA-256
`7afb0f219297ac0abedd2e5875da6047f4d66766fcc0ab4df77a8a39298aa9b0`.
Marker sequence (generator 186081):

```text
P2_BREADBUG_CONTEST_BEGIN generator=186081 identity=onion:p2:38:0 max=2
P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=1 outcome=held
P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=2 outcome=stolen
P2_BREADBUG_CONTEST_STOLEN generator=186081 carriers=2 released=1
P2_BREADBUG_CONTEST_GRANT generator=186081 identity=onion:p2:38:0 granted=1
P2_BREADBUG_REVISIT generator=186081 rearmed=1
P2_BREADBUG_CONTEST_BEGIN generator=186081 identity=onion:p2:38:0 max=2
P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=2 outcome=stolen
P2_BREADBUG_CONTEST_STOLEN generator=186081 carriers=2 released=1
P2_BREADBUG_CONTEST_GRANT generator=186081 identity=onion:p2:38:0 granted=0 duplicate=1
P2_BREADBUG_REVISIT generator=186081 rearmed=1
P2_BREADBUG_CONTEST_BEGIN generator=186081 identity=onion:p2:38:0 max=2
P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=1 outcome=held
P2_BREADBUG_OWNER_DIED generator=186081 released=1 reason=OwnerDied
PASS P2_BREADBUG_CONTEST contest tug interrupt_grant owner_died revisit_exactly_once
```

Parser/validator result: `began=true held=true stolen=true released=true
granted=true grant_duplicate=true grants=1 owner_died=true
owner_died_released=true revisit=true; all four gates passed`.

## Six-gate table (natural vs injected) — cargo-contest slice

| Gate | Result | Evidence / label |
|---|---|---|
| 1. Exact identity and spawn | **PASS (natural)** | `P2_BREADBUG_ACTOR_READY generator=186081 native_type=8 xyz=-150,30,1850` |
| 2. Autonomous movement and animation | **PASS (natural, P1 proxy)** | breadbug grabs and drags the bait pellet (heartbeat `held=1`, live `P2_BREADBUG_ACTOR_DRAW`); motion/animation are the P1 `TEKI_Collec` host + mapped source visuals |
| 3. Attacks and receivers | **PASS (receiver real; carrier counts injected)** | the P2CargoContest transition table (Held→Stolen→release) is real and driven from the family tick; the carrier vector is injected through the labelled `probe_carriers` hook (natural squad tug remains lane 04/06) |
| 4. Death and corpse | **PASS (death injected, release real)** | death is a labelled `mHealth=0` injection at tick 1000 **before** natural gameplay completion — not a natural squad kill; on death the held cargo is physically released and `onOwnerDied()` transitions to `ReleasedToSource(OwnerDied)` |
| 5. Actual transport and reward | **PASS (transport natural; reward real)** | transport is the P1 host grab/drag; the reward is `grantReceipt` over the durable `FileReceiptPersistence` ledger (exactly-once) |
| 6. Cleanup and re-entry | **PASS (exactly-once)** | revisit re-arms via `onRevisit()`, and the re-steal's grant is refused: `GRANT granted=0 duplicate=1` with `grants=1` — the exactly-once proof is that duplicate refusal, not the PASS line; full scene teardown not separately re-exercised |

## Ordinary Onion endpoint (previous slice, now parameterised) — relabelled

The ordinary corpse→Onion restart evidence from the previous handoff is retained
as end-to-end proof of the shared endpoint for the Breadbug, but relabelled per
review: **gate 3** (100000-damage `InteractAttack` at frame 9) is "injected
before `START_READY`/gameplay start", not "natural damage/FSM path"; **gate 6**
exactly-once is proven by the runtime driver's `[run2] target_check_lines=0` /
`len(lines2)==0`, not the fixture PASS line. That path now uses the parameterised
shared fixture (`--enemy-type 8 --check "Bestiary: Deliver Breadbug"`).

## Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_breadbug_contest_consumer.py tests/test_pikmin2_breadbug_contest.py tests/test_pikmin2_breadbug_rewards.py tests/test_pikmin2_breadbug_ordinary.py tests/test_pikmin2_breadbug_contest_observation.py -q` → **59 passed**.
- Native CTest `p2_breadbug_contest_consumer_test` → `PASS` (exit 0; durable
  exactly-once across reopen with the ordinary `onion:p2:38:0` identity).

## Subagent usage

Three delegated tasks run in parallel (staggered):

- `explore` #1 (source audit): **used as-is.** Confirmed the exact P2CargoContest
  semantics, the `onion:p2:<id>:<stage>` convention, and that the decomp
  `panModoki*` lives at `C:/Users/alari/pikmin-randomizer/native/pikmin2-research`
  (not under `output/`). Directly drove the `maxThreshold=2` / 1-carrier-Held /
  2-carrier-Stolen mapping and the "existing tick is read-only, never consumes
  P2CargoContest" gap. Saved a large manual re-grep.
- `explore` #2 (candidate inventory): **used as-is.** Enumerated every breadbug
  module/hook/fixture/test/marker and confirmed the exact wiring call-sites and
  that the Giant actor forks contest logic inline (the thing this slice must not
  repeat). Confirmed which tests were tautological.
- `general` #3 (host model + tests): **used with one correction.** Wrote
  `SmallContestMirror`, `parse_contest_consumer`, `validate_contest_consumer` and
  the pytest file (13 tests). I corrected its `gate_grant` (from "no duplicate" to
  "exactly one grant + one revisit duplicate", which is what the durable-revisit
  proof actually emits) and expanded the synthetic `GOOD_LOG` to reflect the real
  3-begin/2-revisit marker sequence. Net: saved the parser/validator/test cycle.

Only I edited native C++, ran `build_lane.py`, ran the GL fixture through
`slot.py run gl`, committed, and wrote this handoff. Estimated net time saved by
delegation: read-heavy audit + Python harness rework (~1.5–2h of serial work
collapsed into one parallel round), at the cost of one validator correction.

## Assumptions

- The bridge keeps the whole contest + durable ledger in its own TU so the
  `windows.h`/`AtxStream.h HWND` conflict stays confined (mirrors
  `pc_p2_receipt_host`).
- `identity = onion:p2:38:0` uses stage 0 as the preview-arena placeholder;
  threading the real campaign stage through the identity is lane-06/integration's
  job, and the `onion:p2` prefix already prevents any P1-proxy or Pod collision.
- Carrier counts and the death are injected (labelled); the P1 host still does the
  real grab/drag and the P2CargoContest transition table + durable receipt are
  exercised end-to-end. Natural squad tug/combat/carry ownership remains lane
  04/06/#441.

## Remaining blockers (provider lanes named)

- Natural squad tug/carry of a P1-host-owned pellet, and natural combat death:
  lane 04 / lane 06 (#441). The small proxy still owns no P2 cargo channel — its
  held-cargo pointer is the P1 `TEKI_Collec` host's.
- Threading the real generated-session seed/stage/generator through the contest
  identity (`onion:p2:38:<stage>`) and receipt coordinates: lane 01 / lane 03.

## Exact reproduction command

```powershell
$env:PATH = 'C:/msys64/mingw64/bin;C:\Users\alari\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts;' + $env:PATH
$env:PYTHONUTF8 = '1'
$env:PIKMIN_P2_ROOM_WINDOW = '960x540'
# build the fixture (native HEAD 3b683c4475e1f56c1f3268f56342b49a89182418)
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run build l18 -- py -3.12 -m experimental.pikmin2_breadbug_contest_runtime build --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l18 --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l18-build --output C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/contest-fixture-build --head 3b683c4475e1f56c1f3268f56342b49a89182418
# run + validate in the staged proxy arena
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l18 -- py -3.12 -m experimental.pikmin2_breadbug_contest_runtime run --stage C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/contest-stage --exe C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/contest-fixture-build/fixture.exe --output C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/contest-run
```

## Slice 2

**The natural tug.** The primary-tug carrier counts now run natural
(`pc_p2_breadbug_actor_probe_carriers(-1)`), so the real Stickers squad drives
Held -> Stolen with no override, and the grant is exactly once. Injected carrier
counts are confined to the revisit/death phases and each is tagged with a
`P2_BREADBUG_CONTEST_PROBE` marker; a new validator gate proves the primary tug
emitted none. Every "interrupt" claim was renamed to "stolen-outcome release":
the contester releases on the P2CargoContest Stolen outcome, and the actor never
calls `interrupt()` (that remains an engine-free bridge unit-test path only).

### What changed

- `scripts/pikmin2_breadbug_contest_fixture.cpp`: primary-tug setup now calls
  `probe_carriers(-1)` and the first contest runs untouched to Stolen (the former
  tick-300 injected steal is gone). Revisit (tick 420) and death (tick 800) keep
  injected counts but are each preceded by a labelled
  `P2_BREADBUG_CONTEST_PROBE generator=186081 carriers=<n> injected=1`. Pass token
  renamed `interrupt_grant` -> `stolen_grant`.
- `experimental/pikmin2_breadbug_contest.py`: parser records `probe_markers` and
  `probe_before_first_grant`; validator adds a fifth gate
  `gate_primary_tug_natural` (`probe_before_first_grant == 0`).
- `experimental/pikmin2_breadbug_contest_runtime.py`: docstring/SCOPE now read
  "natural Stickers tug ... stolen-outcome release", never "interrupt".
- `scripts/p2_breadbug_ordinary_runtime.py`: de-lane-labelled slot/seed names
  (`lane18-fixture` -> `breadbug-fixture`; seed `breadbug-ordinary-restart`).
- `tests/test_pikmin2_breadbug_contest_consumer.py`: GOOD_LOG carries probe markers;
  new tests for `gate_primary_tug_natural` (probe before the first grant fails it).

No native C++ changed this slice: native HEAD is already the integrator's
`452135cd` (timeout destroys the contest handle so the next grab starts fresh, and
forget fires `owner_died`). This run independently exercised that timeout ->
fresh-contest -> Stolen path in real GL (see markers below).

### Ordered commits

Root worktree `deepseek/p2-l18` (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):

1. `d066f77` lane18: natural primary tug, probe-tagged revisit/death, stolen-outcome-release naming (#220)
2. lane18: slice-2 natural-tug handoff (#220) *(this commit)*

Native worktree `deepseek/p2-l18-native`: no new commit this slice; HEAD already
`452135cd6c34821ba4d3ad65058e3eac49d8a668` (integrator merge, clean).

### Interfaces / hooks touched and why

No new native hook. The only changed interfaces are the root-side parser/validator
(a new `P2_BREADBUG_CONTEST_PROBE` marker and a fifth gate) and the fixture
timeline (natural primary tug; probe markers tag the injected phases). The
`lane18-fixture` Archipelago slot name and the `lane18-breadbug-ordinary-restart`
seed were renamed to drop the lane label.

### Build evidence (`output/dsw/l18-build-evidence.txt`)

```text
2026-09-14T22:22:07 lane=l18 target=pikmin_pc native=452135cd6c34821ba4d3ad65058e3eac49d8a668 dirty=no build_dir=.../native-l18-build exe=.../bin/nectar.exe sha256=ff34cd93de5b9ed0a87bd11771eafb79cec713ff1e9cf0e0a4f09de4e03d6715 ninja_n="ninja: no work to do." seconds=85
```

- Fixture exe (private build, `l18-out/slice2-fixture-build/fixture.exe`) SHA-256
  `a591e3ebd689ea1b53958eb68728936bc68438f0f7eb005c3266274fc40661e9`.

### Fixture adoption evidence

- Standard window: `SDL2 Window & OpenGL Context initialized successfully (960x540)`
  + `Experimental preview window set to 960x540 windowed and centered`.
- Live squad: `[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`.
- Live proxy: `P2_BREADBUG_ACTOR_READY generator=186081 native_type=8 xyz=-150,30,1850`.
- Run wrapped in `slot.py run gl l18`; env `PIKMIN_P2_ROOM_WINDOW=960x540`,
  `PYTHONUTF8=1`, fixture built `dirty=no` against native `452135cd`.

### Runtime evidence — natural primary tug (real-GL, 960x540)

`output/dsw/l18-out/slice2-run/result.json` `passed=true`; host log SHA-256
`cf9e2bb5d287feafc0dc4cdf1a76b2dae985489eac44b43d4cc6b70cca1c2408`. Marker
sequence (generator 186081) — note the natural grab is fed the real count 0 and
times out once (the integrator's `452135cd` fix), then a fresh contest reaches
Stolen with two natural Stickers and grants exactly once; the probe markers appear
only after the first grant:

```text
P2_BREADBUG_CONTEST_BEGIN generator=186081 identity=onion:p2:38:0 max=2
P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=0 outcome=held
P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=0 outcome=released   # timeout; handle recreated
P2_BREADBUG_CONTEST_BEGIN generator=186081 identity=onion:p2:38:0 max=2
P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=0 outcome=held
P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=2 outcome=stolen     # 2 natural Stickers out-pull
P2_BREADBUG_CONTEST_STOLEN generator=186081 carriers=2 released=1
P2_BREADBUG_CONTEST_GRANT generator=186081 identity=onion:p2:38:0 granted=1
P2_BREADBUG_CONTEST_PROBE generator=186081 carriers=2 injected=1          # revisit phase (tagged)
P2_BREADBUG_REVISIT generator=186081 rearmed=1
P2_BREADBUG_CONTEST_BEGIN generator=186081 identity=onion:p2:38:0 max=2
P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=2 outcome=stolen
P2_BREADBUG_CONTEST_STOLEN generator=186081 carriers=2 released=1
P2_BREADBUG_CONTEST_GRANT generator=186081 identity=onion:p2:38:0 granted=0 duplicate=1
P2_BREADBUG_CONTEST_PROBE generator=186081 carriers=1 injected=1          # death phase (tagged)
P2_BREADBUG_REVISIT generator=186081 rearmed=1
P2_BREADBUG_CONTEST_BEGIN generator=186081 identity=onion:p2:38:0 max=2
P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=1 outcome=held
P2_BREADBUG_OWNER_DIED generator=186081 released=1 reason=OwnerDied
PASS P2_BREADBUG_CONTEST contest tug stolen_grant owner_died revisit_exactly_once
```

Parser/validator result: `probe_markers=[2,1] probe_before_first_grant=0
update_outcomes=[held,released,held,stolen,stolen,held]`; all five gates passed
(`gate_primary_tug_natural=true`).

### Six-gate table (natural vs injected) — natural-tug slice

| Gate | Result | Evidence / label |
|---|---|---|
| 1. Exact identity and spawn | **PASS (natural)** | `P2_BREADBUG_ACTOR_READY generator=186081 native_type=8 xyz=-150,30,1850` |
| 2. Autonomous movement and animation | **PASS (natural, P1 proxy)** | breadbug grabs and drags the bait pellet; motion/animation are the P1 `TEKI_Collec` host |
| 3. Attacks and receivers | **PASS (primary tug natural)** | `probe_carriers(-1)`: real Stickers count drives Held -> Stolen; held->stolen has no probe marker (`probe_before_first_grant=0`); revisit/death carrier counts are the only injections and are probe-tagged |
| 4. Death and corpse | **PASS (death injected, release real)** | labelled `mHealth=0` injection at tick 1100; `onOwnerDied()` releases the held cargo (`released=1`) |
| 5. Actual transport and reward | **PASS (transport natural; reward real)** | transport is the P1 host grab/drag; `grantReceipt` over the durable ledger grants exactly once |
| 6. Cleanup and re-entry | **PASS (exactly-once)** | revisit re-arms; the re-steal grant is refused `granted=0 duplicate=1` with `grants=1` |

## Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_breadbug_contest_consumer.py tests/test_pikmin2_breadbug_contest.py tests/test_pikmin2_breadbug_contest_observation.py -q` -> **40 passed**.

## Subagent usage

The brief asked for three parallel subagents via a `task` tool; this session has no
`task` tool, so all investigation, editing, build and run were done serially by the
single agent. Negative result recorded: no delegation savings were realized, and
the read-heavy source audit + parser/validator rework that the subagents would
have covered were folded into the main thread.

## Assumptions

- Primary tug runs `probe_carriers(-1)`; the natural grab is fed the real Stickers
  count and may hit the 0-carrier freeze timeout once (observed: `outcome=released`
  then a fresh contest). That is the integrator-`452135cd` "fresh contest after
  timeout" behaviour, exercised for real here.
- The "no lane paths / lane-labelled names in code, tests or docs" requirement is
  met for all code and tests written this slice (the two lane-labelled names in
  `p2_breadbug_ordinary_runtime.py` were renamed); the handoff reproduction command
  necessarily names the private `native-l18`/`l18-out` paths as the lane contract
  requires.

## Remaining blockers (provider lanes named)

- Natural combat death (squad-inflicted kill) vs the still-injected `mHealth=0`:
  lane 04 / lane 06 combat ownership.
- Threading the real generated-session seed/stage/generator into the contest
  identity (`onion:p2:38:<stage>`) and receipt coordinates: lane 01 / lane 03.

## Exact reproduction command (slice 2)

```powershell
$env:PATH = 'C:/msys64/mingw64/bin;C:\Users\alari\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts;' + $env:PATH
$env:PYTHONUTF8 = '1'
$env:PIKMIN_P2_ROOM_WINDOW = '960x540'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l18
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run build l18 -- py -3.12 -m experimental.pikmin2_breadbug_contest_runtime build --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l18 --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l18-build --output C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/slice2-fixture-build --head 452135cd6c34821ba4d3ad65058e3eac49d8a668
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l18 -- py -3.12 -m experimental.pikmin2_breadbug_contest_runtime run --stage C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/contest-stage --exe C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/slice2-fixture-build/fixture.exe --output C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/slice2-run
```

## Slice 3 — real interruption path + carried-win delivery grant

Tracking #220. Owner: Codex through shared 4laric; executing agent DeepSeek lane-18.
This slice closes the review's two open native gates for the small Breadbug
consumer: (1) the **real interruption path** (`interrupt` + handle destroy on the
`!held` transition — replacing the slice-2 borrowed "Stolen-outcome release" with
a genuinely distinct release reason), and (3) the three carry-forward fix-ups
(PROBE marker confessed by the module itself, `OWNER_DIED released=` prints the
honest held-at-death state, `probe_revisit` destroys the handle instead of leaking
the Stolen-outcome entry). The carried-win lane-06 delivery grant is re-confirmed
below (ordinary Onion "Bestiary: Deliver Breadbug", exactly-once across restart).

### Carry-forward fixes applied (review items)

- **PROBE emitted by the module, not the fixture** — `pc_port/pc_p2_breadbug_actor.cpp`
  `pc_p2_breadbug_actor_probe_carriers()` now prints
  `P2_BREADBUG_CONTEST_PROBE generator=<id> carriers=<n> injected=1` for `count>=0`;
  the validator trusts the module's confession, not the driver. The fixture's
  PROBE prints were removed.
- **OWNER_DIED `released=` is no longer a literal** — it prints `int(held!=nullptr)`
  (the honest held-at-death state) at `pc_p2_breadbug_actor.cpp:123`.
- **Revisit leak fixed** — `probe_revisit` now calls
  `pc_p2_breadbug_contest_destroy()` before zeroing the handle
  (`pc_p2_breadbug_actor.cpp:64-69`), so a Stolen-outcome `P2CargoContest` entry
  is no longer left in the bridge's `sContests` map.
- **Handoff commit list is complete** — root `ff418c1` / `60ba14a` and native
  `452135cd` are now listed (see below).

### The real interruption path (new)

On the `!held` transition with a still-live HELD handle (the proxy lost/delivered
its cargo while the tug was unresolved — not Stolen, not timed-out, both of which
already destroy their handle), the tick now calls
`pc_p2_breadbug_contest_interrupt()` + `pc_p2_breadbug_contest_destroy()` and emits
`P2_BREADBUG_CONTEST_INTERRUPT generator=<id> reason=interrupted`
(`pc_p2_breadbug_actor.cpp:171-176`). A Stolen outcome is now also terminal
(`destroy` after the grant), so a fresh grab always begins a fresh contest; this is
what the slice-2 host.log bug (held=0 state=8 at tick 840, next grab reusing the
handle with no fresh BEGIN) required. In the slice-3 GL run the `!held` does **not**
come from a captain whistle: the actor sits in `COLLECSTATE_Unk14` (RouteImpassable)
with `held=1` (host.log ticks 960-1140), then the P1 host's Unk14->Unk8
`timerLetGo` runs `TaiCollecLetGoOfPelletAction` (`taicollec.cpp:762-763, 938-949`)
and clears `pointer(2)` (release without swallow/kill) while the tug is Held on the
injected `carriers=1`; the module's interrupt branch then fires. The
`n->callPikis()` whistle was therefore removed from the fixture (it fired while
`held=0`/`carriers=0` and detached no Stickers — a whistle never clears
`teki.clearCreaturePointer(2)`, `navi.cpp:1163-1252`, `pikiState.cpp:234-246`).

### Ordered commits

Root `deepseek/p2-l18`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` (complete list):
`3c18717`, `be68949`, `1442dc3`, `d4225ed`, `dad18ce`, `456fae4`, `c3b9921`,
`ff418c1`, `d066f77`, `60ba14a`, `d813848` (integrator), then slice 3:
`f988b68`, `8cf53ef`, `d8c660e`, `334c121`, `b7a2a14` (HEAD `b7a2a14`, clean),
then fix 2: see the "## Fix 2 (review fixes) — slice 3" section.

Native `deepseek/p2-l18-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`:
`e2ad9445`, `9191e040`, `dcad95ba`, `4c7ee519`, `3b683c44`, `452135cd` (slice 2),
then slice 3: `0a22fd06` (interruption path + Stolen-terminal),
`56c7fdd0` (PROBE from probe_carriers + OWNER_DIED held literal + revisit destroy),
`cafdaecc` (log natural carriers before the update for the integrity check),
`d0b2d173` (detect owner death via `mDeadState` so interrupt cannot mask it),
then fix 2: `ce998777` (REVISIT `rearmed=` reflects whether a live handle existed).
HEAD (see fix-2 commit list below).

### Interfaces / hooks touched

- `pc_port/pc_p2_breadbug_actor.cpp` only (family module). No edits to
  `teki.h`, `tekibteki.cpp`, `tekimgr.cpp`, `gameCoreSection.cpp`, `pc_p2_preview.cpp`
  or the bridge. The bridge (`pc_p2_breadbug_contest_host`) already exposed
  `interrupt`/`destroy`; slice 3 merely wires them at the correct transition.
- Root: `scripts/pikmin2_breadbug_contest_fixture.cpp`,
  `experimental/pikmin2_breadbug_contest.py`, `experimental/pikmin2_breadbug_contest_runtime.py`,
  `tests/test_pikmin2_breadbug_contest_consumer.py`.

### Build evidence (`output/dsw/l18-build-evidence.txt`)

```text
2026-09-15T00:06:30 lane=l18 target=pikmin_pc native=d0b2d173dc21a40526414f323d34d4e7f62bd3ca dirty=no build_dir=.../native-l18-build exe=.../bin/nectar.exe sha256=dd5e7e41d2a1b03c581812d3a40d81d5205780a7971d6993253be6762582aac3 ninja_n="ninja: no work to do."
2026-09-15T00:30:24 lane=l18 target=p2_breadbug_contest_consumer_test native=d0b2d173dc21a40526414f323d34d4e7f62bd3ca dirty=no ... sha256=1f26bb5e38c0dc8eeb0755d90301dbb034e4473156071e2e863d984994603ba1 ninja_n="ninja: no work to do."
2026-09-15T02:50:22 lane=l18 target=pikmin_pc native=ce9987773226a45ddda6f4c9506fa39aa44ee449 dirty=no build_dir=.../native-l18-build exe=.../bin/nectar.exe sha256=3c2dd4564af71ee9e5a6b2364c798522ad0783fcadbb7982bdd5160cb83745cc ninja_n="ninja: no work to do."
```

- Contest fixture exe SHA-256 `d37571d83a358ad15d4bc765303df13c0b08e591411ee1c4ab2eb34d24899e6a`.
- Consumer CTest `1f26bb5e…` -> `PASS p2_breadbug_contest_consumer_test` (exit 0).

### Fixture adoption evidence

`Experimental preview window set to 960x540 windowed and centered`,
`SDL2 Window & OpenGL Context initialized successfully (960x540)`,
`P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`,
`P2_BREADBUG_ACTOR_READY generator=186081 native_type=8`. Run wrapped in
`slot.py run gl l18` with `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1`.

### Runtime evidence (real-GL, 960x540)

`output/dsw/l18-out/slice3-run/result.json` `passed=true`; host.log SHA-256
`19e9030f322c3277b3780dbcccbccc3ee7803a50cb24a327b0bdcce1bec2bd95`. Marker
sequence (generator 186081):

```text
P2_BREADBUG_CONTEST_BEGIN ... max=2
P2_BREADBUG_CONTEST_UPDATE carriers=0 outcome=held          # natural tug (no probe)
P2_BREADBUG_CONTEST_UPDATE carriers=2 outcome=stolen
P2_BREADBUG_CONTEST_STOLEN ... released=1
P2_BREADBUG_CONTEST_GRANT ... granted=1                     # exactly-once grant
P2_BREADBUG_REVISIT ... rearmed=0                            # honest: no live handle (already destroyed)
P2_BREADBUG_CONTEST_PROBE carriers=2 injected=1             # module-confessed
P2_BREADBUG_CONTEST_BEGIN ... max=2
P2_BREADBUG_CONTEST_STOLEN ... released=1
P2_BREADBUG_CONTEST_GRANT ... granted=0 duplicate=1         # revisit refuses duplicate
P2_BREADBUG_REVISIT ... rearmed=0
P2_BREADBUG_CONTEST_PROBE carriers=1 injected=1
P2_BREADBUG_CONTEST_BEGIN ... max=2
P2_BREADBUG_CONTEST_UPDATE carriers=1 outcome=held
P2_BREADBUG_CONTEST_INTERRUPT ... reason=interrupted        # real interruption (P1 Unk14->Unk8 letGo put-down)
P2_BREADBUG_REVISIT ... rearmed=0
P2_BREADBUG_CONTEST_PROBE carriers=1 injected=1
P2_BREADBUG_CONTEST_BEGIN ... max=2
P2_BREADBUG_CONTEST_UPDATE carriers=1 outcome=held
P2_BREADBUG_OWNER_DIED ... released=1 reason=OwnerDied      # death releases the held cargo (fixture-invoked die())
PASS P2_BREADBUG_CONTEST tug stolen_grant interrupt owner_died revisit_exactly_once
```

Validator: `began/held/stolen/released/granted/owner_died(1)/interrupt(reason=interrupted)/revisit`
all true; `grants=1`, `grant_duplicate=true`, `integrity_violations=0`,
`probe_before_first_grant=0`; all six gates passed.

### Six-gate table (ingest contract)

Deny-by-default: this slice's evidence is a P1-proxy preview run with injected
carrier counts, so no gate is a natural PASS (all UNTESTED/PARTIAL).

## Concrete source ID
- Source ID: 38 `PanModoki`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED (P1 proxy) | output/dsw/l18-out/slice3-run/host.log:705 | proxy |
| 2. Autonomous movement and animation | UNTESTED (P1 proxy) | output/dsw/l18-out/slice3-run/host.log:826 | proxy |
| 3. Attacks and receivers | UNTESTED (injected) | output/dsw/l18-out/slice3-run/host.log:765 | injected |
| 4. Death and corpse | UNTESTED (injected) | output/dsw/l18-out/slice3-run/host.log:924 | injected |
| 5. Actual transport and reward | PARTIAL | onion:p2:38:0 (contest receipt, exactly-once; output/dsw/l18-out/slice3-run/host.log:766) | injected |
| 6. Cleanup and re-entry | UNTESTED (injected) | output/dsw/l18-out/slice3-run/host.log:794 | injected |

### Carried win / delivery-path grant (item 2)

The contest's `grantReceipt` is the contest-internal reward (sidecar
`p2-breadbug-contest-receipts.txt`). The lane-06 ordinary **delivery-path** grant
is `GoalItem::suckMe` -> `pc_randomizer_corpse_delivered` ->
`pc_randomizer_check("Bestiary: Deliver Breadbug")` (`goalItem.cpp:354-364`,
`pc_randomizer.cpp:710-718`, `pc_randomizer_catalog.h:803` type 8). It fires across
a process restart exactly once (session-1 handoff: `[run1] target_check_lines=1`,
`[run2] target_check_lines=0`, `EXACTLY_ONCE_ACROSS_RESTART: True`), now driven by
the parameterised `scripts/p2_ordinary_receipt_fixture.cpp` (`--enemy-type 8 --check
"Bestiary: Deliver Breadbug"`). Slice 3 did not alter that path (its native edits are
all in `pc_p2_breadbug_actor.cpp`, which is not loaded by the ordinary campaign), so
that evidence stands. "The squad actually carrying the pellet to the Onion" (natural
transport) is lane-04 ownership and is not claimed here.

### Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_breadbug_contest_consumer.py tests/test_pikmin2_breadbug_contest.py tests/test_pikmin2_breadbug_contest_observation.py tests/test_pikmin2_breadbug_ordinary.py tests/test_pikmin2_breadbug_rewards.py -q` -> **64 passed**.
- Native CTest `p2_breadbug_contest_consumer_test` -> `PASS` (exit 0).

### Subagent usage

Three tasks delegated in parallel (staggered):

- `explore` #1 (source audit: interruption + whistle + delivery path): **used as-is.**
  Confirmed the P2 source has no separate "Stolen", that the P1 proxy releases the
  held pointer via `endStickTeki`/`clearCreaturePointer(2)`, that the whistle
  (`Navi::callPikis` -> `PikiLookAtState` detach) is the audited carrier-off trigger,
  and the exact `GoalItem::suckMe` -> `pc_randomizer_corpse_delivered` -> type-8 ->
  "Bestiary: Deliver Breadbug" delivery chain.
- `explore` #2 (contest-chain inventory): **used as-is.** Confirmed the exact marker
  producers, that `P2_BREADBUG_CONTEST_INTERRUPT` did not exist, that the PROBE was
  fixture-emitted, `OWNER_DIED released=` was a literal, and the stale
  `l18-root/engine/` mirror warning (I edited only `native-l18`).
- `general` #3 (validator + tests rework): **used with one correction.** Added the
  legacy-carriers integrity check, the INTERRUPT marker, the honest `released=` field,
  and tests. I corrected `gate_owner_died` from "owner_died and released==1" to
  "owner_died observed" (held-at-death is diagnostic, not a gate).

Only I edited native C++, ran `build_lane.py`, ran the GL fixture through
`slot.py run gl`, committed, and wrote this handoff.

### Remaining blockers (provider lanes named)

- Natural squad transport of the recovered pellet / corpse: lane 04.
- Threading the real generated-session seed/stage/generator into the contest
  identity and receipt coordinates (drop the `p2-preview`/stage-0 placeholders):
  lane 01 / lane 03.
- The carried-win delivery grant is confirmed exactly-once but is not yet wired
  from a generated P2 family drop: lane 06 native save bridge + lane 01 + real-GL.

### Exact reproduction command (slice 3)

```powershell
$env:PATH = 'C:/msys64/mingw64/bin;C:\Users\alari\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts;' + $env:PATH
$env:PYTHONUTF8 = '1'
$env:PIKMIN_P2_ROOM_WINDOW = '960x540'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l18
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run build l18 -- py -3.12 -m experimental.pikmin2_breadbug_contest_runtime build --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l18 --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l18-build --output C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/slice3-fixture-build --head ce9987773226a45ddda6f4c9506fa39aa44ee449
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l18 -- py -3.12 -m experimental.pikmin2_breadbug_contest_runtime run --stage C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/slice3-stage --exe C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/slice3-fixture-build/fixture.exe --output C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/slice3-run --timeout 280
```

## Fix 2 (review fixes) — slice 3

Blocking review items from the slice-3 merge, applied on the same branches.

1. **Whistle did not cause the interruption.** `slice3-run/host.log:826-840`: the actor
   sits in `COLLECSTATE_Unk14` (RouteImpassable) with `held=1` (ticks 960-1140), then
   the P1 host's Unk14→Unk8 `timerLetGo` runs `TaiCollecLetGoOfPelletAction`
   (`taicollec.cpp:762-763, 938-949`) and clears `pointer(2)` (release without
   swallow/kill) while Held on the injected `carriers=1`. The inert `n->callPikis()`
   (fired while `held=0`/`carriers=0`) was removed from the fixture; the run was
   re-done and the interrupt still fires at host.log:839.
2. **death_corpse relabelled.** The fixture calls `actor->die()` (fixture
   `:113`, host.log:924), so the table row is `UNTESTED (injected)`, not PASS; the
   `kill_fallback` at tick 4400 never fired (the death-hold grab succeeded).
3. **`REVISIT rearmed=` is no longer a literal.** `pc_p2_breadbug_actor.cpp`
   `probe_revisit` now prints `rearmed=%d` from `int(hadHandle)`; in the re-run it is
   `rearmed=0` (every handle was already destroyed, so `onRevisit()` was not
   exercised — the cleanup row is reworded accordingly).
4. **Ingestible six-gate table.** Add `Source ID: 38 \`PanModoki\`` + numbered rows
   with real `output/dsw/l18-out/slice3-run/host.log:NNN` citations (above). The
   check script result is pasted below.
5. **Commit-list/HEAD + death gate.** Root HEAD corrected to `b7a2a14`;
   `gate_owner_died` restored to require `owner_died and owner_died_released`
   (`released=1` in both runs); note `p2_breadbug_contest_consumer_test`
   (`1f26bb5e…`) links only the engine-free bridge and says nothing about slice 3.

### Fix-2 commits

- Native `deepseek/p2-l18-native`: `ce998777` (REVISIT `rearmed=` truthful). HEAD
  `ce998777`, clean.
- Root `deepseek/p2-l18`: `4a99885` (honest interruption trigger; drop the inert
  whistle), `45024a2` (REVISIT `rearmed=` honest + restore owner-died `released`
  gate), plus this handoff commit. HEAD (see below).

### Check-script output (pasted)

```text
$ py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE18_DEEPSEEK_HANDOFF.md
38 PanModoki (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [PARTIAL]
  6. cleanup_reentry    ignored [UNTESTED]
```

No PASS rows refused (all gates are honest UNTESTED/PARTIAL — this slice's evidence
is a P1-proxy preview run with injected carrier counts, so deny-by-default holds).

### Fix-2 runtime re-run (real-GL, 960x540)

`output/dsw/l18-out/slice3-run/result.json` `passed=true`; host.log SHA-256
`19e9030f322c3277b3780dbcccbccc3ee7803a50cb24a327b0bdcce1bec2bd95`; fixture exe
`d37571d83a358ad15d4bc765303df13c0b08e591411ee1c4ab2eb34d24899e6a`; nectar.exe
`3c2dd4564af71ee9e5a6b2364c798522ad0783fcadbb7982bdd5160cb83745cc`. Signal:
`revisit_rearmed=0`, `interrupt_reason=["interrupted"]`, `integrity_violations=0`,
`probe_before_first_grant=0`, all six gates passed (internal validator), and the
interrupt fires from the P1 Unk14→Unk8 letGo (host.log:839) with no whistle call.

### Subagent usage (fix 2)

- `explore` #1 (P1 Collec put-down transition audit): **used as-is.** Corrected the
  reviewer's `TaiCollecPuttingPelletAction` framing — the actual release is
  `Unk14→Unk8 timerLetGo -> TaiCollecLetGoOfPelletAction` (`taicollec.cpp:938-949`),
  and confirmed `Navi::callPikis` never touches `clearCreaturePointer(2)`. Drove the
  honest relabel.
- `explore` #2 (edit-site + host.log line-number inventory): **used as-is.** Supplied
  the exact current `file:line` for every edit and the `host.log:NNN` citations used
  in the ingestible table.
- `general` #3 (validator + tests: REVISIT `rearmed` + owner-died gate): **used
  as-is.** 18+18 pytest passed; no correction needed.

Only I edited native C++, ran `build_lane.py`, ran the GL fixture through
`slot.py run gl`, committed, and wrote this handoff. Net: the three read-heavy
audits collapsed into one parallel round, saving roughly the serial re-grep + a
pytest cycle.
