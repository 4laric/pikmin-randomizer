# Honeywisp matched material comparison (#207)

New experimental/pikmin2_qurione_material_compare.py instruments only a private
copied native family translation unit. Both source waitl pose0 models draw in the
same frame at equal depth, scale1, yaw0, x=-35/+35, y=z=0. A fixed view eye0,80,300
and target0,20,0 removes random live flight height from this diagnostic. This is
not live actor positioning, animation fidelity or gameplay acceptance.

The left model is the original MOD; right is the source-recognized TEV-only patch.
No geometry or lighting-control changes. Both share ambient70,60,70, FOV23 and
aspect1.5998 in this run. Parser requires both cases and rejects missing or changed
pose/depth/scale/projection/ambient evidence. Two tests pass.

Private copied b602d8c43dc6a1132821f787b99a28097c3c7521 native inputs were compiled
and linked; copied link inputs are hashed before/after. Executable
6427e02104b587ddcc8225274c860948416550542ad235781a6529ed3c1e023d
completed exit0 in24.95seconds. Build/input record:
output/p2-qurione207/fixed-fixture/{commands.json,inputs.json,build.log}.
Runtime evidence: output/p2-qurione207/fixed/evidence.json.
Captured pair: output/p2-qurione207/fixed/comparison.png.

The same-frame image visibly restores pink eyes/mouth on the right while the left
has white facial features. This verifies the isolated source TEV constant/stage
correction has the intended visible effect. Both retain very bright bodies; source
lighting-channel parity is still unresolved and no full fidelity claim is made.
Host glow remains separately visible above/right at the actual actor locations;
it is not drawn by this fixed-pose helper. No effect suppression was performed.
The previous random-flight comparison remains preserved as inconclusive evidence.

Run tests: `py -3.12 -m unittest tests.test_pikmin2_qurione_material_compare`.
No shared native/converter edits, builds, exports or commits were performed.
