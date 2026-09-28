# Mamuta runtime and Kimi handoff — #230

Native `7faa64475176658af85e2f558858c6d660cd4d20` passed the bounded private original-arena run. The fixture copies/link-checks production inputs through the existing provenance builder, replaces only its App and tutorial handler, and supplies ordinary Controller A pulses to dismiss the extinction tutorial. Enemy states, attacks and animation counters are not forced. The captain is placed near the configured actor for observation.

Evidence outside the checkout: `C:/Users/alari/pikmin-randomizer/output/p2-lifecycle-batch/mamuta-native-run-01/result.json`; session `0b543675ef0640dc82ce05a624ff4d0d`. Private executable `mamuta-runtime-build-01/fixture.exe`, SHA256 `943ecba1aef4f3ea70870bbc942c7cd6160f66355a715134f46574025d4f51b9`. Full source/build snapshots and compile/link commands are under `mamuta-runtime-build-01/baseline/provenance.json` and `instrumentation.json`.

Passed: exact generator221001/type24/full stored birth(-150,30,1850); source wait-anchor draw; ordinary Chappy generator221002 declined the binding; 300 normal updates; explicit forget/reset declined subsequent drawing; zero GX desync warnings. Motion4 and motion2 were observed naturally. Swing, corpse, same-family ordinary control and P2 planting were not tested. The tick120 screenshot shows a P1 fallback posture; it is not an imported wait-pose screenshot. No false visual screenshot claim substitutes for the source-wait draw log.

Run focused host tests with `py -3.12 -m unittest tests.test_pikmin2_mamuta_native tests.test_pikmin2_mamuta_runtime -v` (five tests). The runtime driver rejects missing wait rendering, incomplete native completion, incorrect identity/height and GX desync. `experimental/pikmin2_mamuta_runtime.py` builds the private fixture; `scripts/test_pikmin2_mamuta_native.py` stages fresh sessions and records executable SHA before execution.

## Manual production-input handoff

Supplementary source-wait capture: `C:/Users/alari/pikmin-randomizer/output/p2-lifecycle-batch/mamuta-native-capture-03/e21093514d904e4b8f6d98b584eb64ac/mamuta-source-wait.png`. The fixture waits for ten consecutive naturally reached Wait1 frames after normal rendering; the source draw log precedes capture. Imported Mamuta is visibly present, with a pale, flat-looking body unlike the textured P1 fallback. This passes visible binding, **not material fidelity**; Kimi should audit the imported materials/geometry. The feet are partly occluded by the arena tree rim, so ground-contact quality is not signed off.

Supplementary run passes the same identity/control/reset gates with zero GX desync. Fixture `mamuta-runtime-capture-03/fixture.exe` SHA256 `d7509a7d984ca472ff258b47ce61127fd433ae1f279bf4769b18b3436bd96d81`, using the original immutable link-input snapshot and tutorial object. Its local `commands.json` records the private relink. Prior capture02 is preserved but its capture preceded the imported draw submission, so it is not counted as imported visual evidence. No shared source/build changes were made.

Launch `C:/Users/alari/pikmin-randomizer/output/p2-lifecycle-batch/mamuta-kimi-01/Play.cmd`.

This separate directory contains an immutable copied production `nectar.exe`, SHA256 `978f77755b7574f7c7570daf4041243ede18100014bdc5ec29639e4406a82477`, from the same native HEAD. Session `412c4bbc80af491b847a8af1d7d067fc` uses Kimi's source import unchanged. `handoff.json` records executable and session paths. This manual launcher has no fixture tutorial auto-dismissal, actor manipulation or auto-reset; normal user controls apply. The launcher itself has not been physically playtested by this agent.

Expected: P1 Miurin behavior with P2 static wait/swing/dead anchors; unsupported motions temporarily show P1 graphics. Do not score P1 in-place flowering as successful P2 planting or 99-cap semantics. Shijimi companions are not created. This is an isolated test arena, not a campaign seed.
