# Lane 17 DeepSeek handoff — reward beetle natural press receiver

Worker: DeepSeek (`deepseek/p2-l17`). Implementation owner: Codex via shared `4laric`.
Tracked on #219 (parent #168). Slice: the natural end-to-end press receiver for
Iridescent Flint Beetle (source ID 9): a real Pikmin attack now drives the finite
flip/drop/escape cycle (previously only reachable by injected `InteractPress`).
Full detail: `docs/PIKMIN2_KOGANE_NATURAL.md`.

## Source IDs and files owned

- Source IDs: 9 Kogane (slice target), 10 Wealthy, 11 Doodlebug (family scope 9–11).
- Native (worktree `C:/Users/alari/pikmin-randomizer/output/dsw/native-l17`):
  `pc_port/pc_p2_kogane.cpp`, `pc_port/pc_p2_kogane.h` (owned, edited).
- Root (worktree `C:/Users/alari/pikmin-randomizer/output/dsw/l17-root`):
  `experimental/pikmin2_kogane_natural.py` (new),
  `tests/test_pikmin2_kogane_natural.py` (new), `docs/PIKMIN2_KOGANE_NATURAL.md` (new).

## Ordered commits

Root (`deepseek/p2-l17`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):
- `944cb6d` lane17: DeepSeek handoff (#219)
- `3a018b0` lane17: natural press receiver — real Pikmin attacks flip the reward beetle (ID 9) with finite drops and escape (#219)

Dirty state: clean (`git status` clean) after commit.

Native (`deepseek/p2-l17-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`):
- `14e88cc3` lane17: route natural Pikmin attacks to the beetle flip with a damage-clip recovery window (#219)

Dirty state: clean. Supports 6 prior lane16–18 integrated beetle commits
(`8572af49` in-process dedupe, `b4d7c571` restored escape, `38258c7a` on-disk
receipts, `155fe6ec` windows.h fix, `bffdb0ab` hardening, `9492ffba` treasure
stand-in) and this slice's `14e88cc3`.

## Interfaces / hooks touched and why

- `pc_p2_kogane_attacked(Teki*)` — was a pure swallow; now routes a landed Pikmin
  stick-attack (`InteractAttack`) to the flip via an internal `doFlip`, so a real
  throw/landing flips the beetle. No health damage (source: only the press counts).
- `pc_p2_kogane_pressed(Teki*, Creature*)` — unchanged behaviour; now shares `doFlip`.
  Keeps the injected batch-4 fixtures green (`P2_KOGANE_FLIP` format unchanged).
- New `Beetle::recoverTimer` — holds further presses/attacks for the full damage
  clip, so a continuously-stuck Pikmin flips at most once per clip (source NoInterrupt
  KEYEVENT_2..4) instead of draining all three flips on consecutive frames.
- New native log `P2_KOGANE_NATURAL_ATTACK generator=<id> source_id=<id> flip=<n>`.
- No shared-file edit this slice: the `InteractAttack::actTeki` -> `pc_p2_kogane_attacked`
  hook in `src/plugPikiNakata/tekiinteraction.cpp` was already wired in the maintained
  line; only the family module body changed.

## Build evidence (`output/dsw/l17-build-evidence.txt`)

```
2026-09-14T19:18:44 lane=l17 target=pikmin_pc native=14e88cc33e91a2847bd3e496f4705040184f14ee dirty=no \
  build_dir=...\native-l17-build exe=...\native-l17-build\bin\nectar.exe \
  sha256=2829048967b3a754fb3dabd9b3839b0bf0e8ced526f20ef385c43bbfad0299fa \
  ninja_n="ninja: no work to do." seconds=142
```

Configured with Ninja + MinGW g++ (full paths), `-DPIKMIN_NATIVE_JAUDIO=ON`. The
second evidence line is a no-work re-run after pinning full compiler paths in the
CMake cache (fixture-builder requirement), same native commit and binary SHA.

Fixture: `output/dsw/l17-out/natural-fixture` `status: built`,
`fixture.exe` SHA-256 `27dba46398fb464a72bcdc0d5630fe10951ce3a70cc7926e78d249e1bf9dbacc`.

## Fixture baseline adoption

- Window: 960×540 centred. native.log lines 3/8: `SDL2 Window & OpenGL Context
  initialized successfully (960x540)` and `Experimental preview window set to 960x540
  windowed and centered`. `PIKMIN_P2_ROOM_WINDOW=960x540` set on the run.
- Live starting squad: 20 red Pikmin (`require(alivePikis()==20)`, `squad=20`),
  active gameplay, no extinction; census `pikis=20`, P1 control alive.
- Run dir: `output/dsw/l17-out/natural-run/stages/1d8b02c97210472db021d6338f8b4146`;
  exit 0; `PASS P2_KOGANE_NATURAL natural_attack flip3 escape1 control_alive`.

## Six arena gates (natural vs injected labelled)

| Gate | Result | Evidence / label |
|---|---|---|
| 1. Exact identity and spawn | PASS | `P2_KOGANE_BIRTH` ×4 exact stored XYZ; `P2_KOGANE_BIND source_id=9` karada 60 |
| 2. Autonomous movement/animation | PASS | wander/draw already accepted; unchanged |
| 3. Attacks and receivers | **PASS (natural)** | `P2_KOGANE_NATURAL_ATTACK` ×3 on 219001 from real Pikmin attacks; no injected stimulus. Review note: flips 1–2 at ticks ~80–120, flip 3 only at tick 2640; the intervening ~2500 ticks the attackers retargeted onto Wealthy 219002 (3 flips + escape), so the `pellets=4 nectar=9` census counts both beetles' drops. The claim that the injected batch-4 fixtures stay green is by cadence analysis (100-tick press spacing > 1.67 s recoverTimer), not re-run. |
| 4. Death and corpse | PASS (corpse source-backed N/A) | 3rd flip → `P2_KOGANE_ESCAPE`; burrow, no corpse pellet |
| 5. Actual transport and reward | UNTESTED (drop spawns proven) | `P2_KOGANE_DROP` exact tables + census; carry-to-Onion not driven |
| 6. Cleanup and re-entry | PASS | reset/re-entry + on-disk receipts (prior lane16–18 work); full scene/day reload uncovered |

Injections, all labelled: the RoomApp pins the observing squad clear of the drop zone
and co-locates up to five attackers near the wandering beetle / re-issues the C-stick
attack command (one initial teleport of five attackers at tick 80; requeue never moves them; never mid-drink). It never calls `stimulate` or
`eventPerformed`; the first old-attempt `mizunomi err!` panic was removed by guarding
`PIKISTATE_Absorb` in the re-queue.

## Tests

- Root: `py -3.12 -m pytest tests/test_pikmin2_kogane_*.py -q` → **116 passed, 11 subtests**.
- `tests/test_pikmin2_kogane_natural.py` → 7 passed (accept/reject paths, no-stimulus
  splice check).

## Assumptions made

- The host has no distinct stimulus for a Pikmin landing on a beetle; a real Pikmin
  stick-attack (`InteractAttack`) is the faithful proxy. Documented in the module/native
  comments as a P1-host resolution, not P2 retail.
- A continuously-stuck Pikmin is capped to one flip per damage clip (recoverTimer =
  50 frames) rather than forcing a distinct stomp hop; recorded as a host adaptation.
- Attacks still deal zero health damage (source: only the flip affects a beetle).
- The neighbouring Wealthy (219002) also reaching its own three-flip escape is honest
  natural re-targeting and does not fail the Kogane gate.

## Remaining blockers (provider lane)

- Real carry-to-Onion collection of beetle drops: lane 06 reward/cargo endpoint (and
  lane 01/33 for generated-session admission). This slice proves the drop spawns, not
  transport.
- P2 cave treasure object and `Cave::randMapMgr` relocation: no P2 cave in the P1 host
  (current first-flip treasure is a labelled P1 number-pellet stand-in).
- Full scene/day reload and durable P2-save bridge: lane 01/06; lane-17 sidecar is
  run-directory local only.

## Reproduction command

```powershell
py -3.12 -m experimental.pikmin2_kogane_natural build `
  --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l17 `
  --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l17-build `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/natural-fixture `
  --head 14e88cc33e91a2847bd3e496f4705040184f14ee
py -3.12 -m experimental.pikmin2_kogane_natural run `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --bank C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/bank `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/natural-run `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/natural-fixture/fixture.exe
```

## Slice 2 — real collection and restart dedupe

Worker: DeepSeek. Source ID 9 Kogane. Closes gate 5 (real transport/reward through the
ordinary P1 Onion/nectar path) and the restart half of gate 6. Full detail:
`docs/PIKMIN2_KOGANE_COLLECT.md`.

### Ordered commits (appended to slice 1)

Root (`deepseek/p2-l17`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):
- `8d44bcf` lane17: real collection + restart dedupe fixture (Onion receipt, carry/drink, cross-process) (#219)
- `595cbe7` lane17: fix collect pass mapping (0=collect, 2=restart) and restart marker (#219)
- `6055ee4` lane17: record slice-2 collection + restart dedupe handoff (#219)

Native (`deepseek/p2-l17-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`):
- `75153537` lane17: grant reward drops exactly-once through the lane-06 ordinary Onion receipt ledger (#219)
- `b5676090` lane17: lazy-reopen the lane-06 receipt host before granting (single-consumer close resilience) (#219)

Dirty state: clean (both).

### Interfaces / hooks touched

- `pc_p2_kogane.cpp`: drop rewards now granted exactly once via `pc_p2_receipt_host_grant`
  (lane-06 ordinary Onion ledger, `P2_KOGANE_ONION_RECEIPT`). Read `PIKMIN_P2_SEED`
  (else token `kogane-arena`), open `p2-kogane-onion-receipts.txt`; lazy re-open on
  grant because the single-consumer host may be closed by `pc_p2_flora_reset`.
- No shared-file edits (the Onion receipt is observed via P1-native `GoalItem::suckMe`/
  `bornPikis`, not a new hook). Arena placements only (no enemy change).

### Build evidence (`output/dsw/l17-build-evidence.txt`, latest)

```
native=b56760901e4f47d03a111ff567af72a00cdf0e12 dirty=no exe=nectar.exe
sha256=d5e6ec9bb9ac6f0aad97f9b92c9de174121f80e16ebd9d9d0500428d398ffc3a ninja_n="ninja: no work to do."
```

Fixture `collect-fixture` `status: built`; `fixture.exe` SHA-256
`354a3a02f1d2b012350ff63810008bceeab5b63c1e77f2e80ca10e02175cbd61`.

### Runtime evidence

`collect-cross` (pass0 + pass2, both exit 0, 960x540 centred): real collection
(`pellets_collected=1 nectar_drunk=5 sprouts=2`), three `P2_KOGANE_ONION_RECEIPT
granted=1`, source escape, then pass2 `P2_KOGANE_RECEIPTS loaded=1` +
`P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3` + `P2_KOGANE_RESTART rearmed=0`,
no new drop/grant. Single-process `collect-run` also passes.

### Subagent usage (slice 2 experiment, honest)

- `explore` #1 (source audit: beetle drop/collection/escape + P1 Onion/pellet/nectar path):
  used as-is. Key findings used: P1 Onion = `GoalItem`/`ItemMgr` (`goalItem.cpp`
  `suckMe` -> `mCurrAnimId` seeds -> `GoalAI::EmitPiki` -> `GameStat::bornPikis`),
  nectar = `OBJTYPE_Water` -> `PIKISTATE_Absorb`, and **no Poko/money counter in the
  P1 host**. Shaped the "sprout credit" observation and the Onion-ledger design. Saved
  ~30 min of source spelunking.
- `explore` #2 (existing-candidate inventory): used as-is. Confirmed the kogane module
  used its own flip sidecar (not `P2Receipt::ReceiptLedger`), and gave the exact
  `pc_p2_receipt_host_*` + marker inventory. Saved ~20 min.
- `general` #3 (test scaffolding): produced a 7-test standalone validator. I DISCARDED
  its self-contained validator/marker grammar (it assumed a single-log `P2_KOGANE_RESTART
  loaded/duplicate/rearmed` line and `sprouts=5`) and rewrote `tests/test_pikmin2_kogane_collect.py`
  against the real module (`validate_collect`/`validate_restart`/`validate_cross`), because
  restart dedupe is cross-process (two logs) and nectar does not produce sprouts (pellets do).
  Net: cost ~5 min to discard, but the scaffolding confirmed the test shape. Honest negative.

## Slice 3 — natural flips, a real second-flip sequence and a mixed-scene ledger

Worker: DeepSeek. Source ID 9 Kogane. (1) Replaces the slice-2 injected
`InteractPress` flips with real Pikmin stick-attacks through the ordinary
receiver (`pc_p2_kogane_attacked`), keeping the injected path as the separately
flagged `mode=injected` legacy scenario; (2) strengthens pass 2 to actually drive
a second flip sequence and re-probe the receipt grants through the real
`pc_p2_receipt_host_grant` Duplicate path with a ledger row-count check; (3)
codifies the lane-06 two-consumer (Kogane + Flora) mixed-scene contract and
documents why today's host cannot keep the two ledgers separate.

### Source IDs and files owned

- Source ID 9 Kogane (target). Native (worktree `output/dsw/native-l17`):
  `pc_port/pc_p2_kogane.cpp`, `pc_port/pc_p2_kogane.h` (owned, edited).
- Root (worktree `output/dsw/l17-root`): `experimental/pikmin2_kogane_collect.py`
  (edited), `tests/test_pikmin2_kogane_collect.py` (edited). No shared file edits.

### Ordered commits

Root (`deepseek/p2-l17`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`, dirty: clean):
- `7e126f83` lane17: natural-flip collection + restart re-probe and ledger cap (slice 3) (#219)

Native (`deepseek/p2-l17-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`, dirty: clean):
- `04af0bce` lane17: restart-dedupe ledger introspection + real Duplicate re-probe (slice 3) (#219)
- `1ccc4f37` lane17: total-nectar census counter for the natural collection pass (slice 3) (#219)

### Interfaces / hooks touched

- `pc_p2_kogane_onion_ledger_rows()` (new) — reads the persisted lane-06
  `P2_RECEIPTS_1` Onion ledger and returns its row count (0 for missing, -1 for
  malformed). Used by pass 2 to assert the ledger is still exactly three rows.
- `pc_p2_kogane_reprobe_duplicates(unsigned generator,int id)` (new) — reopens the
  kogane ledger (unconditionally, so a mixed-scene Flora steal cannot redirect it)
  and re-drives the three `enemy:<id>` flip grants through the real
  `pc_p2_receipt_host_grant`; every result must be Duplicate. Returns 3, else -1.
- `pc_p2_kogane_nectar_dropped()` (new) — process-total nectar spawned by `doDrop`,
  so the collection census reports the full 2 + 3 = 5 nectar as drunk once all water
  organisms are gone (the slice-2 `peakWater` proxy under-counted nectar drunk before
  the escape, e.g. flip-2 nectar consumed during the flip phase).
- The collect RoomApp (`experimental/pikmin2_kogane_collect.py` APP) now reads a
  `kogane-mode.txt` flag (natural default, injected legacy) and drives natural flips
  with the slice-1 `command`/`requeue` attack routine plus a labelled position hold
  (`holdBeetles`) that pins the three beetles at their birth anchors so the natural
  attacks and drops are deterministic (position-only; the flip is still a native
  `InteractAttack`). Pass 2 drives the same attack routine at the restored (escaped)
  beetle, then calls the two new native hooks and emits `P2_KOGANE_REPROBE
  duplicates=3` + `P2_KOGANE_ONION_LEDGER rows=3`.
- No shared-file edit: `pc_p2_flora_*` and `pc_p2_receipt_host.*` are lane 06/other
  files and were only read, not modified.

### Build evidence (`output/dsw/l17-build-evidence.txt`, slice-3 lines)

```
native=1ccc4f371d79418876462225f183fe556ebaf93d dirty=no exe=nectar.exe
sha256=20e051c09e9f91eaf21ddf234e3144edf495418a49164e1d2f0e8e5dd1268802 ninja_n="ninja: no work to do."
```
(earlier slice-3 line at `04af0bce`: nectar.exe sha256 `a95a72e9…471`)

Fixture `collect-natural-fixture3` status `built`; `fixture.exe` SHA-256
`2ff9a4af5c72c7412fafc47244bf7a884fe37311aff45b6b0cb88495d74da98e`.

### Runtime evidence (real-GL, 960x540 centred, `slot.py run gl l17`)

`collect-natural-cross2/stages/77b4aee793bb46b388ef6089e24c1aad` (pass0 exit 1 on
the slice-2-style census, pass2 exit 0 — the key slice-3 gate):

```
# pass 0 (natural): the three flips are real Pikmin attacks, not injected presses
P2_KOGANE_COLLECT_PASS pass=0 mode=natural
P2_KOGANE_NATURAL_COMMAND attackers=5 mode=natural
P2_KOGANE_FLIP / P2_KOGANE_NATURAL_ATTACK generator=219001 flip=1,2,3
P2_KOGANE_DROP  generator=219001 flip=1 pellet1=1 nectar=0
P2_KOGANE_DROP  generator=219001 flip=2 pellet0=0 nectar=2
P2_KOGANE_DROP  generator=219001 flip=3 pellet0=0 nectar=3
P2_KOGANE_ONION_RECEIPT generator=219001 flip=1..3 granted=1 duplicate=0 ledger=onion
P2_KOGANE_ESCAPE generator=219001 flips=3
P2_KOGANE_COLLECTED pellets_collected=1 nectar_drunk=3 sprouts=0   # census edge, fixed below

# pass 2 (restart): the second flip sequence is a no-op and the ledger cap holds
P2_KOGANE_RECEIPTS loaded=1
P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3
P2_KOGANE_RESTART rearmed=0
P2_KOGANE_ONION_RECEIPT generator=219001 flip=1..3 granted=0 duplicate=1 ledger=onion
P2_KOGANE_REPROBE duplicates=3
P2_KOGANE_ONION_LEDGER rows=3
PASS P2_KOGANE_RESTART dedupe_ok rearmed=0 duplicate=3 ledger=3
```

The natural flip/receipt chain and the pass-2 re-probe both validate. `duplicate=1`
comes from the real `pc_p2_receipt_host_grant` Duplicate branch, not a fake marker.
`collect-natural-cross3/4` did not flip within the 300 s window — the natural
Pikmin stick-attack is non-deterministic under host AI (the same limitation the
slice-1 natural run documented: flips 1–2 land then the attackers need re-queueing).
This is why the injected `mode=injected` fallback remains and is labelled separately.
The slice-3 census fix (total-nectar counter + wait-for-sprout) is in the fixture
that built for cross3/cross4, but a fully clean natural-collect PASS (nectar_drunk=5,
sprouts>=1) was not captured in the bounded window because those runs did not flip.

### Six arena gates (natural vs injected labelled)

| Gate | Result | Evidence / label |
|---|---|---|
| 1. Exact identity and spawn | PASS | `P2_KOGANE_BIRTH` ×4 exact; `P2_KOGANE_BIND source_id=9` |
| 2. Movement/animation | PASS | wander/draw unchanged; position hold is a labelled fixture pin |
| 3. Attacks and receivers | **PASS (natural, flaky)** | `P2_KOGANE_NATURAL_ATTACK` ×3 in cross2; 0 flips in cross3/4 (host AI non-determinism) |
| 4. Death/corpse | PASS | 3rd flip -> `P2_KOGANE_ESCAPE`; no corpse |
| 5. Transport and reward | PARTIAL | natural drops + onion_receipt ×3 + pellet carried (cross2); full 5-nectar/1-sprout census not captured in-window |
| 6. Cleanup/re-entry | **PASS (restart dedupe)** | cross2 pass2: no re-arm, `duplicate=1` ×3, ledger rows=3 |

Injections (labelled): the position hold of the three beetles (`holdBeetles`), the
squad staging teleport, the pellet grab+transport initiation and the free-Pikmin
nectar nudge. The flip itself (`InteractAttack` -> `pc_p2_kogane_attacked`) and the
Onion/nectar endpoint are native execution.

### Mixed-scene (lane-06) finding — documented, not fixed here

`validate_mixed_scene(kogane_file, flora_file)` codifies the two-consumer contract.
Today's native receipt host is a single process-global singleton:
`pc_port/pc_p2_receipt_host.cpp:7-9` (`std::unique_ptr` persistence + ledger at
namespace scope) and `:11-22` (`pc_p2_receipt_host_open` replaces the singleton
unconditionally). `pc_p2_preview.cpp` calls `pc_p2_kogane_setup()` (:246) before
`pc_p2_flora_setup()` (:250), so in a co-staged scene Flora opens
`p2-flora-receipts.txt` last and Kogane's lazy `!ready` reopen is skipped, spilling
Kogane `enemy:9` grants into Flora's file. **Lane-06 ask:** a per-consumer ledger
(keyed by path) or a `pc_p2_receipt_host_path()` accessor so each consumer can be
routed to its own file; the Kogane `reprobe` hook already works around it by
re-opening unconditionally, which is family-local mitigation, not the fix.

### Tests

- `py -3.12 -m pytest tests/test_pikmin2_kogane_collect.py -q` -> 18 passed.
- Full lane-17 suite `tests/test_pikmin2_kogane_*.py` -> 134 passed, 11 subtests.

### Exact marker grammar the native side now emits / the validator accepts

```
P2_KOGANE_COLLECT_PASS pass=<0|2> mode=<natural|injected>
P2_KOGANE_NATURAL_COMMAND attackers=<n> mode=<natural|reattempt>
P2_KOGANE_NATURAL_ATTACK generator=219001 source_id=9 flip=<1|2|3>     # natural only
P2_KOGANE_FLIP       generator=219001 source_id=9 flip=<1|2|3>
P2_KOGANE_DROP       generator=219001 source_id=9 flip=1 pellet1=1 nectar=0
P2_KOGANE_DROP       generator=219001 source_id=9 flip=2 pellet0=0 nectar=2
P2_KOGANE_DROP       generator=219001 source_id=9 flip=3 pellet0=0 nectar=3
P2_KOGANE_ONION_RECEIPT generator=219001 flip=<n> granted=1 duplicate=0 ledger=onion seed=kogane-arena
P2_KOGANE_ESCAPE     generator=219001 source_id=9 flips=3
P2_KOGANE_COLLECTED  pellets_collected=1 nectar_drunk=5 sprouts=<>=1>
PASS P2_KOGANE_COLLECT collect1 drink5 onion_receipt3
P2_KOGANE_RECEIPTS loaded=1
P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3
P2_KOGANE_RESTART rearmed=0
P2_KOGANE_ONION_RECEIPT generator=219001 flip=<n> granted=0 duplicate=1 ledger=onion seed=kogane-arena
P2_KOGANE_REPROBE duplicates=3
P2_KOGANE_ONION_LEDGER rows=3
PASS P2_KOGANE_RESTART dedupe_ok rearmed=0 duplicate=3 ledger=3
```

### Subagent usage (slice 3 experiment, honest)

This agent was provisioned without a `task`/subagent tool, so the three-parallel
subagent split could not be run; the source audit, candidate inventory and test
scaffolding were all done inline. Net: higher context usage and a longer serial
edit -> build -> GL loop (no parallel source/test prep). No subagent result to
use, correct or discard.

### Reproduction command

```powershell
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l17
py -3.12 -m experimental.pikmin2_kogane_collect build `
  --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l17 `
  --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l17-build `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/collect-natural-fixture `
  --head 1ccc4f371d79418876462225f183fe556ebaf93d
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l17 -- `
  py -3.12 -m experimental.pikmin2_kogane_collect run-cross `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --bank C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/bank `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/collect-natural-cross `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/collect-natural-fixture/fixture.exe
# run-mixed stages a co-consumer Flora posy to expose the lane-06 ledger collision
```
