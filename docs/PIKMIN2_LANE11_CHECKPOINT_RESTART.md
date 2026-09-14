# Lane 11: cave checkpoint schema-3 (Bulbmin) restart path

Lane 11 (species/Bulbmin) of [PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md),
parent [#131](https://github.com/4laric/pikmin-randomizer/issues/131); checkpoint
tracking [#112]. Implementation owner: Codex through shared `4laric`; executing
agent `opencode-go/deepseek-v4.1-flash`.

This closes the lane-11 acceptance clause "selected species survives actual
routing **and restart**" for the versioned checkpoint: the cave transfer wire
format is now an explicit, gated round trip (schema 3 carries Bulbmin), and a
real process restores a Bulbmin from a schema-3 checkpoint on disk.

## Wire format

`pc_port/pc_p2_cave_transfer.h` extracts the exact encode/decode the engine used
inline in `pc_p2_cave.cpp`:

```text
P2_CAVE_ENTRY_<schema> <32-hex token> <floor> <health> <count>
<species> <maturity>          (count lines)
P2_CAVE_TRANSFER_<schema> <32-hex token> <floor> <health> <count>
<species> <maturity>          (count lines)
```

- Schema 1 = Blue/Red/Yellow/Purple, 2 = +White, 3 = +Bulbmin (matches
  [PIKMIN2_SPECIES_CAPABILITY_MATRIX.md](PIKMIN2_SPECIES_CAPABILITY_MATRIX.md)).
- The transfer schema is bumped to the newest surviving species and never
  downgraded, so a Bulbmin is never written where an old reader would silently
  reinterpret the color id.
- Old readers reject a newer species as a `Pikmin` clause (not a header error),
  reject unknown versions as `header`, and reject bad token/floor/health/
  maturity/trailing data.

`pc_p2_cave.cpp` now parses entries and formats transfers through this header;
behavior is unchanged. Gate `tools/test_p2_cave_transfer.cpp` ->
`PASS P2_CAVE_TRANSFER` (engine-free).

## Campaign serializer

The cave/campaign supervisor `experimental/pikmin2_campaign.py` now knows
White/Bulbmin: `SPECIES`/`SPECIES_SCHEMA`, a schema-aware `entry_text`
(`P2_CAVE_ENTRY_3` when the squad carries Bulbmin), and a `transfer_schema`
parser that rejects a `P2_CAVE_TRANSFER_2` payload carrying Bulbmin
("Cave transfer schema too old for species"). Regression tests:
`tests/test_pikmin2_campaign_bulbmin.py` and `tests/test_pikmin2_cave_transfer.py`.

## Live process restore

A prepared Emergence floor-2 run (`output/p2-lanes1011-restore-01`, reused from
a prior campaign session) was given a schema-3 entry with a mixed squad
(red/yellow/purple/**Bulbmin**) and launched with the private native build at
960x540. Native `nectar.exe` SHA-256
`6DCCD28D0F82A68021E08FB7EDF6B68023237502ACEC07A54F4029B9871E0B81`.

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered
P2_CAVE_RESTORE species=1 maturity=0      (x16)
P2_CAVE_RESTORE species=2 maturity=1
P2_CAVE_RESTORE species=3 maturity=2
P2_CAVE_RESTORE species=5 maturity=0      <-- Bulbmin restored
P2_CAVE_READY floor=2 survivors=19 health=0.625
```

Log: `output/p2-lanes1011-restore-01/native-restore.log`. No `Invalid P2 cave
entry` abort and no extinction.

## Provenance and remaining

- Native `opencode/p2-lanes1011-elecbug` @ `416ccb49` (patches
  `native-candidates/p2-lanes1011-elecbug/0001..0005`).
- Root doc and tests on `opencode/p2-lanes1011-root`.
- The **write** half is proven by the gated wire encoder (the engine's own
  function) and the campaign serializer tests. A fully automated live
  **two-process** run (write in process 1, restore in process 2) needs the
  lifecycle fixture/campaign to drive the F6 boundary; the fixture source is not
  retained in the repo, and input injection is not automated. That is the named
  remaining dependency for a supervisor-driven end-to-end restart.
