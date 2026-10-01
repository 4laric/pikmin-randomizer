# Dwarf Red runtime module validation (#120 / #186)

The new `experimental/pikmin2_kochappy_fixture.py` driver instruments an immutable native room fixture and runs health/registry or longer combat/corpse probes. This uses the existing imported concrete room, **not the planned P1-stage arena**. It does not edit maintained generators or production native sources.

## Provenance

Native `e704b268`, snapshot at `output/p2-red-runtime/snapshot`: 47 production link inputs copied with before/copy/after hash verification and matching archived native headers/tools. The input list was compared against current Ninja; production `pc_main` is replaced by the private fixture, while new Kochappy and Breadbug objects are included. The camera-adjusted private binary is `output/p2-red-runtime/fixture-v3/preview_p2_room.exe`, SHA256 `4537d0a32155346e081b109e44477528edde58240ad73f4507caded1376c5366`.

The driver records generator position and offset separately, their expected XYZ sum, generator/profile hashes and exact executable hash. It supplies source identity through the separate Red installer. An ordinary Chappy is born as a control and must retain its original 130 initial/max health and no Red name.

## Probe boundaries

The health probe verifies Red initial/max health 200, ordinary fallback, explicit forget/reload/reset, and actual manager slot reuse when the actor is legally removable. An unremovable actor is reported as unmeasured, never coerced into passing.

The lifecycle probe leaves enemy health and animation intact. The inherited fixture assigns Pikmin attack actions and may assign transport actions if free recruitment is insufficient. Actual native damage, death animation, corpse construction, physical hauling and delivery must still occur. This is not a manual-player combat test. The captain is repositioned to bring the enemy into the real camera/render path. Post-delivery reset checks registry membership without dereferencing a consumed corpse.

## Initial evidence

`output/p2-red-runtime/lifecycle-circle/evidence.json` records a native exit 0 with successful Red live, attack, death and corpse render markers, source name/max-health retention, real damage kill, physical hauling over 321 units, Pod total 182, duplicate-credit rejection and registry reset. Captured attack/carried images were inspected: the Red model is visible and material rendering is intact in those frames. Native load reported one texture attachment for the 60-pose/960,000-byte bank.

**Overall acceptance remains failed in that run because exact spawn XYZ did not match.** The inherited room actor is a `GenAreaCircle` radius-50 spawn. Native `GenTypeAtOnce::setBirthInfo` samples the circle; `GenAreaCircle::getPos` adds an XZ random offset to generator position. Therefore the fixture's declared point `(185, 0, -180)` is not an exact actor position. This is source-backed fixture randomness, not a coordinate-packing or Red policy defect. The unnormalized run is retained rather than relabeled as a pass.

The earlier short baseline probe passed ordinary health and actual slot reuse with no Red profile. The first Red health probe passed health/registry checks but initially failed both exact XYZ and offscreen visual coverage; the camera-adjusted lifecycle run resolved visual coverage. The later fixed-point runs below resolve the position gate without relabeling those initial failures.

## Fixed-point rerun

With integration approval, the Red preparer reuses the content lane's `deterministic_births` helper to change only the selected private generator's circle radius from 50 to 0. Positions, offsets, identity, types, flags and every other byte remain unchanged. No maintained generator writer or native file changed. `output/p2-red-runtime/radius-byte-audit.json` independently compares the failed-circle input and new input: only bytes 4067 and 4068 changed, inside the four-byte radius field beginning at offset 4067; file length remains 4275 bytes.

- Before SHA256: `2f6fd4950392fa2d7707f664c390366afdad1e8cf8a4300d18be707b07228792`.
- After SHA256: `77f49a2021729c76b2a9544d493249ed9515569bd9db728166b2524d4a53d96c`.

The same `fixture-v3` executable passed all measured gates in `health-fixed/evidence.json`, `baseline-fixed/evidence.json`, and `lifecycle-fixed/evidence.json`, each with exit 0. The Red startup log now reports exactly `(185, 0, -180)`, source `Kochappy` ID 1 and generator 385875968. Initial/max health is 200; the ordinary control stays at 130. Short Red checks pass explicit forget, reload and reset; the absent-profile run preserves defaults.

The fixed lifecycle observed attack/death animation, live/corpse rendering and max-health/identity retention, actual damage defeat, corpse hauling beyond 329 units, total 182 Pokos, duplicate-credit rejection and post-delivery registry reset. Actual manager slot reuse was not measured in the fixed runs because the actor was not legally removable; the harness did not force removal. Scene-manager reconstruction and the separate P1-stage arena remain open. The 32 focused Red fixture/bank/shared-normalizer tests pass.

P1-stage arena acceptance, natural manual combat, and scene-manager reconstruction remain untested. No full P2 FSM, collision or animation-event parity is claimed.
