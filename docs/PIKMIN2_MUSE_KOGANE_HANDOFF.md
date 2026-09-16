# Muse Kogane handoff — natural-throw receiver gate (lane 54, #494)

Worker: Muse Spark 1.3 (`opencode/muse-spark-1.3-contributor-free`, lane muse-kogane/l54).
Implementation owner: Codex through shared GitHub account `4laric`.
Parent #219; wave #491. Source ID 9 Kogane is the slice target; 10 Wealthy is
observed-only (UNTESTED, not claimed).

## Scope result

Gate 3 (`attacks_receivers`) is closed with a real thrown-Pikmin /
player-controller event path. The legacy lane 17 acceptance used a forced
fixture attack directive with per-frame held observers; this run removes those
substitutes: one staged captain position, genuine `Navi::throwPiki`
throw-release events, ballistic flight plus the Pikmin's own engagement, and a
free squad with freely wandering beetles. No Kogane-module source change was
needed: no receiver defect was reproduced (the `InteractAttack` ->
`pc_p2_kogane_attacked` -> `doFlip` path behaves per source). Gates 1/2 are
corroborated by this run; gates 4/5/6 are preserved lane 17 evidence, not
relabelled.

## Source ID

```
Source ID: 9 `Kogane`
```

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/muse-wave/l54/throw-run1/stages/e4a17e103dbe4b1198e61d2c9adf4c39/native.log:751 | natural |
| 2. Movement and animation | PASS (natural) | output/muse-wave/l54/throw-run1/stages/e4a17e103dbe4b1198e61d2c9adf4c39/native.log:899 | natural |
| 3. Attacks and receivers | PASS (natural) | output/muse-wave/l54/throw-run1/stages/e4a17e103dbe4b1198e61d2c9adf4c39/native.log:899 | natural |
| 4. Death and corpse | PASS (source-backed N/A corpse) | docs/PIKMIN2_LANE17_DEEPSEEK_HANDOFF.md gate 4; output/dsw/l17-out/fix4-cross/stages/08b36a21ef504eaa8af9d4ac13e45a8b/native-pass0.log:774 | source-backed N/A (burrow, no corpse) |
| 5. Transport and reward | PASS (natural transport) | docs/PIKMIN2_LANE17_DEEPSEEK_HANDOFF.md gate 5; output/dsw/l17-out/fix4-cross/stages/08b36a21ef504eaa8af9d4ac13e45a8b/native-pass0.log:793 ; onion:enemy:9 | natural transport; flip trigger there is a fixture command |
| 6. Cleanup and re-entry | PASS (natural restart) | docs/PIKMIN2_LANE17_DEEPSEEK_HANDOFF.md gate 6; output/dsw/l17-out/fix4-cross/stages/08b36a21ef504eaa8af9d4ac13e45a8b/native-pass2.log:727 | natural restart dedupe |

Gate detail (all line numbers are the `native.log` above unless noted):

- Gate 1: all four roster actors born at exact expected XYZ (`:751`-`:754`;
  TARGET 219001 at -440,30,1500). Roster identity asserted in-fixture.
- Gate 2: the TARGET wandered freely the whole run -- first throw aims 577
  units from the staged captain (`:899` `dist=577.1`), second 654 units
  (`:921`), both at live positions far from the birth anchor. No movement
  pinning exists in the fixture (machine-audited).
- Gate 3: exactly one staged captain row (`:755`), then genuine throw-release
  events `P2_KOGANE_THROW n=1` (`:899`) and `n=2` (`:921`). Every TARGET flip
  strictly follows the first throw: `NATURAL_ATTACK`/`FLIP`/`DROP` flip 1 at
  `:903`-`:905`, flip 2 at `:915`-`:917` (latched Pikmin's own attack loop,
  no new throw), flip 3 at `:926`-`:928`, `ESCAPE` at `:930`, process exit 0
  with `PASS P2_KOGANE_NATURAL_THROW` at `:932`. Drop rows match the audited
  table exactly (flip1 `pellet1=1 nectar=0`, flip2 `nectar=2`, flip3
  `nectar=3`). The fixture source is machine-audited for zero substitutes
  (one staged reposition; no attack directive, mode write, injected press or
  per-frame holder); a legacy forced-AI log with identical flip rows is
  rejected by the validator (unit-tested).
