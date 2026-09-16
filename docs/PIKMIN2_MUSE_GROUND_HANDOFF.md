# Muse ground lane handoff — Sokkuri79 ordinary-delivery bridge (l55, #495)

Parent #165; wave #491; integration #437/#186.
Implementation owner: Codex through shared account `4laric`; executing
contributor: Muse Spark 1.3 via OpenCode (`opencode/muse-spark-1.3-contributor-free`),
lane muse-ground (l55). Attempt `e26dabd396e6cdf6e1e3f3512bbe476f1e908ce5ba74d55a0b4ab1655092ae80`, generation 3
(recovery of the same session after the free provider stalled; prior slice
preserved, not redone).

## Slice delivered

**Source IDs owned:** Sokkuri 79 (implemented this slice), ElecBug 28 (deferred;
untouched until the first complete Sokkuri slice, per brief ordering).

**Concrete slice:** the missing family-side ordinary-delivery bridge for
Sokkuri79. Before this slice no family module called the lane-06 ordinary
receipt path: `pc_randomizer_p2_bind_source` had zero family callers, so a
naturally killed/hauled Sokkuri corpse reaching `GoalItem::suckMe` could only
ever credit the P1-proxy Chappy check, never `onion:p2:79`. The slice binds
source 79 at Sokkuri setup (generator uid = `Generator::_70`), clears it on
`pc_p2_sokkuri_forget` (idempotent; the central `pc_p2_forget_teki` seam also
clears it), and emits `P2_SOKKURI_DELIVERY_BIND` for the observer. No shared
file is touched; no Transport/kill/credit is injected; no health, AI mode, or
extinction semantics change.

Also new: `experimental/pikmin2_muse_ground.py` (honest delivery validator:
transport PASS needs BOTH `onion:p2:79 new=1` AND natural-carry markers; a
receipt alone is interface-only), `tests/test_pikmin2_muse_ground.py` (10
unit tests, all pass), and `native/tools/p2_muse_ground_fixture.cpp` (natural
death -> corpse -> carry-observation replacement-main source; not yet built or
run — see remaining work).

ElecBug28: no module change this slice (scope ordering). Its gate rows below
preserve lane-14 evidence without relabelling.

## Slice 2 — natural death/corpse/haul observation (generation 3)

**Concrete slice:** build the slice-1 fixture source and observe what free
Pikmin do with a naturally killed Sokkuri corpse — no health/state writes, no
Transport injection, no `suckMe` fallback (the fixture contains neither code
path). Two preserved gen-2 native commits complete the fixture:
`7ab1262b` (`pc_p2_preview.h` include + doc refresh) and `54e018f7`
(preview-room entrypoint guard + equivalent 960x540 centred-window block, per
the fan-out custom-fixture rule).

**Fixture adoption (this slice, all fields):**

```text
Fixture baseline adoption
Child issue / lane / implementation owner: #495 / muse-ground (l55) / Codex through shared 4laric (Muse Spark 1.3)
Root commit + dirty state / overlay source: 0fea5ec5 clean / scripts/preview_pikmin2_room.py (ensure_pikmin_squad present)
Native commit + dirty state / worktree / private build directory: 54e018f7 clean / output/msw/native-l55 / output/msw/native-l55-build
Squad change present / window change present (ancestry or source evidence): overlay ensure_pikmin_squad=True (source); native pc_main 960x540 + pc_window_center=True (source); fixture own entrypoint mirrors preview_p2_room window block (54e018f7)
Fresh arena command / run directory / asset and config hashes: experimental.pikmin2_sokkuri_natural_runtime.prepare(assets, dsw/l14-out/ground, output/muse-wave/l55/arena-carry2) / arena-carry2/6efb254a98c84685accb348d6157eb33 (arena.json sha256 46de181b945bc9ab33d62cdfd285a6cb3363ecd6bf39b1299bf5ba2bf5520b5e)
Executable SHA-256 / fixture provenance status if applicable: fixture-carry3/fixture.exe e2468b5e3e6b9bc4e47024a10fda83d98ccc270fd55b51dc38da0d4edc135496 / provenance.json status built vs expected head 54e018f7
Window setting / observed size and centring evidence: PIKMIN_P2_ROOM_WINDOW=960x540, SDL_AUDIODRIVER=dummy / run-carry3/capture/native.log:7 windowed and centered
Live starting Pikmin / active gameplay / no immediate extinction evidence: run-carry3/capture/native.log:235 Direct boot 20 reds; :794 READY squad=20; no Extinction marker in 1049 lines
PASS, FAIL, or BLOCKED; remaining work: PARTIAL PASS (natural chain observed; no terminal fixture PASS line — see limits)
```

