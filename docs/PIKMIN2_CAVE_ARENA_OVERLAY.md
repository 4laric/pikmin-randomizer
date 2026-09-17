# Legal single-pr05 cave arena overlay / p2-cargo input provider (#654)

Lane `runtime-fixtures-cave-arena-overlay-pr05`. Owner: Codex through shared
account `4laric`. Root-only tooling slice; no native build, no runtime run,
no ADMIT, no playability claim. Issue #654 stays OPEN.

## Observed abort (real source evidence, no invention)

The accepted guarded cave boot (#642) and consumer yakushima4 P1 (#161)
reach the 960x540 centred window, then the boot aborts at
`engine/pc_port/pc_p2_preview.cpp:128` (`P2 preview: duplicate treasure`).
The native predicate in `pc_p2_preview_setup` is exact:

- With no `p2-cargo.txt` and no `p2-cargo-free.txt`: the first live pellet
  whose config model id is `pr05` becomes the treasure; a SECOND one
  aborts. Cargo-free arenas must therefore carry zero pr05 rows (the
  beasts-floor2 convention enforced in
  `experimental/pikmin2_beasts_floor2.py`).
- With `p2-cargo.txt`: every live generated pr05 scaffold must bind
  exactly one spec row by native generator id
  (`P2 cargo duplicate/missing generator`, `actor count mismatch`,
  `unknown actor` aborts otherwise).

Real staged generic chal0 arena (l51 staging, read-only reference):
`assets/dataDir/stages/chal0/default.gen` sha256
`2f6fd4950392fa2d7707f664c390366afdad1e8cf8a4300d18be707b07228792`
carries 24 records with exactly ONE `preview treasure bolt` (model bytes
`50rp`, the little-endian `pr05` scaffold). The generic overlay path is
therefore legal; the duplicate arises when cave sidecar staging adds
further pr05 treasure scaffolds without a cargo binding.

## Provider contract

`experimental/pikmin2_cave_arena_overlay.py` (`P2_CAVE_ARENA_OVERLAY_1`):

- `decode_arena_gen`: real framing via shared
  `scripts.preview_pikmin2_room.records` (read-only reuse); reports every
  pr05 record as `{generator_id, label, position}` where generator_id is
  the LE u32 at offset 8 (roster/native convention).
- `decode_run_inputs`: cargo presence via shared
  `experimental.pikmin2_cargo.read_cargo` (read-only reuse);
  `p2-cargo-free.txt` must be exactly `P2_CARGO_FREE_1`; cargo+free
  conflict refused.
- `evaluate_boot_predicate`: mirrors the native abort table
  (`abort-duplicate-treasure`, `abort-duplicate-generator`,
  `abort-cargo-binding`, `legal-single-treasure`, `legal-cargo`,
  `legal-cargo-free`, `no-treasure`). Live-actor/generator count
  agreement stays runtime-checked by the boot fixture (recorded limit).
- `emit_single_pr05_overlay`: prunes to exactly one pr05 row
  (deterministic lowest generator id, or an explicit keep id), repacks the
  BE header count, and reparses the result.
- `emit_cargo_package`: renders strict `P2_CARGO_1` from caller-supplied
  specs (never invented) binding every arena pr05 generator exactly once,
  validated by the shared strict reader; returns the text plus a
  machine-readable `p2-cave-arena-overlay-1` package with hashes.
- `input_package`: verdict + pins for the guarded boot consumer.
- `guard_record`: hashes canonical `scripts/p2_fixture_captain_guard.h`
  read-only and fails closed on drift (pinned
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`).

Downstream consumers: #161, #154, #642. Shared checkpoint/generation/
treasure providers stay with their provider shards; no shared
overlay/arena/builder/guard/native file was edited.

## Evidence

- `tests/test_pikmin2_cave_arena_overlay.py`: 26 tests pass, including the
  focused duplicate-pr05 abort reproduction, malformed/missing-input and
  cargo-grammar boundaries, deterministic hash pins (overlay
  `ba0c8d81...b4cb42`, cargo `70653f6a...59ecd8f874`), and a real-arena
  grounding test against the staged sha above.
- Log: `output/workflow/autofill/planning-shards/provider-runtime-fixtures/prepared/cave-overlay-output/pytest.log`.
- Handoff: `.../cave-overlay-output/handoff.json` (tooling; all six
  runtime gates UNTESTED; fixture adoption N/A).