- Honesty notes: the squad was out of throw range for the first ~1900 ticks
  (`THROW_SKIP` rows `:756`-`:887`) -- the selector waited rather than
  forcing. The free squad Half of the run: Wealthy (219002) flipped 3x and
  escaped (`:881`-`:914`) through unscripted idle-AI contact with zero aimed
  throws -- supporting natural-combat evidence, not a Wealthy gate claim.
  Drops in this run were not carried (free squad may drink); pickup and
  restart accounting rest on the preserved lane 17 evidence cited above.

```
Source ID: 10 `Wealthy`
```

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | — | — |
| 2. Movement and animation | UNTESTED | — | — |
| 3. Attacks and receivers | UNTESTED | — | — |
| 4. Death and corpse | UNTESTED | — | — |
| 5. Transport and reward | UNTESTED | — | — |
| 6. Cleanup and re-entry | UNTESTED | — | — |

Wealthy shares the `pc_p2_kogane` module and flipped 3x unscripted in this
run, but no per-identity acceptance run was produced for it; every gate
remains `UNTESTED` for admission purposes.

## Source IDs and files owned

- Source IDs: 9 Kogane (slice target). 10 Wealthy observed-only.
- Native (worktree `output/msw/native-l54`, branch `codex/muse-l54-kogane-native`):
  `tools/p2_muse_kogane_fixture.cpp` (new, owned). `pc_port/pc_p2_kogane.*`
  inspected, not modified (no defect reproduced).
- Root (worktree `output/msw/l54-root`, branch `codex/muse-l54-kogane`):
  `experimental/pikmin2_muse_kogane.py` (new),
  `tests/test_pikmin2_muse_kogane.py` (new),
  `docs/PIKMIN2_MUSE_KOGANE_HANDOFF.md` (this file).
- Legacy `experimental/pikmin2_kogane_*` / `native/pc_port/pc_p2_kogane.*`
  history belongs to lane 17 and was read, never edited.

## Ordered commits (dirty: clean on both)

