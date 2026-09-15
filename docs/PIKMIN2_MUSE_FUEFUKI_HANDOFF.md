# Muse lane l57 (Fuefuki41) — observer slice handoff

Slice: **correlated natural-spawn observer + negative tests for gate 1**.
This slice builds the additive acceptance contract (same real generated
slot/generator across placement, source-41 resolve and Fuefuki actor binding
markers) and proves it fail-closed. It runs no gameplay and changes no shared
placement, packaging, family FSM, or legacy lane files. Gate 1 stays BLOCKED
on the muse-placement (l52/#492) and muse-packaging (l53/#493) candidates;
gates 2–6 stay exactly as the claim-held legacy l28 lane left them.

- Source enemy: **Fuefuki (Antenna Beetle), EnemyID 41** (`EnemyID_Fuefuki`,
  `BDT_Strong`). Roster: `docs/PIKMIN2_ENEMY_ROSTER.json` source_id 41,
  role source, spawnable.
- Legacy l28 lane is claim-held: inspected read-only
  (`output/deepseek-wave/handoffs/l28.md`, diagnostic slice + slices 3–4);
  no edit to its worktree, family FSM, or handoff.
- Parent issues: family #245; wave #491; child #497.

## Source ID and files owned (all new, additive)

- Root (new):
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
- Native (new, engine-independent):
  - `native/tools/p2_muse_fuefuki_fixture.cpp` — standalone stdlib-only
    log checker implementing the same triple contract; exit 0 iff
    correlated, 1 otherwise. No engine headers; not linked into any game
    target.

No shared file touched. No native engine build required for this slice
(no engine source changed); the fixture compiles standalone with MinGW
g++ 16.2.0 `-Wall -Wextra -Werror`.

## Ordered commits (clean)

Root branch `codex/muse-l57-fuefuki` (base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`):

- `ec53d25b0822d3b999495a17b913bdd140c536b7` lane57: Fuefuki gate-1 correlated observer + negative tests (#497)
- (this commit) lane57: observer-slice handoff doc (#497)

Native branch `codex/muse-l57-fuefuki-native` (base `7b9ecaa668fd55332073446cdbdaf6424b209ea7`):

- `a0b559fa5954444c0a10afb6f4020a1f72ce58f0` lane57: Fuefuki gate-1 standalone log-checker fixture (#497)

## Marker contract audited (read-only, this worktree)

- `native/pc_port/pc_p2_generated_placement.cpp:7-30` — `default` case
  returns false: **no case-41 bind arm** (owned by muse-placement l52).
- `src/plugPikiNakata/genteki.cpp:141` — `P2_SEED_RESOLVE
  source_id=%u target=%u ...` with `target = pc_randomizer_generator_id`
  (the seed slot uid).
- `src/plugPikiNakata/genteki.cpp:148-150` — birth-hook
  `pc_p2_placement_probe_birth(..., info.mGenerator->_70, uid, ...)`:
  placement `generator` is the engine file id, `slot` is the seed uid.
- `native/pc_port/pc_p2_hardlanes.cpp:711` — `P2_HARDLANES_READY
  family=Fuefuki vehicle=Napkid gen=%u ...` with `gen = _70` file id;
  `P2_FUEFUKI_TEKI_* generator=%u` markers carry the same file id.
- `randomizer/p2_placement_catalog.py` — no `(41, 'Fuefuki', ...)` candidate
  row in this worktree (owned by muse-placement l52).

Correlation rule implemented: `placement.slot == seed.target` (uid) AND
`placement.generator == binding.gen` (file id).

## Tests and tool runs

- `py -3.12 -m pytest tests/test_pikmin2_muse_fuefuki.py -q` → **12 passed**.
- `py -3.12 -m pytest tests/ -q -k fuefuki` → **45 passed** (12 new + 33
  legacy l28 Fuefuki suites, no regression).
- Standalone fixture compile (MinGW g++ 16.2.0, `-Wall -Wextra -Werror`,
  `C:\msys64\mingw64\bin` on PATH) → exit 0, clean.
- Fixture on correlated sample log → `gate1_ok=1`, exit 0.
- Fixture on proxy-without-seed sample log (legacy l28 teki-receipt shape:
  `P2_HARDLANES_READY family=Fuefuki` + `P2_FUEFUKI_TEKI_DEAD`, no
  `P2_SEED_RESOLVE`) → `gate1_ok=0`, exit 1.
- Python observer agrees with the fixture on both samples.
- `py -3.12 scripts/check_p2_handoff_gates.py
  docs/PIKMIN2_MUSE_FUEFUKI_HANDOFF.md` → EXIT=0 (no refused PASS rows).

## Concrete source ID

- Source ID: 41 `Fuefuki`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | experimental/pikmin2_muse_fuefuki.py correlated triple unsatisfied: no P2_SEED_RESOLVE source_id=41 leg exists; native/pc_port/pc_p2_generated_placement.cpp:7-30 has no case-41 bind arm; randomizer/p2_placement_catalog.py has no (41, Fuefuki) candidate row. Awaiting reviewed muse-placement l52/#492 and muse-packaging l53/#493 candidates | natural (no runtime attempted; observer only) |
| 2. Autonomous movement and animation | UNTESTED | Preserved: accepted PASS under claim-held legacy l28 slice 4 (output/deepseek-wave/handoffs/l28.md slice 4, run-motion.log). No new run in this observer slice; ledger unchanged | natural (legacy) |
| 3. Attacks and receivers | UNTESTED | Preserved: accepted PASS under claim-held legacy l28 slice 4 (output/deepseek-wave/handoffs/l28.md slice 4, engine InteractAttack receiver). No new run in this observer slice; ledger unchanged | natural (legacy) |
| 4. Death and corpse | UNTESTED | Preserved: accepted PASS under claim-held legacy l28 slice 3 (output/deepseek-wave/handoffs/l28.md slice 3, teki-receipt run.log). No new run in this observer slice; ledger unchanged | natural (legacy) |
| 5. Actual transport and reward | UNTESTED | Preserved: accepted PASS under claim-held legacy l28 slice 3 (output/deepseek-wave/handoffs/l28.md slice 3, P2_POD_RECEIPT corpse:fuefuki:245001). No new run in this observer slice; ledger unchanged | natural (legacy) |
| 6. Cleanup and re-entry | UNTESTED | Preserved: accepted PASS under claim-held legacy l28 slice 4 (output/deepseek-wave/handoffs/l28.md slice 4, P2_FUEFUKI_RESET/REENTRY). No new run in this observer slice; ledger unchanged | natural (legacy) |

## Remaining work (exact dependency record)

1. muse-placement l52/#492: candidate-only legal-slot profile for 41 +
   narrow `case 41` native bind arm in `pc_p2_generated_placement.cpp`
   (shared file owned by that lane). No `dependency-ready.json` published
   yet at `output/muse-wave/l52/`.
2. muse-packaging l53/#493: candidate-only generated-session staging for
   41. No `dependency-ready.json` published yet at `output/muse-wave/l53/`.
3. On reviewed candidate commits: cherry-pick into this private worktree
   (record base/order, keep dependency changes separate from authored
   scope), regenerate a fresh private arena with the current
   starting-squad overlay, build via the leased runner, run at 960x540,
   and feed the real log through both observers for a gate-1 verdict.

## One exact reproduction command

```
cd C:/Users/alari/pikmin-randomizer/output/msw/l57-root
py -3.12 -m pytest tests/test_pikmin2_muse_fuefuki.py -q   # 12 passed
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_FUEFUKI_HANDOFF.md  # EXIT=0
```
