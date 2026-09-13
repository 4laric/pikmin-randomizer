# Integrate 1feade3 onto the maintained P2 engine

Codex implementation owner through shared account 4laric; issue #402.
Requested source: `1feade3a5f76abf2046dfc2ba326de7dd5013310`, from
`kimi/p2-bulblax-import`. Target base: `9b374b5` on
`codex/pikmin2-room-preview`. Integrated cherry-pick: `f9ccbc8`.

## Scope and reconciliation

- Batch-2 sampled proxy display for Dweevil, flora, ground invertebrates,
  cannon and Waterwraith families; batch-3 sampled proxy display for aquatic,
  flying and Snagret families; static Long Legs bind-pose display.
- Setup, live/corpse draw and manager reset/reuse hooks for those displays.
  The target lacked the batch-2 and Long Legs modules referenced by the
  submitted delta. Their `.cpp`/`.h` files come from the same frozen commit.
- Initial opt-in Purple earthquake/stun path for registered Red Dwarf
  Bulborbs, the dedicated TAI state and lifecycle-preserving transition API.
- Initial White species identity, sampled model, Ivory conversion/plucking,
  selection, movement/attack/carry values, and native tutorial checkpoint v2.
  Imported native test/fixture sources accompany these changes.

The source parent also contained unrelated hard-lane, BombSarai and BigTreasure
registration. Those are not changes made by the requested commit and were not
pulled into CMake/setup through conflict context. Their separate submissions
remain separate integration candidates.

Conflicts retain the newer target behavior:

- Beasts floor 2/3/4 entry profiles, distinct 64-character token namespace,
  cargo-terminal/descent guards, and the current transfer writer.
- Giant Breadbug actor registration/draw, Queen/King reset and pointer-lifetime
  cleanup, campaign Snow binding, Mamuta interaction rules and Kurage receiver.
- Queen's recently merged diffuse/BTK specular layer is byte-unchanged.
- Existing Beasts fixture dispatch remains alongside new Purple/White fixtures.

Native tutorial `P2_CAVE_ENTRY_2` accepts White identity 4 on tutorial floors
1/2 with the existing 32-character token. It emits `P2_CAVE_TRANSFER_2`.
Version 1 and Beasts formats retain their old species limits; Beasts transfers
are not silently upgraded. This integration does not enable schema 2 in the
Python supervisor or add new seed/package options. It is a native opt-in
restoration interface awaiting its separate supervisor/staging rollout.

One review correction clears White identity when making a Pikmin Purple,
preventing simultaneous species flags. Other ordinary color resets already
clear both flags in the imported code.

## Validation

`tests/test_pikmin2_integration_402.py` compiles and executes the imported
Purple impact/White parameter policies and the production `tai.cpp` transition
regression. It also checks tutorial v1/v2 versus Beasts floor/token namespaces,
unknown versions and malformed tokens. Focused cave/Purple/integration tests:
24 passed, 4 local-asset skips, 25 subtests passed.

Combined `pytest tests -q -rs` with MinGW on PATH: **1391 passed, 23 skipped,
1052 subtests passed**. Skips require absent local asset outputs or Windows
symlink privileges. Log: private `output/integrate402-tests.log`.

Native candidate `e9ca54f8` builds using the current Windows production
configuration (`cmake --build build-timing --target pikmin_pc -j6`).
Executable SHA256:
`2378a15c1221673b32f4f5bbd8c38d3c57d764092e9d237b9446014e5dbb73e5`.
Private build log: `output/integrate402-build-final.log`. Existing compiler
warnings remain; no new build failure was suppressed.

Lane evidence on #393/#395 records actual Purple throw/quake/Fit, nonlethal
damage and lethal corpse behavior, and White Ivory conversion/plucking with
population conservation. Those are prior worker runs, not new combined
gameplay sign-off. This integration repeats the compiled contracts and current
production build; the Queen renderer regression is recorded below.

## Remaining boundaries

The batch display modules explicitly use P1 proxy actors and approximate host
animation phase; source P2 AI, hitboxes, drops and encounter mechanics are not
made complete by registration. Long Legs remains static bind-pose display.
Existing family death/corpse, movement and reload gates remain on their issues.
Purple direct-hit damage and White poison/gas/digging/storage are later lane
work, not part of this frozen submission. No player package, save, generated
model, retail asset or runtime state is committed or replaced.

### Combined renderer regression

The exact-build Queen fixture passed in a fresh private stage with ordinary
Red Pikmin and the new optional family/White/Purple-impact profiles absent.
It observed 242296 specular-contribution channels and 336312 animated channels,
with both diffuse and phase-zero replay pixel-identical. This retains #399's
controlled-light test boundary; it is not new imported-family visual acceptance.
Fixture SHA256:
`caf036f040f7830d8dc86edcad402dfff5bfa93fc4432302b17aa2aa9ea68299`.
Provenance: private `output/integrate402-fixture/provenance.json`.
Runtime evidence: private `output/integrate402-run/native.log` and captures.
