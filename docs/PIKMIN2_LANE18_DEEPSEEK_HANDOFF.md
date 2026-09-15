# Lane 18 DeepSeek handoff — small Breadbug ordinary Onion/AP receipt (#220)

Implementation owner: Codex through shared account 4laric. Executing agent:
DeepSeek session, lane 18 (Breadbugs/nests). This slice closes the
"Breadbug ordinary cargo/reward endpoints and restart acceptance" item from the
lane ledger by consuming the already-integrated lane-06 ordinary Onion endpoint
for the small Breadbug. No native change was needed; the shared endpoint already
maps native type 8 to the `Bestiary: Deliver Breadbug` check.

## Source IDs and files owned

- Concrete source enemy: **38 PanModoki** (small Breadbug). Native incarnation in
  this engine: **TEKI_Collec (type 8)**; verified `native/pc_port/pc_randomizer_catalog.h:803`
  maps type 8 → `Bestiary: Deliver Breadbug`, and `randomizer/catalog.py:149`
  records the audited native area as **The Forest Navel** (carry 3).
- Root files added (this lane, no shared files touched):
  - `scripts/p2_breadbug_ordinary_fixture.cpp` — replacement-main fixture that
    kills a real `TEKI_Collec`, drives its corpse through `GoalItem::suckMe`,
    and asserts the durable check.
  - `scripts/p2_breadbug_ordinary_runtime.py` — stages a real schema-9 native
    randomizer session in the Forest Navel, runs the fixture twice, proves
    exactly-once across process restart.
  - `tests/test_pikmin2_breadbug_ordinary.py` — wiring tests (4).

## Ordered commits and dirty state

Root worktree `deepseek/p2-l18`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`:

1. `3c18717` lane18: Breadbug ordinary Onion-endpoint fixture, driver and wiring tests (#220)
2. `be68949` lane18: make Breadbug ordinary fixture exit deterministically under delivery toasts (#220)

Root HEAD `be68949`, clean.

Native worktree `deepseek/p2-l18-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`.
**No native commits, no native dirty state.** This slice consumed lane-06's
integrated ordinary endpoint (`GoalItem::suckMe` -> `pc_randomizer_corpse_delivered`
-> `pc_randomizer_check`, durable `checks.txt`) which already handles type 8; no
`pc_p2_*` module, hook or shared-file edit was required.

## Interfaces/hooks touched and why

None. The ordinary Onion endpoint and the `Bestiary: Deliver Breadbug` catalog
entry are already integrated (lane 06 / lane 01). Reused as-is. The only
breadbug-specific piece is the root fixture/driver that names `TEKI_Collec` and
the check string; no provider/consumer agreement change was needed.

## Build evidence

From `output/dsw/l18-build-evidence.txt`:

```text
2026-09-14T19:32:30 lane=l18 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l18-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l18-build\bin\nectar.exe sha256=dc710712a71fefb0aecd62f6a3444a84d41bfd18f3cdaed0feea8cb1eab796f9 ninja_n="ninja: no work to do." seconds=0
```

- Configure: Ninja + MinGW g++ (absolute `C:/msys64/mingw64/bin/g++.exe`),
  `-DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON` (the maintained JAudio
  config; the default OFF config fails to link on `Jac_NoteDemoSkipped`).
- Full build: 603 objects, `bin/nectar.exe` linked.
- `ninja -n` dry-run: `ninja: no work to do.`
- Fixture built via `scripts/build_pikmin2_fixture.py` against that build:
  `fixture.exe` SHA-256
  `e88217ce5bac24921c7a650281b3160f22c0e2794824e85d5fca7e8822487f96`
  (provenance `status=built`).

## Fixture adoption evidence

- Fixture `main` mirrors the maintained startup: `pc_window_init(..., 960, 540)`
  + `pc_window_center()`; observed log line
  `[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)`.
- Live starting squad observed: `[Pikmin Randomizer] START_READY stage=2 field_red=20`.
- Run used a real campaign stage (Forest Navel) with `PIKMIN_P2_ROOM_WINDOW=960x540`
  and `PYTHONUTF8=1`; run wrapped in `slot.py run gl l18`.

## Six-gate table (natural vs injected)

| Gate | Result | Evidence / label |
|---|---|---|
| 1. Exact identity and spawn | **PASS** | `P2_BREADBUG_ORD_TARGET type=8 x=145.4 y=-177.1 z=2326.5` (vanilla Forest Navel; no injection) |
| 2. Autonomous movement and animation | source-backed N/A for this slice | Not exercised here (target killed at frame 9); prior lane evidence (`docs/PIKMIN2_BREADBUG_ACTOR_RUNTIME.md`) shows 478u movement PASS in the proxy arena |
| 3. Attacks and receivers | **PASS (receiver natural; attack injected)** | Captain `InteractAttack` (scripted test input, 100000 dmg) accepted by the real `TEKI_Collec` receiver; health→0 through the natural damage/FSM path |
| 4. Death and corpse | **PASS (natural)** | Death at frame 9, real corpse `target->mPellet` with `mDeadState==2`, `P2_BREADBUG_ORD_CORPSE ready` (contrast prior injected `mHealth=0` which left `corpse=0`) |
| 5. Actual transport and reward | **PASS (reward real; transport injected)** | `CHECK 45 Bestiary: Deliver Breadbug` written to `checks.txt` via real `GoalItem::suckMe`; natural carry moved only 8.81u (`natural=0`), so the endpoint was invoked directly — labelled intervention, natural transport remains lane 04 |
| 6. Cleanup and re-entry | **PASS (re-entry/exactly-once)** | run2 (fresh process, same session) boots the same day, re-kills the respawned Breadbug, and grants **0** new checks; full actor teardown not separately re-exercised |

## Runtime evidence (exactly-once across restart)

```text
schema 9 catalog gameplay-checks-v9 profile navel-day2
[run1] exit=0 target_check_lines=1 checks=['Population: 10 total Red Pikmin', 'Bestiary: Deliver Breadbug']
[run2] exit=0 target_check_lines=0 checks=[]
EXACTLY_ONCE_ACROSS_RESTART: True
```

- run1 dir: `output/dsw/l18-out/runtime/session-442af6e5/runs/e83cd7786bc8a9a5608bbe54f9ad02c23ee68d6519a184c28c575a0e2e0a7286`,
  log SHA-256 `527b92cf710e46de30bdc5367ae8e74c3260dcc9c92268d2b86f789abd6c6d12`.
- run2 dir: `output/dsw/l18-out/runtime/session-442af6e5/runs/12e51706cf16a61e583161baa4e5c4886d1d2980f2349e0e37ae7d59e678ff36`,
  log SHA-256 `d30f6c329446b3ba0ef960fd03d6201897a145ff57969e7fc469ad71dc8b8253`.
- run1 log tail: `P2_BREADBUG_ORD_FALLBACK_SUCKME natural_carry=0`,
  `CHECK 45 Bestiary: Deliver Breadbug`, `P2_BREADBUG_ORD_RESULT natural_carry=0 checked=1`,
  `PASS P2_BREADBUG_ORDINARY_RECEIPT`.

## Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_breadbug_ordinary.py -q` -> 4 passed.
- `py -3.12 -m pytest tests/test_pikmin2_breadbug_ordinary.py tests/test_pikmin2_breadbug_rewards.py tests/test_pikmin2_breadbug_contest.py -q`
  -> 40 passed.

