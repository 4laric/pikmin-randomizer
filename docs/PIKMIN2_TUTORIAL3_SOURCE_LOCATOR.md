# tutorial_3 source locator provider (#153)

Dependency-free provider for the real tutorial_3 cave source. Unblocks the
tutorial_3 P1 owner: the P0 blocker recorded by the done `p2-cave-tutorial_3`
lane ("actual definition bytes unavailable - exact retail-ISO prerequisite
recorded") is now resolvable against the verified local legal disc.

## Contract

Module `experimental/pikmin2_tutorial3_source_locator.py`:

- `DEFAULT_ISO` = `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`
  (local legal US GPVE01 disc), overridable with `--iso`.
- `user/Mukki/mapunits/caveinfo/tutorial_3.txt`, read through the existing shared
  `experimental.pikmin2_assets.disc_files` reader. No parser fork.
- Pinned bytes: offset 770672856, 9701 bytes, sha256
  `adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb`
  (verified this turn against the disc).
- Codec is shift_jis, recorded explicitly: strict UTF-8 decoding of the retail
  bytes fails at byte 0x1e; shift_jis decodes 9051 chars including the
  `# CaveInfo` header, the `8 # FloorInfo` count line and the per-floor
  `# FloorInfo` / `# TekiInfo` / `# ItemInfo` / `# GateInfo` / `# CapInfo`
  blocks.
- `locate_and_decode()` returns `SourceBundle(iso, offset, size, sha256, data, text)`.
- `floor_units(text)` returns one `FloorUnit(floor, rooms, unit, light)` per
  `# FloorInfo` block in file order (8 blocks: default floor 0 plus floors
  1..7), carrying f000 floor index, f005 room count, f008 unit file and f009
  light ini. Read-only; nothing guessed.

## Fail-closed behavior

- Disc absent -> `SourceMissing` (CLI exit 2) with an actionable message
  (default path or `--iso`). Never substitutes synthetic/P1 content.
- Member absent -> `SourceMissing`; layout drift or hash mismatch ->
  `HashMismatch` (CLI exit 3); unpinned bytes are refused.

## Downstream consumer contract

Consumer: tutorial_3 P1 owner (`p2-cave-tutorial_3`, issue #153). It receives
the exact hash-pinned bytes plus decoded text and the per-floor unit/room
structure; it must not substitute synthetic content when the pin fails.

## Evidence

- Focused tests `tests/test_pikmin2_tutorial3_source_locator.py`: real-disc
  positive (offset/size/hash/text), 8-block floor/unit structure, not-plain-UTF-8
  codec record, absent-disc, missing-member, hash-mismatch and layout-drift
  negatives, decode stability, CLI pin report and decoded-text output.
- No ADMIT, no build/runtime, no manifest write. All six arena gates UNTESTED.
- Captain safety (#632) is not exercised here (tooling-only, no runtime run):
  the downstream runtime slice must adopt `scripts/p2_fixture_captain_guard.h`
  sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`.