**Runtime evidence (run-carry3, `output/muse-wave/l55/run-carry3/capture/native.log`,
1049 lines, SHA-256 `5dd85ff8b9e9c32c411f3119ea091f30781efe2f863761ac81be34d8db380a29`;
replicated in run-carry2 up to tick 7740, UTF-16 raw log + `.utf8.log` decoded copy):**

- `:776`–`:778` bind chain: `P2_SOKKURI_DELIVERY_BIND` + `P2_SOKKURI_BIND`
  (source 79) + `P2_ENEMY_READY` (120 HP, native FSM).
- `:797`–`:847` seven `P2_SOKKURI_DAMAGE` hits 105.0 → 15.0 (real
  InteractAttack drain, no writes anywhere in fixture/native path).
- `:851` `P2_SOKKURI_DEAD ... prior_health=15.0` (combat-culminated, small prior).
- `:862` `P2_MUSE_GROUND_CORPSE pellet=1`.
- `:876`–`:914`+ 53 natural carry rows, first `tick=480 moved=62.11`,
  max `tick=960 moved=573.55`: free Pikmin grasped the corpse and hauled it
  ~573 units from the death site, then stalled (cargo-free arena has no
  Onion — carriers run out of route; expected, reported, not a defect).
- No `P2_ORDINARY_P2_RECEIPT` (preview room runs without the randomizer
  session, so `pc_randomizer_p2_corpse_delivered` correctly returns false) —
  gate 5 stays UNTESTED; the haul is carry evidence only, never a reward claim.
