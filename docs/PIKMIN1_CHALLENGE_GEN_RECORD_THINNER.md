# Trial-arena .gen-record thinning tool (#795)

Fail-closed repo utility: parses staged retail generator (`.gen`) files,
identifies buried-sprout `GenObjectPiki` records, and emits a thinned arena
with the buried total below the field cap, with byte-level provenance.
Unknown layouts abort with exact offsets; nothing is guessed.

## Why

Retail chal4 buried sprouts are binary `GenObjectPiki` records
(`p1-challenge-trial-arena-thin-v2`, #792, BLOCKED on exactly this).
`GenObjectPiki::birth` with spawn state 0 births a `PikiHeadItem` and
`pikiheadItem.cpp:143` counts it into the birth cap; the staged chal4
arena carries 15 buried-piki generators totalling exactly 100 == the cap,
so the trial squad cannot birth (#770). This tool removes whole
buried-sprout generator records (largest first) until headroom fits the
squad; every kept record stays byte-identical.

## Format (cited)

- File: `GeneratorMgr::read` (native `src/plugPikiKando/generator.cpp:997`):
  ID32 version, 3x f32 navi, [v0.1: f32 direction], int32 BE count, records.
- Record: `Generator::read` (`generator.cpp:735`): ID32 name/version/id70,
  int32 carry, 32B memo, 3x f32 pos/offset, object/area/type sections.
- Section: `GenBase::read` (`generator.cpp:172`): ID32 version, class
  `doRead` bytes, `Parameters::read` entries (`parameters.cpp`: 3 ASCII ID
  bytes + 1 size byte, payload, `FFFFFFFF` terminator).
- IDs are 4 bytes stored reversed (`ID32::read`, `sysCommon/id32.cpp`);
  ints/floats are big-endian (`Stream::readInt`, `sysCommon/stream.cpp`).
- Object `doRead`: piki 0B, plnt 4B (`plantMgr.cpp:375`), pelt 4B
  (`genPellet.cpp`), item pascal string + 64B iff version != v0.0
  (`genItem.cpp:87`), teki 1B + 2B + ID32 + 5 ints + 5 floats (last
  `TekiPersonality::read` branch; proven by whole-file tiling), boss 4B
  (`genBoss.cpp:41/88`), work name/shape strings with v0.3 floats iff the
  engine name table resolves move stone (`workObject.cpp:37`).
- Areas `pint`/`circ` (12B + radius float for circ); types `1one`/`aton`/
  `irnd` (base `b00`/`b01` + count params).
- Contributions: `aton` maxCount, `1one` 1, `irnd` conservative max.

## Usage

- `py scripts/p1_challenge_gen_record_thinner.py assess --in chal4/default.gen`
- `py ... thin --in default.gen --out thin.gen --provenance prov.json
  [--cap 100] [--squad 20]`
- Exit 0 ok; exit 3 refusal with exact offset on stderr.

## Provenance packet

Input/output sha256 + sizes, record counts, buried before/after, and per
removed record: file offset, length, sha256, memo, `p00`, type,
contribution. Output is re-parsed before return and kept bytes verified.

## Limits

- Only the layouts above parse; anything else (new classes, versions,
  param sets, `irnd`-piki beyond conservative max) refuses — that is the
  contract, not a gap to work around in the tool.
- Tool only, never an engine unblock; consumer is
  `p1-challenge-trial-runtime-acceptance` (#567) thinned-arena birth proof.
- No native files, no engine edits, no runtime beyond self-tests, no ADMIT.