## Assumptions made

- The native build must be configured with `-DPIKMIN_NATIVE_JAUDIO=ON` (absolute
  MinGW g++/gcc) to link; this matches the other lanes' build caches. The
  `build_lane.py` wrapper does not add JAudio, so the first configure was done
  through `slot.py run build`, and `build_lane.py` then records the incremental
  evidence.
- "Ordinary" means the ordinary Onion/AP ledger (durable `checks.txt`) — not the
  experimental Pod economy. This is the exactly-once ordinary reward endpoint the
  lane ledger asked for.
- The Breadbug is sourced in the Forest Navel (`starting_area='navel'`), per the
  audited catalog area; the fixture mirrors lane-06's `p2_ordinary_receipt_fixture.cpp`
  with `TEKI_Collec` and the breadbug check name.
- Natural Pikmin carry does not move the corpse in this unattended fixture (no
  whistle/carry command is issued), so label transport as injected; this matches
  lane-06's Dwarf Bulborb evidence and keeps natural transport with lane 04.

## Remaining blockers (provider lanes named)

- Natural Pikmin transport of the corpse: lane 04.
- Small-Breadbug P2 contested cargo / interruption release with a real cargo
  owner, and native exactly-once receipt persistence wired into a generated
  session (beyond this fixture): lane 06 native save bridge + lane 07 lifetime
  owner (open on #168/#220/#441). The Giant press/contest/digest/defeat ally
  evidence is separate `pc_p2_giant_breadbug_actor` work, not repeated here.

## Exact reproduction command

```powershell
$env:PATH = 'C:/msys64/mingw64/bin;C:\Users\alari\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts;' + $env:PATH
$env:PYTHONUTF8 = '1'
$env:PIKMIN_P2_ROOM_WINDOW = '960x540'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l18 -- py -3.12 scripts/p2_breadbug_ordinary_runtime.py --exe C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/fixture-build/fixture.exe --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --output C:/Users/alari/pikmin-randomizer/output/dsw/l18-out/runtime
```