- Validator: `experimental.pikmin2_muse_ground.validate(run-carry3 log)` →
  `identity=1 damage=1 death=1 corpse=1 receipt=0 carry=0 haul=573.5
  transport=untested` ("natural haul movement observed but no ordinary
  onion:p2:79 receipt").

**Limits (honest):** both runs exited cleanly (SDL shutdown, exit 0) before
the fixture's `observed>9000` terminal line — run-carry2 at tick 7740,
run-carry3 at tick 3600 — with no extinction, no FAIL, and no sunset marker
found; the early-session-end cause is unestablished. No terminal
`PASS P2_MUSE_GROUND_RUNTIME` line is claimed. run-carry1 (pre-entrypoint-fix
exe) is VOID: it booted the title flow and logged zero P2 markers.

## Ordered commits

Root base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`; native base
`7b9ecaa668fd55332073446cdbdaf6424b209ea7`. Both branches clean at handoff.

| Branch | Commit | Subject |
|---|---|---|
| native `codex/muse-l55-ground-native` | `ecc80b72` | lane55: bind Sokkuri79 ordinary delivery source + muse-ground fixture source (#495) |
| native `codex/muse-l55-ground-native` | `7ab1262b` | lane55: muse-ground fixture preview include + doc refresh (#495) |
| native `codex/muse-l55-ground-native` | `54e018f7` | lane55: muse-ground fixture preview entrypoint + window block (#495) |
| root `codex/muse-l55-ground` | `50f6e89a` | lane55: Sokkuri79 delivery observer/validator + unit tests (#495) |
| root `codex/muse-l55-ground` | `0fea5ec5` | lane55: Sokkuri79 delivery-bridge handoff docs (#495) |
| root `codex/muse-l55-ground` | (this handoff) | lane55: Sokkuri79 natural haul observation + validator carry parsing (#495) |

Dirty state: none (both clean).

## Interfaces / hooks touched and why

Family-owned native change only, in `pc_port/pc_p2_sokkuri.cpp`:

- `#include "pc_randomizer.h"` (the header already documents "Called by the
  family bind path (or a fixture)").
- `pc_p2_sokkuri_setup()`: after the module bind, calls
  `pc_randomizer_p2_bind_source(view, 79, generator)` and prints
  `P2_SOKKURI_DELIVERY_BIND generator=%u source_id=79`. Rejected ids are
  logged by the callee, never fatal; 79 is in the bindable roster
  (`pc_randomizer_p2_roster.h`). Single-use: consumed by
  `pc_randomizer_p2_corpse_delivered` on delivery.
- `pc_p2_sokkuri_forget()`: also calls `pc_randomizer_p2_forget_source`
  (idempotent) so a recycled actor address can never inherit source 79.

No `teki.h`, `tekiinteraction.cpp`, `tekimgr.cpp`, `goalItem.cpp`, `navi.cpp`,
`pc_p2_preview.cpp`, CMake, roster, admission, or seed-default change. Shared
cargo changes, if needed after the first natural-carry observation, go as a
focused request to #491 — none is requested here.

## Build evidence

Leased heavy-build runner
(`output/muse-wave/control/leased_run.py --configure`), private build dir
`C:\Users\alari\pikmin-randomizer\output\msw\native-l55-build`:

- Log: `C:\Users\alari\pikmin-randomizer\output\muse-wave\l55\build-1789515320859273900.log`
  (SHA-256 `5f2ca00a15e92cd37c3b4df016bfc44c33247cd97b6e7b69cea242e941481684`).
- Native base `7b9ecaa668fd55332073446cdbdaf6424b209ea7`, dirty at build
  `M pc_port/pc_p2_sokkuri.cpp` + `?? tools/p2_muse_ground_fixture.cpp` —
  exactly the committed content (`ecc80b72`); worktree clean at handoff.
- `nectar.exe` SHA-256
  `d10ba07bbf2bff00cc91209c29e31a9f4fad673bf22b49b9cee0b535b70302cc`;
  `ninja -n` → `ninja: no work to do.` Config: Ninja + MinGW g++ Release,
  `PIKMIN_NATIVE_JAUDIO=ON`, `PIKMIN_NATIVE_OPTIMIZE=OFF`.
- First `leased_run --configure` attempt failed on a missing Ninja binary
  (`CMAKE_MAKE_PROGRAM` unset); retried with the Python Scripts Ninja on PATH
  through the same leased wrapper (no direct second build). Evidence log kept.

## Fixture adoption evidence

Adopted this slice — see the slice-2 adoption record above (fresh
arena-carry2, fixture-carry3 `built` provenance, 960x540 observed at
run-carry3 log:7, 20 live reds, no extinction). Prior-slice "UNTESTED, not
adopted" status is superseded by that record; runtime claims cite
run-carry3/capture/native.log line numbers.

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_muse_ground.py -q` → **12 passed**
  (slice 2 adds haul-observation parsing tests: haul-without-receipt stays
  UNTESTED with the max-haul distance in the reason; sub-threshold movement
  is not evidence).
  Log: `C:\Users\alari\pikmin-randomizer\output\muse-wave\l55\pytest-muse-ground2.log`
  (SHA-256 `2675629be57902242564d4f0eeaef6105dbb3081bf5ce3fd27b6a25e02cf9c4b`).
  Log: `C:\Users\alari\pikmin-randomizer\output\muse-wave\l55\pytest-muse-ground.log`
  (SHA-256 `1f9fb0ce1e1c43148f35a905389b3e5fad27d0995fe930449aced89d879ff400`).
- Covers: natural death chain stays untransported without receipt;
  receipt-without-carry stays interface-only; receipt+carry passes; injected
  markers never pass; large prior_health fails; duplicate `new=1` breaks
  exactly-once while `new=0` duplicate keeps it; missing delivery bind fails
  identity.

## Six-gate evidence tables (per identity)

Gates 1–4 for both identities preserve the latest lane-14 natural evidence
(read-only citations); gate 5/6 stay UNTESTED per the lane-14 honesty
corrections (generator `init` re-bind / fixture forget is not full natural
scene re-entry; cargo-free arena had no lane-06 receipt). No gate is
downgraded or upgraded without findings in this slice.

### Concrete source ID

- Source ID: 79 `Sokkuri`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md natural-run2 native.log:782 | natural |
| 2. Autonomous movement and animation | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md natural-run2 native.log:826 | natural |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md natural-run2 native.log:801 | natural |
| 4. Death and corpse | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md natural-run2 native.log:904 | natural |
| 5. Actual transport and reward | UNTESTED | natural haul observed output/muse-wave/l55/run-carry3/capture/native.log:876 (first natural move) and :914 (max 573.55 units); no onion:p2:79 receipt in preview room (randomizer session absent by design) | natural |
| 6. Cleanup and re-entry | UNTESTED | injected (cleanup natural; re-entry would be forced re-bind, not full scene re-entry) | injected |

### Concrete source ID

- Source ID: 28 `ElecBug`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md elecbug-run4a native.log:807 | natural |
| 2. Autonomous movement and animation | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md elecbug-run4a native.log:820 | natural |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md elecbug-run4a native.log:867 | natural |
| 4. Death and corpse | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md elecbug-run4a native.log:1082 | natural |
| 5. Actual transport and reward | UNTESTED | deferred until Sokkuri slice completes; no lane-06 receipt in cargo-free arena | natural |
| 6. Cleanup and re-entry | UNTESTED | injected (cleanup natural; re-entry forced re-bind) | injected |

Checker: `py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_GROUND_HANDOFF.md`
from the lane root → exit 0, no refused PASS rows (verified before handoff).

## Assumptions

- Incremental `P2_SOKKURI_DAMAGE` + small-`prior_health` death = natural combat
  drain (lane-14 signature, unchanged).
- The lane-06 ordinary endpoint (`GoalItem::suckMe` →
  `pc_randomizer_p2_corpse_delivered` → `onion:p2:79`, single-use binding,
  no P1 double-credit) is taken as the delivery mechanism; this slice wires
  the family side only and does not re-prove the provider.
- The Skitter Leaf is harmless; natural lethal death needs the free squad to
  fully drain 120 HP (proven in lane-14 natural-run2, replicated in
  run-carry2/run-carry3: 7 hits 105→15, prior 15.0).
- The cargo-free arena has no Onion, so hauled corpses stall once carriers run
  out of route (~573 units); the stall is reported, not a defect.

## Remaining blockers / next step

1. Exactly-once `onion:p2:79` receipt (owner: this lane, next slice): the
   natural haul is proven; what remains is driving a hauled Sokkuri corpse
   through the real ordinary Onion endpoint with the family bind in a
   randomizer-enabled session and capturing `new=1` plus duplicate `new=0`
   across restart. No dependency blocks this; no new shared hook is expected
   unless that run reveals a real receiver/route defect (then a focused
   request to #491).
2. Full natural scene re-entry beyond generator recreation (lifetime lane
   concern, #397/07): not claimed here; gate 6 stays UNTESTED honestly.
   (Both carry runs also exited before the fixture's terminal line with no
   extinction/FAIL; early-session-end cause unestablished — recorded, not
   claimed.)
3. ElecBug28 delivery/re-entry only after the Sokkuri slice completes (brief
   ordering); its module is untouched.

## Exact reproduction

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
py -3.12 -m pytest tests/test_pikmin2_muse_ground.py -q
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_GROUND_HANDOFF.md
```