Root (`codex/muse-l54-kogane`, base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`):
- `2802df23` natural-throw runner + validator + tests (#494)
- `ca8c993c` stage evidence glob fix (#494)
- `4bd0bee1` temporal throw-stimulus check for latched multi-flip chains (#494)

Native (`codex/muse-l54-kogane-native`, base `7b9ecaa668fd55332073446cdbdaf6424b209ea7`):
- `da6f6868` natural-throw RoomApp fixture fragment (#494)

Heads: root `4bd0bee18839c93c41507f14315fd2e89276ab05`, native
`da6f68680f8748519dd97fe124db531d422be91f`.

## Interfaces / hooks touched

- None in shared engine code. The fixture drives two public engine APIs
  exactly as the throw state machine does on `KEY_Action0`
  (`naviState.cpp:2331`-`2342`): `Piki::mFSM->transit(p, PIKISTATE_Flying)` +
  `Navi::throwPiki(p, aim)` after `Navi::findNextThrowPiki()`. The flip itself
  travels `aiAttack.cpp` stick attack -> `InteractAttack::actTeki` ->
  `pc_p2_kogane_attacked` -> `doFlip` (native, unchanged).
- One staged captain `Navi::resetPosition` at tick 1 (reported staging, not
  gameplay); everything else is engine AI/physics.

## Build evidence

- Private build dir `output/msw/native-l54-build`, native
  `da6f68680f8748519dd97fe124db531d422be91f` clean; `pikmin_pc` 616/616 linked,
  `ninja: no work to do.` dry run. Log
  `output/muse-wave/l54/build-1789515259992294600.log` (sha256
  `14d98e2547c323169b4958bd043e18748166a4b398c7ab96ebe08be49de9f592`).
  Production exe `bin/nectar.exe` sha256
  `90196a8336d40787b1ed93577e14aaa09d5746645d7ca4120e84a4eef391cac2`.
- Fixture `fixture-throw1` provenance `built` for expected head
  `da6f68680f8748519dd97fe124db531d422be91f`; `fixture.exe` sha256
  `273b464489eb3bf0df6026d1a97b8b5bb06e96be8d65812e50f99c122c41ea59`.

## Fixture baseline adoption

```text
Fixture baseline adoption
Child issue / lane / implementation owner: #494 / muse-kogane (l54) / Codex through shared 4laric; contributor Muse Spark 1.3
Root commit + dirty state / overlay source: 4bd0bee18839c93c41507f14315fd2e89276ab05 clean / scripts/preview_pikmin2_room.py overlay() with ensure_pikmin_squad (present, lines 66/99)
Native commit + dirty state / worktree / private build directory: da6f68680f8748519dd97fe124db531d422be91f clean / output/msw/native-l54 / output/msw/native-l54-build
Squad change present / window change present (ancestry or source evidence): overlay squad helper present in worktree source; window default inherited from preview base; both confirmed at runtime (see below)
Fresh arena command / run directory / asset and config hashes: py -3.12 -m experimental.pikmin2_muse_kogane run --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --bank C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/bank --output .../throw-run1 --exe .../fixture.exe / output/muse-wave/l54/throw-run1/stages/e4a17e103dbe4b1198e61d2c9adf4c39 / arena.json 3ad0e40cedf96fa37c7f939d38a762aee1db4f6da4b65335559dd5c6c9712fc6
Executable SHA-256 / fixture provenance status if applicable: 273b464489eb3bf0df6026d1a97b8b5bb06e96be8d65812e50f99c122c41ea59 / built (expected head da6f68680f8748519dd97fe124db531d422be91f)
Window setting / observed size and centring evidence: PIKMIN_P2_ROOM_WINDOW=960x540 / native.log:2 SDL window 960x540, :7 preview window set to 960x540 windowed and centered
Live starting Pikmin / active gameplay / no immediate extinction evidence: :760 SQUAD pikis=20; ~2000 ticks of selector/throws/flips/escape; :932 PASS with exit 0; no extinction screen
PASS, FAIL, or BLOCKED; remaining work: PASS for the assigned gate-3 slice; Wealthy identity and any shared combat work explicitly out of scope
```

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_muse_kogane.py -q` -> 12 passed
  (validator accept/reject incl. forced-AI-log discrimination, fixture audit,
  drop-table parity with the legacy audit).
- `py -3.12 -m pytest tests/test_pikmin2_muse_kogane.py tests/test_pikmin2_kogane_collect.py -q`
  -> 35 passed (no legacy regression).
- Runtime validator on the real log: 11/11 checks incl. fixture audit
  (`runtime-evidence.json` sha256
  `cd6aa7419611fa1d9d00e2d2b04e8ed1d90f77d0e18ce065ed40b796c9a57a91`).

## Gate-check output

```
$ py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_KOGANE_HANDOFF.md
9 Kogane (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    accepted [PASS]
10 Wealthy (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
```

No refused PASS; the Wealthy `UNTESTED` table is an honest non-claim and
correctly `ignored`.

## Exact reproduction

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
$env:PYTHONPATH='C:\Users\alari\pikmin-randomizer\output\msw\l54-root'
py -3.12 C:/Users/alari/pikmin-randomizer/output/muse-wave/control/leased_run.py --lane-file C:\Users\alari\pikmin-randomizer\output\muse-wave\l54/lane.json -- py -3.12 -m experimental.pikmin2_muse_kogane build --native C:\Users\alari\pikmin-randomizer\output\msw\native-l54 --build-dir C:\Users\alari\pikmin-randomizer\output\msw\native-l54-build --output C:\Users\alari\pikmin-randomizer\output\muse-wave\l54\fixture-throw1 --head da6f68680f8748519dd97fe124db531d422be91f
py -3.12 -m experimental.pikmin2_muse_kogane run --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --bank C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/bank --output C:/Users/alari/pikmin-randomizer/output/muse-wave/l54/throw-run1 --exe C:/Users/alari/pikmin-randomizer/output/muse-wave/l54/fixture-throw1/fixture.exe
```

Bank note: the visual/sidecar bank is the lane 17 validated install output,
consumed read-only (sidecar sha256 `9a8ae0af67aa768bdc29098db3195f2622a603c4de6cfb3b5639f80426404abb`
as staged); no lane 17 worktree, claim or verdict was edited.
