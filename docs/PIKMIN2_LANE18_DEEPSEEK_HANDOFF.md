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
