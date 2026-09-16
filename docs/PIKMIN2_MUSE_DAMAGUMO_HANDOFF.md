# Muse Damagumo56 observer handoff (issue #173, shard enemies-3)

Lane `shard-enemies-3-damagumo56-observer`, generation 2. Additive observer
slice on the integrated Long Legs family. Family modules
(`engine/pc_port/pc_p2_long_legs*.{h,cpp}`) were read-only; no family edit,
no shared edit, no ADMIT, no ledger write, no gameplay PASS claimed.

- Source ID: 56 Damagumo (Beady Long Legs), roster `denied`, all six gates
  UNTESTED before this slice.
- Issue #173 stays OPEN.

## What was delivered

- `experimental/pikmin2_muse_damagumo.py` - dependency-free run-log
  observer / acceptance contract, six-gate verdict with fail-closed
  negatives and explicit injected-run rejection.
- `tests/test_pikmin2_muse_damagumo.py` - 18 focused tests over SYNTHETIC
  logs (positive lifecycle, injected taint, mhealth injection, teleport and
  short walk, wrong child count, generator disagreement, missing walk/dead/
  re-entry/window/completion, extinction, empty log). Synthetic logs are
  labelled; they are not runtime evidence.
- `native/tools/p2_muse_damagumo_fixture.cpp` - standalone engine-free
  marker-contract checker (`-Wall -Wextra -Werror`, no engine headers),
  agreeing with the Python reader on the synthetic positive (exit 0) and a
  synthetic injected log (exit 1); no-argv exit 2.
- `synthetic-contract.log` / `fixture-synthetic.log` / `py-synthetic.json` -
  labeled synthetic agreement evidence only.

## Source pins (read-only retail)

- Damagumo `onInit` `disableEvent(0, EB_LeaveCarcass)` (Damagumo.cpp:80):
  no carcass, no corpse, no corpse transport. Gate 5 is source-backed N/A.
- Damagumo disc speed 100 (`p2LongLegsParmsFor`) through the source
  Stay->Land->Wait->Walk cycle.
- Death with no held treasure births 25 ShijimiChou (Damagumo deathChildren
  25). Held-treasure drop/carry/receipt belongs to the treasure-receipts
  provider (#614) and was NOT built here.

## Six-gate table (Source ID 56 Damagumo)

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | observer contract only; no live Damagumo56 staged in this turn | natural (no runtime) |
| 2. Autonomous movement and animation | UNTESTED | observer contract only; no live Walk observed | natural (no runtime) |
| 3. Attacks and receivers | UNTESTED | observer contract only; no natural squad-combat death observed | natural (no runtime) |
| 4. Death and corpse | UNTESTED | observer contract only; no natural death/child-birth observed | natural (no runtime) |
| 5. Actual transport and reward | N/A | source-backed: Damagumo.cpp:80 disables EB_LeaveCarcass; death reward is child birth (25 ShijimiChou) | source |
| 6. Cleanup and re-entry | UNTESTED | observer contract only; no stage-boundary reset/rebirth observed | natural (no runtime) |

Gates 1-4 and 6 are UNTESTED, not PASS: the observer grammar is ready but no
natural live-actor run was produced this turn.

## Exact blocker (why no runtime evidence)

The lane was provisioned with `native: null` and no private native build or
runtime: there is no provisioned native worktree/build directory for
`shard-enemies-3-damagumo56-observer`, and a natural acceptance run needs an
instrumented Damagumo room app, a heavy leased build, and a live GL 960x540
slot. None of that exists for this lane, and the family files stay read-only
under the completed muse-longlegs owner. The engine-free fixture delivered
here is a contract checker, not the instrumented runtime app.

Next bounded scope: after a private native worktree + build lease and a GL
slot are provisioned, write the instrumented Damagumo fixture app (splice
`tools/preview_p2_room.cpp`, mirroring the l62 pattern), stage a fresh arena
with the overlay squad and a live Damagumo56, and feed the real native.log to
both this observer and the fixture.

## Reproduction (engine-free, no runtime)

```
cd <damagumo56-observer worktree>
py -3.12 -m pytest tests/test_pikmin2_muse_damagumo.py -q   # 18 passed
py -3.12 experimental/pikmin2_muse_damagumo.py synthetic-contract.log  # exit 0
```