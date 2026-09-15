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
