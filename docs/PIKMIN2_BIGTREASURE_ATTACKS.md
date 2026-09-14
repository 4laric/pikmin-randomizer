# Pikmin 2 BigTreasure (Titan Dweevil) per-element attack policies — issue #246

Implementation owner: Codex using shared account 4laric. Parent: #175;
integration contract: #186; roadmap tier 8: #197. Builds on the source audit
([PIKMIN2_BIGTREASURE_AUDIT.md](PIKMIN2_BIGTREASURE_AUDIT.md)) and the weapon
ownership/teardown contract
([PIKMIN2_BIGTREASURE_CONTRACT.md](PIKMIN2_BIGTREASURE_CONTRACT.md)). Isolated
policy milestone on the #169 Groink pattern: no actor, map, damage-receiver,
sound or effect dependency; 30 Hz source ticks; deterministic host-supplied
randomness. Source semantics reference US GPVE01 rev 0 at research revision
`632af93787b9c95b63f0c13be32b161375ce3a96` (BTA =
`src/plugProjectNishimuraU/BigTreasureAttack.cpp`, BTC = `BigTreasure.cpp`).

## Module and host adapter interface

New lane-owned native files: `pc_port/pc_p2_bigtreasure_attacks.h/.cpp` and
`tools/p2_bigtreasure_attacks_test.cpp`. They compose with the existing
ownership/pool module (`pc_port/pc_p2_bigtreasure.h/.cpp`) and add no shared
hooks; Groink lane files are untouched.

The lane-owned adapter interface (`pc_p2_bigtreasure_attacks.h`) follows the
Groink `P2GroinkTraceFn` shape:

- `P2BigTreasureTraceFn` — sphere trace for elec bounce nodes (radius 20,
  source bounce coefficient, trace-mutated velocity, floor/wall flags plus a
  `getMinY`-equivalent ground height).
- `P2BigTreasureGroundFn` — ground height query for water bubble impact.

A future host integration implements both against the P1 map (with the
documented `center.y - radius` / `+ radius` MoveTrace convention from the
Groink prototype); fixtures use a mock flat-floor/wall world.

## Per-element policies

- **Fire (Flare Cannon)** — `P2BigTreasureFirePolicy`, 8 nodes. Ratio grows
  3/s; extent `scale × 200`, radius 25, Y gate `40 × scale`; one node
  immediately on start, then every 0.1 s; nodes self-recycle at full extent
  including after `finish()` (BTA `:85-139`, `:1203-1268`). Directional
  pre-attack triplet (F/FL/FB/FR) from the wrapped target-relative angle
  quadrants (BTC `:1116-1146`). Scale 1.0 normal / 1.25 damaged.
- **Gas (Comedy Bomb)** — `P2BigTreasureGasPolicy`, 200 nodes. Ratio grows
  0.27/s to extent 480; radius 10, switching to 15 past half extent; Y gate
  30; one arm set immediately, then every 0.1 s; arm angles rotate per
  source update (not per second), reverse on the reversal timer, and freeze
  while bittered (BTA `:189-244`, `:1315-1467`). Normal: 3 arms, 0.015
  rad/update, 30 s reversal. Damaged: 4 arms, 0.02 rad/update, 30 s or 2 s
  reversal by host 50/50 input.
- **Water (Monster Pump)** — `P2BigTreasureWaterPolicy`, 16 nodes. Source
  shot velocity (`vertSpeed = 350/dt/20`, horizontal from halved jittered
  2D distance, BTA `:1802-1849`); `velocity.y -= 20` per source update;
  ground impact via the adapter ends the node with a ground hit; radius 20
  in flight / 30 on impact (BTA `:283-337`). Shot interval 0.5 s normal /
  0.25 s damaged. Bubbles persist across `finish()` (source gap 2) and are
  force-recycled by `defeat()` (lane teardown).
- **Elec (Shock Therapist)** — `P2BigTreasureElecPolicy`, 17 nodes. Anchor
  node invisible, tracking `otakara_elec_eff`; up to `maxDischarge` visible
  bouncing spheres traced through the adapter with the set's bounce factor,
  floor friction on x/z, `velocity.y -= 20` per update, first-floor-contact
  bounce events (BTA `:404-494`, `:2327-2385`). After the scatter delay,
  nodes chain pairwise one link per chain interval; chain-segment hit
  geometry is the source 10 × 20 cross-section with `0 < dotSep < dist`
  (BTA `:436-491`, `:2712-2782`). `finish()` recycles every node with break
  effects. Pool invariant `1 + maxDischarge ≤ 17` enforced in `start()`.
