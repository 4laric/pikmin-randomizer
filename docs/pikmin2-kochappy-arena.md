# Dwarf Red original P1 arena staging

Issue #120 / #186. `python -m experimental.pikmin2_kochappy_arena --assets <P1 assets> --bank <validated Kochappy bank> --output <private output>` stages the original Impact Site course through the existing chal0 experimental slot. Original practice.ini and every practice course file (including embedded collision/routes) are byte preserved and hashed. The stock four goals remain; all old chal0 generator sources are suppressed. Exactly two engineered Chappy generator records are added: source Kochappy Red 186001 and ordinary P1 control 186002. Only the first is profile-bound.

Corrected position helper writes full XYZ with zero translation offsets. Source yaw remains explicitly unapplied. Private deterministic birth helper changes only each selected generator circle radius from 50 to zero, retaining before/after hashes. Positions are engineered near the original landing, not imported P2 positions; terrain and actual stored birth require native acceptance. A later fixture should compare generator position and personality stored birth, then log postphysics drift separately.

Cargo-free preview avoids adding a P2 treasure or changing the original map. No Pod is configured: corpse reward gates are untested and ordinary P1 delivery is not evidence of P2 economy acceptance. Original map assets are shared read-only links; all modified generators and profile assets are private files. Do not edit linked original files.

Staging does not assert AI, combat, delivery, reset, or native material acceptance. Existing Red room fixtures exercise a different scene and cannot establish these arena gates. Executable hash/provenance must be added by a future runtime harness. There is no native build or live seed modification in this wrapper.
