# Damagumo family staging provider (#638)

Lane `damagumo-family-staging-provider`, generation 2. Owner: Codex through
shared account `4laric`. Parent: blocked
`shard-enemies-3-damagumo56-observer` (#173/#312). This is the concrete family
staging prerequisite named by that lane's `staging-gap-gen4.md`: source 56
(Damagumo, Beady Long Legs) can now be staged, bound and resolved to its own
source parameters. No synthetic alias to Houdai, no fake gate PASS, no ADMIT,
no ledger writes.

## Source truth consumed (read-only)

- `P2LongLegsSpecies::Damagumo = 56` and `p2LongLegsParmsFor(Damagumo)` (speed
  100, deathChildren 25 ShijimiChou, no shotgun) already modelled the species;
  only the host binding and staging refused it.
- The Damagumo disc model lives in the demon lane's `Demon` folder
  (`enemy/data/Demon/model.szs`); the batch-1 `long-legs-family.json` carries
  only 66/69 by ownership. This provider consumes an explicit demon-lane 56
  profile and mesh, never a relabelled Houdai/BigFoot asset.

## What changed (owned files only)

- `native/pc_port/pc_p2_long_legs.cpp`: `SPECIES[]` gains
  `{"Damagumo", "longlegs_Damagumo_bind_00.mod"}`; `speciesEnum()` gains an
  explicit `"Damagumo"` arm so a staged Damagumo resolves to
  `P2LongLegsSpecies::Damagumo` (and its disc parms) instead of falling
  through to Houdai. `findSpecies()`/`parseActors()`/`setup()` pick the row
  up with no other change; Houdai and BigFoot paths are untouched.
- `experimental/pikmin2_long_legs_install.py`: `SPECIES`/`FOLDERS`/`ANCHORS`
  accept `Damagumo` (56, folder `Demon`, anchors landing/wait/flick). The
  base `long-legs-family.json` contract for 66/69 is byte-identical when no
  Damagumo actor is staged. A staged Damagumo requires the demon-lane
  `damagumo-family.json` (exact single 56 row, matching id/name/folder/mesh
  hash) plus `Demon/enemy.bmd` with a matching SHA-256; a missing or
  mismatched source is refused, an unused Damagumo mesh is refused, and a
  staged Damagumo without the source is refused. Profile/bank/actor configs
  gain explicit Damagumo rows; the staged mesh is `Damagumo_enemy.bmd`.
- `experimental/pikmin2_long_legs_arena.py`: arena gains the Damagumo slot
  generator `312004` at (-240, 30, 1850) on the neutral Chappy placement
  vehicle. Houdai (312001), BigFoot (312002) and the P1 Chappy control
  (312003) are unchanged.
- `tests/test_pikmin2_long_legs_install.py`: 25 tests (17 preserved/updated +
  8 Damagumo contract tests: source-profile required, mesh required and
  hash-gated, unused mesh refused, missing anchor refused, roundtrip with
  explicit Damagumo rows, never-aliased, base-only install unchanged, arena
  slot present). All pass.
- This file.

## Pins

- Root base `ecf5f53a601a3c563bb44339ec7abf4665795451`, head
  `360cfdf3938201a38c087cb60cd079f38c7af655` (installer/arena/tests).
- Native base `ce89a039f3d37e2f6c551b7dbb32e0864115a56c`, head
  `f01815106d7b2b96edb3da7108237257f295911e` (host binding).

## Observer wake criteria (for shard-enemies-3-damagumo56-observer)

1. Demon lane produces the 56 profile (`damagumo-family.json`) and
   `Demon/enemy.bmd`, with owner review.
2. Family visual converter accepts `Damagumo_enemy.bmd` and emits
   `longlegs_Damagumo_bind_00.mod` (family-owned step, outside this lane).
3. Arena stages slot `312004 Damagumo`; the bound actor emits
   `P2_LONG_LEGS_BIND ... species=Damagumo` and the source STATE/WALK/DEAD
   markers with Damagumo disc timings.
4. The instrumented Damagumo room app drives a natural run; the observer
   correlates its markers. Runtime gates remain unproven until then.

## Checks

- `py -3.12 -m pytest tests/test_pikmin2_long_legs_install.py -q` -> 25 passed.
- Private leased build (configure + `pikmin_pc` + `ninja -n` dry run) with
  executable hash recorded in the lane handoff; no runtime claim.