- **Director** — `P2BigTreasureAttackDirector` integrates the
  4 + 2 × liveWeapons pacing limiter with the health-weighted pick and the
  started flags (one attack at a time), plus bitter force-finish and defeat
  teardown across all pools.

Normal vs damaged parameter selection uses the strict `>` 3000 HP boundary
everywhere: exactly 3000 already selects the damaged set.

## Per-element acceptance evidence

Fixtures in `tools/p2_bigtreasure_attacks_test.cpp`, compiled with local
MinGW g++ 16.2.0:

```powershell
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_attacks_test.cpp pc_port/pc_p2_bigtreasure_attacks.cpp pc_port/pc_p2_bigtreasure.cpp -o <private-output>/p2_bigtreasure_attacks_test.exe
```

Result: warning-clean; all five fixture groups pass
(`p2_bigtreasure_attacks_test: all fixtures passed`, exit 0). The earlier
ownership fixtures still pass (`p2_bigtreasure_test`, exit 0).

- **Fire:** parameter boundary at 3000 (1.0/1.25); all four direction
  quadrants including the π/4 boundary and negative-angle wrap; immediate
  node + 0.1 s cadence; self-recycle at full extent; in-flight drain after
  finish; extent/radius/Y-gate hit geometry at normal and damaged scales.
- **Gas:** normal (3 arms/0.015/30 s) and damaged (4 arms/0.02/30 s or 2 s)
  sets; exact-3000 boundary selects damaged; initial arm spacing TAU/3;
  per-update rotation and wrap; reversal flip after 30 s; bitter freeze;
  arm-set cadence; radius 10 → 15 past half extent; Y gate; 200-node
  exhaustion.
- **Water:** source velocity values (vy 525, vz 114.2857 for a 200-unit
  shot at 30 Hz); ballistic arc with per-update gravity; adapter floor
  impact producing exactly one ground hit and recycle; 20/30 radius switch;
  interval cadence 2 shots/s normal vs 4 shots/s damaged (strict `>` puts
  the first shot on tick 16/9); persistence across finish; defeat teardown;
  16-shot exhaustion.
- **Elec:** four discharge sets across the 3000 boundary (10/12/8/14 nodes,
  scatter 2.7/4.5/0.5/0.2 s); anchor invisibility and joint tracking;
  radius-20 adapter trace with the set's bounce factor; floor bounce with
  0.65 friction and first-contact event; wall bounce through the mock
  adapter; scatter delay gating (no chains at 0.467 s against a 0.5 s
  scatter, chains after); pairwise chain hit geometry (10/20 cross-section,
  segment bounds); `1 + maxDischarge ≤ 17` acceptance/refusal; finish
  recycling.
- **Director:** pacing gate blocks attacks below the 12 s four-weapon
  threshold; first allowed entry starts the elec band; started flags block
  re-entry; bitter force-finish; empty-ownership no-pick; defeat clears all
  pools.

## Design decisions

- Element policies own node geometry/motion; the pre-existing
  `P2BigTreasureAttackPools` remains the lifetime ledger (started flags,
  in-flight counts, finish/defeat semantics). No duplication of ownership.
- Randomness (start angles, jitter, 50/50 parameter picks, trace input) is
  always a host-supplied value; the module never calls a RNG, keeping
  fixtures deterministic and replayable.
- Gas rotation and both gravities are per-source-update quantities (as in
  source), while emit ratios and timers use seconds with `sys->mDeltaTime`;
  the policies preserve that split exactly.
- Chain placement is modeled as one link per chain interval after the
  scatter delay; source places a growing window per `startNewElecList`
  call. Both reach full chaining within `maxDischarge` intervals; the
  per-interval cadence and pairwise-link structure are the contract, not
  the exact links-per-call count (noted for runtime acceptance).

## Deferred and open items

- Per-element runtime acceptance against the real P1 map trace (the mock
  adapter proves the interface, not map parity) — future arena slice under
  #186, fixed placement first per the boss staged-phases gate.
- Damage receivers (InteractFire/Gas/Bubble/Denki application to Pikmin/
  Navi) are host concerns; hit geometry is validated here.
- Source places elec chain links in a growing window per interval; runtime
  acceptance should compare exact chain timing against retail captures.
- Converter handoff (models/motions, weapon models) remains gated on #128;
  pellet configs and `mPelletDropCode` finale treasure are still disc-data
  unknowns from the audit.
