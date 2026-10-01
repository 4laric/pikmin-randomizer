# Overworld source locator provider (#646)

Dependency-free provider for the real overworld stage source. Unblocks the
stranded `p2-overworld-tutorial` P0 owner (#148).

## Contract

Module `experimental/pikmin2_overworld_source_locator.py`:

- `DEFAULT_ISO` = `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`
  (995557376 bytes, local legal US GPVE01 disc), overridable with `--iso`.
- `STAGES_PATH` = `user/Abe/stages.txt`, read through the existing shared
  `experimental.pikmin2_assets.disc_files` reader. No parser fork.
- Pinned bytes: 3275 bytes, sha256
  `4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8`
  (the same real-source pin the done Awakening Wood / Wistful Wild P0 lanes used).
- `locate_and_decode()` returns `SourceBundle(iso, size, sha256, data, text)`.

## Fail-closed behavior

- Disc absent -> `SourceMissing` (CLI exit 2) with an actionable message
  (default path or `--iso`). Never substitutes synthetic/P1 content.
- Member absent -> `SourceMissing`.
- Hash mismatch -> `HashMismatch` (CLI exit 3); unpinned bytes are refused.

## Evidence

- Focused tests `tests/test_pikmin2_overworld_source_locator.py`:
  real-disc positive (size/hash/text), absent-disc, missing-member and
  hash-mismatch negatives, decode round-trip, CLI pin report.
- Downstream consumer: `p2-overworld-tutorial` (#148) P0 owner consumes the
  verified `SourceBundle` to finish the P0 decode. This provider does not
  edit that lane's owned files. No ADMIT, no build/runtime, no manifest write.
