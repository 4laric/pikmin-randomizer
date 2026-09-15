# BigTreasure elemental damage receiver (#246)

Lane 32 of the P2 implementation fan-out `PIKMIN2_IMPLEMENTATION_FANOUT.md`
(coordination #186, tracking #454). Child issue
[#246](https://github.com/4laric/pikmin-randomizer/issues/246), parent
[#175](https://github.com/4laric/pikmin-randomizer/issues/175).

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: DeepSeek (deepseek-v4-pro), 2026-09-14. This slice starts from
the prior lane work in `PIKMIN2_BIGTREASURE_ORDINARY.md`.

Prior slices: [source audit](PIKMIN2_BIGTREASURE_AUDIT.md),
[ownership/teardown contract](PIKMIN2_BIGTREASURE_CONTRACT.md),
[per-element attacks](PIKMIN2_BIGTREASURE_ATTACKS.md),
[host seam](PIKMIN2_BIGTREASURE_SEAM.md),
[conversion](PIKMIN2_BIGTREASURE_CONVERSION.md),
[FSM host](PIKMIN2_BIGTREASURE_FSMHOST.md),
[ordinary FSM drive](PIKMIN2_BIGTREASURE_ORDINARY.md).

## What this slice changes

The ordinary slice left the element runtime **detection-only** (`queryHit`
reported intersections; "the Pikmin damage receiver stays lane 10"). This
slice closes that gap: an emitted fire/gas/water/elec node now applies the
source stimulus to a live Piki/Navi through the already-ported shared P2
receivers (`InteractFire` / `InteractGas` / `InteractBubble` / `InteractDenki`
in `interactBattle.cpp` / `navi.cpp`, lanes 10/11).

New lane-owned native files:

- `pc_port/pc_p2_bigtreasure_receiver.h/.cpp` — engine-free stimulus resolve.
  `p2_bigtreasure_receiver_resolve(weapon, origin, attackDamage, target)` maps a
  confirmed hit to the source stimulus, damage and (elec) zap direction. Source
  anchors (US GPVE01 rev 0, `BigTreasureAttack.cpp`): fire `InteractFire`
  (attackDamage) `:118`; gas `InteractGas` (attackDamage) `:220`; water
  `InteractBubble(0.0)` `:315`; elec `InteractDenki` (attackDamage, zapDir)
  `:470`. `attackDamage` is `CG_GENERALPARMS(mOwner).mAttackDamage`
  (`EnemyParmsBase.h` 'fp24', header default 10.0f).
- `pc_port/pc_p2_bigtreasure_receiver_host.h` — engine-facing apply, shared by
  the ordinary loop and the runtime fixture. `pc_p2_bigtreasure_stimulate_piki`
  / `_navi` construct the matching `Interact` with a `nullptr` owner (the four
  receivers never read `mOwner`; the boss has no real P1 creature actor) and
  `stimulate` the target. Navi fallback mirrors the source non-flick branch
  (`InteractAttack` zero damage) chosen deterministically; the source 50/50
  flick/attack roll stays with the host `randWeightFloat` input.
- `tools/p2_bigtreasure_receiver_test.cpp` (4 groups, engine-free).

Wired seam (additive) in `pc_port/pc_p2_hardlanes.cpp`:

- The ordinary update, when the running element has in-flight nodes, resolves
  and applies the source stimulus to every live Navi/Piki whose position
  intersects the element geometry. The old `P2_BIGTREASURE_ATTACK_HIT`
  detection-only block is replaced by a real application that logs
  `P2_BIGTREASURE_RECV weapon=<e> target=piki species=<n> accepted=<0|1>`.
- `CMakeLists.txt`: one additive TU in the game target and the receiver test.

## Evidence (this pass)

- **Standalone receiver test** (engine-free, `-std=c++17 -Wall -Wextra -Werror`):
  `PASS BIGTREASURE_RECEIVER` (4/4): stimulus map, damage magnitude (water 0),
  elec direction magnitude, none/name. Executable SHA-256
  `1799c74d1009c070549856f639dc92ae5688158a398c94e122e2b08749b6bc07`.
- **Root tests**: `tests/test_pikmin2_bigtreasure_receiver.py` — 4 passed
  (compile-and-run plus three source-anchor checks: ordinary update applies the
  receiver, host emits the shared P2 stimuli, resolve maps all four weapons).
- **Production build** (`pikmin_pc`, JAudio ON, Optimize OFF, Release):
  `[58/58] Linking CXX executable bin\nectar.exe` exit 0; `ninja -n` =
  `ninja: no work to do.`; `nectar.exe` SHA-256
  `8ae19153aabe9e71bd824d688e7dccc65d12474d6f7df4d60f8ed05bc08cbd98`.
- **Link check**: `nm -C nectar.exe` shows `T InteractFire::actPiki`,
  `T InteractGas::actPiki`, `T InteractBubble::actPiki`,
  `T InteractDenki::actPiki` and the lane entry points; `strings` retains the
  `P2_BIGTREASURE_RECV` literals. The four receivers are now referenced by a
  real emitter, satisfying the LTO retention note in
  `PIKMIN2_RECEIVER_PATHS.md` §7.

## Gates

| Gate | Result |
|---|---|
| 1 Exact identity/spawn | UNTESTED this slice (unchanged: fixed-placement visual bank; no ordinary spawn binding yet) |
| 2 Autonomous movement/animation | PASS (unchanged; 12-state FSM keyframe drive from the prior slice) |
| 3 Attacks and receivers | receiver decision + wiring PASS (unit test + production link); natural real-Piki state change UNTESTED in a fresh real-GL run (see blocker) |
| 4 Death and corpse | UNTESTED (unchanged) |
| 5 Actual transport and reward | source-backed N/A this slice |
| 6 Cleanup and re-entry | source-backed N/A this slice |

## Remaining gaps / blocker

The receiver decision and the ordinary-loop application are implemented and
built, but a natural emitter -> real receiver -> Piki state-change observation
was not reproduced this pass because the shared `pikmin2-room105` converted-room
inputs and the `bigtreasure-{host,visual}`-stage assets are absent from
`C:/Users/alari/pikmin-randomizer/output/` (regenerated by the prior lane
worker's private output). A fresh real-GL fixture run needs those staged inputs
plus the fixture build (`scripts/build_pikmin2_fixture.py`). A live real-GL run
with a Pikmin inside the running element's geometry is the honest remaining gate
for "real elemental damage" acceptance.
