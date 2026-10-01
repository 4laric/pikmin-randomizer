# Damagumo bind-mod conversion (#727)

Lane `damagumo-bind-mod-conversion-native`, issue #727. Owner: Codex through
shared account `4laric`. Produces the missing `longlegs_Damagumo_bind_00.mod`
from the pinned staged artifacts and proves it loadable through the family
bind path checks. Owns only the conversion driver, its tests, this doc, the
guarded fixture, and the build helper. No other family/shared/native edits,
no ADMIT.

## Conversion (reproduced, not invented)

Inputs (hash-pinned, read-only): #670 `damagumo-family.json`, #678
`Demon/enemy.bmd`, #685 `damagumo-slot-312004.json` (slot 312004, species
Damagumo, source_id 56). Pipeline: the shared converter consumed read-only
from the pinned long-legs visual module tree, with the family MAT3
multi-stage policy (`approximate_materials=True`, documented for Houdai) plus
explicit bind matrices from shared `joint_matrices` (the BigFoot
explicit-matrices precedent) under `bake_rigid=True`. Damagumo has zero EVP1
envelopes (rigid) but carries a direct matrix reference the strict decoder
only accepts via the explicit-matrices path; the matrices are the model''s
own bind pose, so geometry is unchanged versus default decoding. Output:
104,640 bytes, 902 vertices, 1696 triangles, 1 shape, 4 textures.

## Family bind wiring (verified, no change needed)

`pc_p2_long_legs.cpp` already resolves Damagumo end-to-end once the artifact
exists: `SPECIES` table maps it to `longlegs_Damagumo_bind_00.mod`
(file:57-60), `speciesEnum` + `p2LongLegsParmsFor` carry full Damagumo params
(fsm.cpp), and generic `loadBind` (file:386-408) reads the file, enforces
the 4 MB budget, parses resources and loads the shape. No .cpp change was
required; the fixture proves the artifact through those same checks, and
draw-path execution with a live actor is #173 arena scope.

## Fixture and proof

`tools/p2_damagumo_bind_mod_fixture.cpp` (replacement-main, guarded) reads
the staged artifact, enforces the bind budget and runs the real
`p2animation::resources()` container parse, emitting
`P2_DAMAGUMO_BIND_LOADED` + `PASS P2_DAMAGUMO_BIND_MOD_LOADED` with no abort
and no captain-down. Guard vendored verbatim (`scripts/p2_fixture_captain_guard.h`
sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`),
proven by self-test (exit 0) and negative (exit 86 BLOCKED, no PASS).

## Captain safety #632

Guard runs in the engine-independent self-test/negative modes; this fixture
boots no game world so there is no Navi to observe. No blanket
invincibility; no fake guard provider. Guard/source hashes recorded.

## Remaining scope

#173 stages the artifact into its arena and executes the draw path with a
live Damagumo; #312/#186 review where shared semantics apply. All six
runtime gates UNTESTED here.
