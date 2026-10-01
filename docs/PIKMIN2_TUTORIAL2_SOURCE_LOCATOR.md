# tutorial_2 source locator provider (#152)

Dependency-free provider for the real tutorial_2 cave source. Unblocks the
tutorial_2 P1 owner: P0 blocker (1) (retail `tutorial_2.txt` absent at P0 time)
is now resolvable; `light_a` cargo stays unresolved (P0 blocker 2, still open).

## Contract

Module `experimental/pikmin2_tutorial2_source_locator.py`:

- `DEFAULT_ISO` = `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`
  (995557376 bytes, local legal US GPVE01 disc), overridable with `--iso`.
- `user/Mukki/mapunits/caveinfo/tutorial_2.txt`, read through the existing shared
  `experimental.pikmin2_assets.disc_files` reader. No parser fork.
- Pinned bytes: offset 770662632, 10222 bytes, sha256
  `05a38ab1e37c4ad11b5f48425bec3c2101ff199a4ea0b926fc9f35fde5620049`.
- Codec is shift_jis, recorded explicitly: strict UTF-8 decoding of the retail
  bytes fails (byte 0x8a); shift_jis decodes 9491 chars incl. the `# CaveInfo`
  and floor records.
- `locate_and_decode()` returns `SourceBundle(iso, offset, size, sha256, data, text)`.

## Fail-closed behavior

- Disc absent -> `SourceMissing` (CLI exit 2) with an actionable message
  (default path or `--iso`). Never substitutes synthetic/P1 content.
- Member absent -> `SourceMissing`; layout drift or hash mismatch ->
  `HashMismatch` (CLI exit 3); unpinned bytes are refused.

## Evidence

- Focused tests `tests/test_pikmin2_tutorial2_source_locator.py`:
  real-disc positive (offset/size/hash/text), not-plain-UTF-8 codec record,
  absent-disc, missing-member and hash-mismatch negatives, decode stability,
  CLI pin report.
- Downstream consumer: tutorial_2 P1 (`p2-cave-tutorial_2`). No ADMIT, no
  build/runtime, no manifest write.