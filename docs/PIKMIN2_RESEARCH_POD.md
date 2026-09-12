# Research Pod and economy engineering preview

Owner: Codex using shared 4laric account. Tracking: [#111](https://github.com/4laric/pikmin-randomizer/issues/111), parent [#109](https://github.com/4laric/pikmin-randomizer/issues/109). Experimental, outside Pikipelago v0.1.

## Implemented boundary

The local-disc importer reads the Pod archive and US treasure/carcass configurations. It supports selecting one of Emergence's three treasure IDs. The first tested selection is `dia_a_red` (Citrus Lump): value 180, carrying strength 15, maximum 25 carriers, taken from the source configuration. The native Dwarf scaffold yields 2 Pokos. The source archive/config hashes and conversion decisions are recorded locally in `pod.json`.

The converter can now explicitly bake rigid joint hierarchies into a static bind pose. Parent transforms, signed rotation angles, packet matrix slots and vertex/normal remapping are handled; skinned envelopes, scaled joints and billboards remain rejected. This is not animation support. The Pod converts to 367 vertices and 594 triangles. Material rendering still uses the existing first-texture approximation. Treasure render vertices are raised by their negative minimum Y to adapt a central P2 pivot to P1's bottom-anchored pellet.

In the opt-in preview, all carrier colors route to the Pod anchor. The imported static Pod replaces that anchor's Onion visual; its withdrawal menu and spotlight are suppressed. This reuses the P1 GoalItem destination and collider, with the Pod placed at its suction height. It is not a complete native P2 Pod actor. Treasure physics still use the preview pellet scaffold; the model does not define a new collision hull. Corpse physical behavior remains the P1 Dwarf's.

Deliveries are intercepted before Onion seed production or P1 repair credit. The window title shows the Poko balance and latest receipt. A separate `p2-economy.txt` records unique treasure and authored corpse-instance receipts, with a flushed temporary file and replacement on successful writes. Duplicate IDs cannot pay twice, changed values are rejected, and failed writes leave the in-memory balance unchanged.

**This ledger is not a game save.** It does not restore actors, squad, cave layout, day or collection visibility. The launcher creates a new disposable run each time. Reusing a ledger prevents duplicate money but still regenerates the fixture world. Cave lifecycle work must bind the ledger to a checkpoint and add floor-instance namespaces for corpse IDs before campaign use. One process per run is assumed.

## Local reproduction

```powershell
python -m experimental.pikmin2_pod --iso "PATH/PIKMIN2.iso" --output output/pod-new
python -m scripts.preview_pikmin2_emergence --assets "PATH/pikmin/assets" --imported output/emergence-import --assembled output/emergence-floor1 --treasure "PATH/room105/treasure.mod" --pod output/pod-new --exe "PATH/nectar.exe"
```

Use `--floor 2` without `--assembled` for the slope layout. Omitting `--pod` retains the previous bolt/Onion preview. Normal P1/AP play cannot activate the Pod through these hooks without the explicit isolated preview mode.

## Validation and remaining work

Forty-three focused Python tests pass, including transform composition, normal translation exclusion, shared vertices under different joints, local Pod conversion and skinning rejection, source catalog framing, and assembled preview preparation. Standalone native ledger tests cover duplicate receipts, reload, changed value rejection, malformed input and failed publication preserving the previous balance.

The first native Pod run, `output/pikmin2-emergence-preview/55b98f11051f48ba98594a127fd28267`, passed with 20 Reds: actual transport returned the 15-strength treasure through both room joins, awarding 180 Pokos; actual combat killed the Dwarf and carriers returned its corpse over 1,264 units, reaching 182 Pokos. Repairs remained unchanged. The fixture explicitly assigns transport/attack AI and used its corpse recruitment fallback; it is not manual gameplay sign-off. Its screenshot exposed a treasure pivot mismatch, corrected in the subsequent import.

Still pending: Pod animations/effects and dedicated collision, full treasure/corpse inventory UI, multiple treasures per floor, mixed carrying-strength upgrades, complete roster accounting, cave/squad checkpoints and manual gameplay acceptance. [#112](https://github.com/4laric/pikmin-randomizer/issues/112) owns descent/exit and world persistence; [#113](https://github.com/4laric/pikmin-randomizer/issues/113) owns actual Purples. Issue #111 remains open until its full acceptance criteria are met.

Final mixed-color evidence: `output/pikmin2-emergence-preview/0cae7a27f628432790032da8b65faa5b` exited 0 with red/yellow/blue carriers, 180+2 Pokos and a controller walk back to the Pod. The corrected Citrus Lump and static Pod screenshots were inspected. Floor 2 run `f7d846923ff149f0a986a427f65232d8` also passed: mixed carriers returned the 15-strength treasure up the source slope routes for 180 Pokos, with repairs unchanged. These tests use normal strength for every color; they do not prove upgraded-strength combinations.

Local launchers: `output/pikmin2-pod111/Play.cmd` (assembled first floor) and `Play-floor2.cmd` (slope room). Both start with 20 Reds; the mixed squad is an automated fixture arrangement. Packaged native executable SHA-256: `fcd2e7846e0b1848650eb4389f21ebe2c57dc6b8b3e500eaf9fc01d8ab8f5d78`.

## Audio report

The user heard a continuous dial tone during an automated preview. It stopped when that fixture process was closed. [#116](https://github.com/4laric/pikmin-randomizer/issues/116) tracks the unresolved cause. Automated fixtures now select SDL's dummy audio device before initialization; they still run the mixer and can capture PCM without opening a speaker device. This is a test-harness fix, not a claim that normal preview audio is repaired. A silent floor-2 capture at 20–35 seconds contained varying frequencies and amplitude, rather than establishing one constant tone; that alone does not rule out a later or device-specific failure.

The local engineering launchers temporarily use the same silent device while this is investigated. Normal P1/AP audio settings and system volume are unchanged.

The final silent fixture also passed the previous no-Pod Onion/bolt/combat/corpse path (`1aaf0c7570e8478181fa0e7f9ba402eb`), exercising the guards in the same native build. Its PCM was captured locally for comparison; a renderer or sequencing root cause has not been established. Native source snapshot: `9630447e`.
