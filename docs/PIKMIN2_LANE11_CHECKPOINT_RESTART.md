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

## Automated two-process restart

`experimental/pikmin2_cave_restart_runtime.py` builds a private replacement-main
fixture (`cc4a8acd...`) that drives the real boundary without a human F6: after
the preview is ready and the captain is in `NAVISTATE_Walk`, it stands the
captain at the Research Pod and calls `pc_p2_cave_checkpoint(false)`. Process 1
writes the transfer and exits 42; the campaign supervisor validates it and
re-serializes the entry; process 2 restores it. `validate()` gate reports
`passed=true` on all ten checks (`output/p2-lanes1011-cave-restart-run-02/`).

```text
# process 1 (write), 960x540
P2_LANE11_SQUAD red=16 yellow=1 purple=1 bulbmin=1
P2_CAVE_TRANSFER floor=2 survivors=19 health=0.625 failed=0
P2_LANE11_WRITE ok=1
# p2-cave-transfer.txt
P2_CAVE_TRANSFER_3
...
2 0.625 19
16 lines of "1 0", then "2 1", "3 2", "5 0"
# process 2 (read), 960x540
P2_CAVE_RESTORE species=5 maturity=0
P2_LANE11_READ bulbmin=1 observed=60
PASS P2_LANE11_RESTORE
```

The only deviation is the skipped F6 confirmation dialog (`confirm=false`); the
guarded checkpoint handoff and restore are the engine's. Unit tests:
`tests/test_pikmin2_cave_restart_runtime.py`.

## Provenance and remaining

- Native `opencode/p2-lanes1011-elecbug` @ `416ccb49` (patches
  `native-candidates/p2-lanes1011-elecbug/0001..0005`).
- Root doc and tests on `opencode/p2-lanes1011-root`.
- Remaining is breadth, not this path: production cave placement, the full
  authored floor/treasure roster and the surface roundtrip (#114) stay with the
  cave lane.
