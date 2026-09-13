# Compact skeletal Snow loading (#373)

Codex implementation owner using shared account 4laric. With the skeletal opt-in,
Snow now loads only `snow_wait1_00.mod` for topology, materials and textures. All
other poses come from the joint bank and skin bindings. The old sampled renderer
continues to load its full bank when skeletal playback is disabled.

The loader validates the base model using the existing binary resource/topology
parser and verifies its geometry counts against the skin data when binding an
actor. It still validates animation clip durations against the joint bank. A
missing base model is fatal; missing redundant poses are valid in skeletal mode.
Each actor retains its private mutable geometry and deformation buffers; only
the immutable model resources are shared.

`experimental.pikmin2_skin_fixture.enable` physically removes the 119 redundant
pose files from a freshly generated private test stage, after verifying that each
resolved file is within that stage. The source bank and player assets are not
edited. `skeletal-models.json` records every removed file and the retained base
size. The native geometry verifier no longer attempts to read the sampled bank
when checking skeletal output.

Reproduce using `experimental.pikmin2_skin_fixture build/run` as documented in
[the skeletal playback guide](PIKMIN2_SKELETAL_PLAYBACK.md). `--reference` retains
the sampled bank for comparison. Existing player packages and defaults are not
changed. This removes redundant model loading; it does not change skeleton
sampling, combat events, skinning math, source material approximation or callbacks.

## Evidence

Native `bcd5087d4af11d40fa4838ad744d9b6d9173443d`; production build passed.
Nineteen regression tests and eight subtests passed, including the 351-frame
weighted Groink and 390-frame rigid Snow source comparisons.

The native skeletal lifecycle exited 0 with all acceptance markers: live draw,
attack, death, corpse draw, native carrying, Pod delivery, exact ledger and
no duplicate credit. There were 51 rendered-geometry comparisons. Fixture SHA:
`dd3ae138ce67b19dd272a5fb83a6cb487eb00e027385dbf6df4c7dfdec940fc8`.
Evidence: local `output/compact373/lifecycle`, referenced stage `result.json`,
`native.log` and `skeletal-models.json`.

The loader reported `poses=1 mod_bytes=16000 texture_attach_calls=1`. The private
stage had 119 removed pose files totaling 1,904,000 bytes. The prior bank loaded
120 models totaling 1,920,000 bytes. Joint/skin data and actor geometry buffers
are additional and unchanged. This is a measured model-data/dependency reduction,
not a claim that whole-process memory or frame times fell by the same amount.
Load time in this run was 0.129 seconds; no speed improvement is claimed.

A separate fresh stage with the required base removed exited 3 before Snow
registration; the source loader rejects the failed base-file read. The normal
sampled campaign path passed the production boot/handshake smoke using its full
bank. These are under `output/compact373/missing-base` and `reference`.
Fixture assigns Pikmin actions and repositions the captain; it does not prove
P2 AI parity or unrestricted player campaign/save acceptance.
