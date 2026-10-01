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

Historical `output/p2-playable-cave-930/package-03` showed a boot with 20 reds,
Pod, water, and two native treasure/bud actors. It did not prove natural conversion
or carrying and is not a current runnable handoff. Fresh staging and executable
provenance are mandatory before the next runtime acceptance run.

Still require fresh natural Blue/Yellow conversion, water behavior, mixed-squad
barrier denial, electric opening, real treasure transport and Pod reward, exit,
and repeated checkpoint/restart observation. Captain-down negative controls and
current fixture/window/background adoption must accompany automated acceptance.
Bud visuals remain colored floor markers and automatic ordinary plucking remains
provisional. Template cargo beside the Pod is scaffolding, not a cave treasure.
No full-campaign, retail-geometry, AP, or gameplay-sign-off claim is made.

All assets, binaries, generated packages, saves and logs remain local under ignored
`output/`; the change is source only.
