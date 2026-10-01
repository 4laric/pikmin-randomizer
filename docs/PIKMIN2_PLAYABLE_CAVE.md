# Bounded forest_1 developer cave (#930)

Implementation owner: Codex through shared account `4laric`.

This is an isolated developer package for an original engineered floor, not retail
forest_1 geometry or an accepted campaign. Its `cave.json` descriptor uses
`p2-bounded-developer-cave/1`, independent of released seed manifests, item pools,
AP locations, and campaign sessions. No released seed/AP/session files change.
The native canonical `forest1-bounded-v1` table retains its seed/slot derivation,
two treasure identities, Blue/Yellow bud budgets, and hazard ordering. Descriptor
color requirements are conservative developer metadata; capacity is never supply.
There is no AP delivery or campaign reward integration.

## Fresh staging and hand play

Use current, verified native and generator executables from private source/builds
(or the preferred verified CI artifacts). The generator is built from
`tools/p2_cave_generator_test.cpp` and `pc_port/pc_p2_cave_generator.cpp`.
Run `scripts/stage_pikmin2_playable_cave.py` with these required arguments:

- `--assets`: legal installed P1 assets containing `dataDir/stages/`.
- `--pod`: local extracted bundle containing `pod.mod`, `treasure.mod`, `p2-pod.txt`.
- `--exe`: completed native executable supporting the barrier sidecar.
- `--generator`: completed native cave-generator executable.
- `--output`: a new private directory under ignored `output/`.

`--seed 930 --slot Player1 --salt 0` selects the deterministic descriptor and
physical spacing. Salt changes corridor length without changing logical identities
or requirements. All corridors are 100 units wide. Original mesh, native collision,
water attributes, routes, actors and sidecars are regenerated on each staging run.
The current overlay helper is reused; a new session starts with 20 red Pikmin.
The entry protocol restores checkpoint species/maturity into the staged actors.

The package is local and depends on the source checkout and legal asset paths.
`Play.cmd` starts hand play using those paths. It verifies packaged file hashes,
uses the canonical machine-capacity gate, takes a session lock and serializes
same-launcher process admission. It never stops another owner's process. A fresh
run directory is created per launch. Existing cave/P2 environment overrides are
removed; the window request is 960x540, with native centering required and checked
in runtime evidence. Agent-driven tests must use the current background-test
policy and bounded supervision; hand play keeps ordinary focus behavior.

## Barriers and restart

`p2-cave-barriers.txt` uses `P2_CAVE_BARRIERS_1` with cave/floor/native-seed identity
and exactly one AABB per blocking door in the carry plan. Volumes span the entire
100-unit corridor with wall overlap; bud nodes have no barrier. Water leaf volumes
cover all three wet tiles. Electric volumes sit on the approach to the treasure.
These sidecars require the accompanying strict native reader; an older executable
is unsuitable even if it boots. Geometry and unit tests cannot establish real
mixed-squad carry denial; that remains a runtime gate.

F6 near the far hole requests a floor-boundary checkpoint. Captain health, RGB
squad color/maturity, and consumed bud budgets restore together. Pending sprouts
or conversion outputs must block native checkpointing. Durable native treasure
receipts suppress already-delivered treasure after restart and unsaved exits.
The launcher validates identity and recovers a completed transfer if it previously
stopped before replacing the checkpoint. It rejects a missing receipt ledger in
an existing session rather than silently restoring treasure. Ordinary unsaved
exits restore the last boundary squad (the initial 20 reds before a first boundary),
while delivered treasure remains collected. This is not full campaign resume.

The current developer descriptor intentionally rejects old `seed.json` packages
and any campaign/AP fields. Do not migrate or edit existing user saves; stage a
new package and keep old package evidence read-only.

## Validation and remaining acceptance

`tests/test_playable_cave.py` covers deterministic descriptors, strict rejection,
physical mesh/water, dry-route cuts across salt variants, full-width barrier
coverage, capacity-policy delegation, foreign/malformed receipt and checkpoint
rejection, and crash recovery. Synthetic geometry tests are not gameplay evidence.

Current evidence (2026-10-01) is under canonical
`output/cave-930-resume/`. Production native commit
`19ac61e9a30b0ad9f30e1cf5b07daa22fb8e4088` built clean in
`output/native-cave-930-resume-build`; the no-work dry run passed.
Executable SHA-256:
`6b5a780bfab2fe44834777b49ab086fb0985455d9d8ae270fe053087b236f59f`.
`fixture-01/provenance.json` records the separately linked replacement main.

The guarded fixture is `tools/p2_playable_cave_fixture.cpp`. Set
`P2_CAVE_TEST_SCENARIO` to one of the scenarios below, stage a fresh seed930/salt0
arena, and run it through the canonical bounded fixture supervisor with its matching
`PASS CAVE_PLAYABLE_*` marker. Apply `randomizer.test_run.apply_test_run_env` for
agent tests and call `scripts/capacity_gate.py --kind game` immediately beforehand.
Never reuse a run directory. The local `run-scenario.py` records the exact staged
commands; every run has hashed inputs, capacity snapshot, log and result.

| Scenario / local run | Observed result | Evidence limit |
|---|---|---|
| `boot` / `run-boot-01` | PASS: 20 Pikmin, two buds, two treasure actors | Startup only |
| forced captain down / `run-negative-01` | Exit86, captain-down marker, no success | Deliberate negative input; supervisor correctly reports false |
| `barrier` / `run-barrier-01` | Six accepted electric reactions across90 units | Six free reds positioned by fixture; no carrying claim |
| `carry_denial` / `run-carry_denial-02` | Ordinary treasure pickup, accepted electric reaction, attachment released, zero rewards | Six reds positioned and put in free mode; one real carry denial, not all mixed-squad cases |
| `blue_checkpoint` / `run-blue_checkpoint-01` | Scripted native throw produced one Blue; 20 survivors and consumed budget1 checkpointed | No species write; captain moved to exit by fixture, so no traversal claim |
| `restore` / `run-restore-01` | Fresh process restores20 live Pikmin including Blue and loads bud budgets | Harness consumes actual transfer; normal F6 UI flow not exercised |
| `restore` / `run-restore_receipt-01` | Water treasure actor suppressed, electric actor remains | Durable receipt deliberately injected; no real Pod delivery claim |

Each positive run exited0 within8 seconds under a60-second supervisor. Logs record
centered960x540, healthy captain and current20-Pikmin entry. The first carry-denial
attempt was refused by the GPU capacity gate and launched no game; fresh attempt02
passed after admission cleared. Headless barrier, generator and receipt-host tests
pass. Python cave/staging/room/gate tests:46 passed,4 native-dependent skips.

Still open: player-driven Yellow acquisition and both colors' complete routes,
Blue water-carry immunity, mixed-squad and high-speed runtime denial, electric
opening, actual Pod reward, natural exit traversal, and repeated player F6/resume.
The checkpoint harness compared supplied squad/budget data and observed Blue in a
fresh process; it does not prove every health/maturity value through a full campaign.
Bud visuals remain colored floor markers and automatic ordinary plucking remains
provisional. Template cargo beside the Pod is scaffolding, not a cave treasure.
No full-campaign, retail-geometry, AP, or gameplay-sign-off claim is made.

All assets, binaries, generated packages, saves and logs remain local under ignored
`output/`; the change is source only.
