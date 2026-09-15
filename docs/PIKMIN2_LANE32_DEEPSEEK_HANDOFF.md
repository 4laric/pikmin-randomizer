# Lane 32 Titan Dweevil — DeepSeek handoff (natural elemental damage receiver)

Tracking: [#246](https://github.com/4laric/pikmin-randomizer/issues/246), parent
[#175](https://github.com/4laric/pikmin-randomizer/issues/175). Implementation
owner: Codex via shared account `4laric`; executing agent/session: DeepSeek
(deepseek-v4-pro), 2026-09-14.

## Source ID and slice

Concrete source enemy ID: **73 BigTreasure (Titan Dweevil)**. One missing
end-to-end slice from the lane ledger ("actual elemental damage receiver …
remain"): connect the already-running per-element emission (fire/gas/water/elec)
to the shared P2 Pikmin receivers so a live target actually takes the source
state transition, instead of the prior detection-only `queryHit` log.

## Ordered commits

Root branch `deepseek/p2-l32`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`:

- (native side has its own repo; see below)

Native branch `deepseek/p2-l32-native`, base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`:

- `1a5975f881028bb6b7112cf048b3d631b49b4572` `lane32: wire BigTreasure elemental
  receiver into ordinary update (#246)` — dirty state: **none** (clean).

Root commit (uncommitted at time of this handoff; commit message
`lane32: BigTreasure elemental receiver tests + docs (#246)`):

- `tests/test_pikmin2_bigtreasure_receiver.py`
- `docs/PIKMIN2_BIGTREASURE_RECEIVER.md`
- `docs/PIKMIN2_LANE32_DEEPSEEK_HANDOFF.md`

## Owned files / hooks touched

Native (all additive or narrow-additive):

- `pc_port/pc_p2_bigtreasure_receiver.{h,cpp}` (new, engine-free stimulus resolve)
- `pc_port/pc_p2_bigtreasure_receiver_host.h` (new, engine-facing apply shared by
  the ordinary loop and the runtime fixture)
- `tools/p2_bigtreasure_receiver_test.cpp` (new)
- `pc_port/pc_p2_hardlanes.cpp` (additive: replace detection-only block with a
  live receiver application; remove `sBigTreasureHitLogged`)
- `CMakeLists.txt` (additive: one game TU + one test target)

No shared-semantics file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`) was
changed; the shared P2 receivers are the existing lane-10/11 implementations, now
referenced by a real emitter.

## Why: receiver contract

The four element receivers are already ported (lane 10/11; `interactBattle.cpp`
`InteractFire/InteractDenki/InteractGas`, `navi.cpp` `InteractDenki::actNavi`) and
route through the lane-11 `p2_species_immune` capability matrix. The lane-32
module only resolves the source stimulus (which element -> which `Interact`,
magnitude, elec direction) and the ordinary loop applies it. No second damage
framework is introduced.

## Build evidence (output/dsw/l32-build-evidence.txt)

```text
lane=l32 target=pikmin_pc native=1a5975f881028bb6b7112cf048b3d631b49b4572 dirty=no
  exe=.../native-l32-build/bin/nectar.exe
  sha256=8ae19153aabe9e71bd824d688e7dccc65d12474d6f7df4d60f8ed05bc08cbd98
  ninja_n="ninja: no work to do."
lane=l32 target=p2_bigtreasure_receiver_test native=1a5975f8... dirty=no
  p2_bigtreasure_receiver_test.exe sha256=1799c74d1009c070549856f639dc92ae5688158a398c94e122e2b08749b6bc07
```

`nm -C nectar.exe` shows `T Interact{Fire,Gas,Bubble,Denki}::actPiki` and the lane
entry points; `strings` retains `P2_BIGTREASURE_RECV` literals.

## Fixture adoption

- Overlay source: root `scripts/preview_pikmin2_room.py` `overlay()` →
  `ensure_pikmin_squad()` (verified present in this worktree).
- Native window default: `pc_port/pc_main.cpp` 960x540 + `pc_window_center()`
  (present; the runtime fixture also sets 960x540 + centered explicitly).
- Fresh arena / runtime evidence this pass: **NOT reproduced** — the shared
  `pikmin2-room105` converted-room inputs and `bigtreasure-{host,visual}`-stage
  assets are absent from `C:/Users/alari/pikmin-randomizer/output/` (prior
  worker's private output). I did not stage a new real-GL run, so no centred
  960x540 window or live-squad acceptance is claimed for THIS pass; the prior
  lane slice (ORDINARY doc) already recorded centred startup + 20-red squad on
  this source line.

## Six-gate table

| Gate | Result | Natural vs injected |
|---|---|---|
| 1 Exact identity and spawn | UNTESTED | fixed-placement visual bank; no ordinary spawn binding yet (unchanged) |
| 2 Autonomous movement / animation | PASS (prior slice) | natural keyframe FSM drive |
| 3 Attacks and receivers | decision+wiring PASS (unit + link); live Piki state change UNTESTED | **injected/unit** for the decision; natural application compiled but not observed in a fresh GL run |
| 4 Death and corpse | UNTESTED | — |
| 5 Actual transport and reward | source-backed N/A | this slice does not touch reward ownership |
| 6 Cleanup and re-entry | source-backed N/A | this slice does not touch lifetime |

## Tests run

- Native standalone: `p2_bigtreasure_receiver_test.exe` → `PASS BIGTREASURE_RECEIVER` (4/4).
- Root: `py -3.12 -m pytest tests/test_pikmin2_bigtreasure_receiver.py -q` → 4 passed.

## Assumptions

- Boss elemental `attackDamage` is the `EnemyParmsBase.h` 'fp24' header default
  `10.0f` until the disc general-parameter table is wired; the port receivers are
  magnitude-insensitive for Pikmin state transitions (only Navi health uses it).
- `InteractGas` has no `actNavi`, so gas is a no-op on captains (matches the port
  receiver interface); the source 50/50 Navi flick/attack fallback is chosen
  deterministically (attack) and left for the host `randWeightFloat` input.
- The elec zap direction is the source-shaped `150/mag y=150` horizontal vector;
  the port receivers do not consume it.
- A `nullptr` interaction owner is safe: none of the four elemental receivers
  dereference `mOwner`, and the boss has no real P1 creature actor.

## Remaining blockers

- **Lane 07/09 + a reserved real-GL slot**: a fresh room105 + BigTreasure visual
  stage to run the natural emitter -> receiver -> live-Piki-state-change
  acceptance (blocking provider: integration/lane 01 or 33 for the combined
  build, plus the converted-room inputs that were regenerated previously).
- Deterministic hit placement: the fixed boss at `(0,0,0)` did not reach the
  squad in the prior live run; a fixture that relocates a live Pikmin into the
  running element geometry (fire/gas/water/elec) is needed for the natural gate.

## Reproduction

```powershell
$env:PYTHONUTF8='1'
export PATH="/c/msys64/mingw64/bin:$PATH"
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l32 --target p2_bigtreasure_receiver_test
C:/Users/alari/pikmin-randomizer/output/dsw/native-l32-build/p2_bigtreasure_receiver_test.exe
```
