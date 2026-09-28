# Static cave transition visuals (#112)

Local importer:

```powershell
py -3.12 -m experimental.pikmin2_transition_assets --iso <US-disc.iso> --output <new-directory>
```

`transition-assets.json` schema1 contains `models.hole` and `models.geyser`, each
with `file`, `sha256`, source model hash, bounds and placement. Files are
`cave_hole.mod` and `cave_geyser.mod`. Native placement is unit scale, yaw zero,
Y offset zero at the validated ground anchor. Keep source origins: bottom-aligning
these assets would move their slightly underground rims above the terrain.

Sources are `user/Kando/objects/dungeon_hole/arc.szs:dungeon_hole.bmd` and
`user/Kando/objects/kanketusen/arc.szs:kanketusen.bmd`. Decomp references are
`src/plugProjectKandoU/itemHole.cpp` and `itemBigFountain.cpp` resource loaders and
`makeTrMatrix`. Both exposed states set bury depth zero. The source hole
`changeMaterial` hides its flag joint; the importer verifies that exact joint/shape
layout and omits the flag shape and unused vertices. The geyser has a source
vertical joint scale of1.163055, baked into positions/normals through the existing
rigid converter, so runtime scale remains one. Scale-compensated joints are rejected.

This is static artwork only. Geyser `damage.bck`/`out.bck`, water particles,
collision platforms, sound, emergence/burial state and retail interaction FSM are
not imported. The existing F6 checkpoint interaction remains separate. The hole
rim does not cut a hole in terrain. Copyrighted source/generated files stay local.

Local extraction succeeded for both assets and a second extraction produced
identical model and manifest bytes. Focused tests cover source scale/translation,
unsupported/singular transforms, deterministic manifest contracts, truncated reads
and refusal to overwrite prior imports. Native visual acceptance is separate.

## Integrated playtest

Native `5421633e` binds these models to the existing floor-specific anchors via
`P2_CAVE_VISUAL_1`. The campaign option is `--transition-assets <import-directory>`;
it requires `--transitions`. Both model hashes and the manifest are validated and
frozen before opening a checkpoint, then included in its content identity. Only
the selected model is written into each private run. Missing assets, changed
hashes, unsupported transforms and unsafe model names are rejected. Omitting
the option retains the engineering markers and the previous save identity.

The actual native render fixtures were inspected on both floors. The hole rim
and geyser base appear at ground level; the geyser remains a static rock model
without water effects. F6 at the model retains confirmation and the established
checkpoint rules. This is not a physical terrain opening or a complete P2 actor.

Validation: 181 Python tests and 28 subtests passed. The native two-floor test
with these assets retained 480 Pokos, 19 survivors including ten Purples,
maturity and health; repeated reload and extinction checks passed. The fixtures
inject collection/casualty/conversion and reposition the test captain, so they
do not replace a controller playthrough.

Local launcher: `output/p2-transitions-batch/Play.cmd`, with a new `play-session`.
Production SHA256: `58534df2090d57845c782155eb14b2bb4536a0c56ee4362d19cdddf7a47d6ea4`.
Visual evidence: `output/p2-transitions-batch/hole.png` and `geyser.png`;
persistence evidence: `output/p2-transitions-batch/native-check/result.json`.
Models, binaries, generated runs and saves stay local.

The original Atlas position was also rechecked with the previous seam fix. It
still stalls on a distinct uphill section before the Pod; #123 remains open and
the validated engineering placement remains in this bundle.
