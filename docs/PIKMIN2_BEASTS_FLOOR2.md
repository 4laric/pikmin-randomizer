# Hole of Beasts floor 2 staging

This is a cargo-free, prepare-only profile, **not launchable** on the current preview. `experimental.pikmin2_beasts_floor2` emits `readiness.json` with `native_ready=false`; it has no launch option.

US source `user/Mukki/mapunits/caveinfo/forest_1.txt`, definition 1, specifies two BlackPom (Violet Candypops), six HikariKinoko and two KareOoinu_s. The cap list specifies two Egg. There are no treasures, gates, geysers or clogged holes. Source dependency closure also needs the Pom parent manager and TamagoMushi egg helper. Eggs, plants, egg drops/helpers and descent remain unsupported here.

The source unit pool `1_units_cent2_tsuchi.txt` contains room_cent2_4_tsuchi, cap_tsuchi, item_cap_tsuchi, way2_tsuchi, way2x2_tsuchi, way3_tsuchi, way4_tsuchi and wayl_tsuchi. This bounded profile selects only the cent2 room and caps its exits. It preserves source routes and the two type-8 candidate transforms (slots 30 and 31), projects their ground and retains stable floor-scoped identity. This is an explicit engineering selection, not retail generation. Room materials retain the existing explicit approximation and deferred texture animation limits.

Two existing P1 Pom actors receive explicit Violet conversion metadata. Their native IDs are 62000 and 62001. This reuses the existing conversion proxy; it does not implement P2 Pom models or its full FSM. Twenty scaffold Pikmin and two receiver/ship anchors are engineering placements. The default treasure and enemy are removed. The generator validator rejects cargo, unexpected actors or incorrect flower metadata. No cargo config, treasure model override or economy receipt is emitted.

Native blocker: `native/pc_port/pc_p2_preview.cpp`, `pc_p2_preview_setup`, unconditionally requires a `pr05` before loading the treasure and initializing the optional Pod/Purple systems. A future explicit cargo-free opt-in must skip treasure binding/loading and preserve Pod/Purple initialization; absent opt-in must retain existing validation. It must also keep cargo collection absent and validate no reward can be produced. A hidden zero-value treasure is not an acceptable workaround. This batch makes no native edits and does not claim conversion or traversal runtime acceptance.

CLI: `py -3.12 -m experimental.pikmin2_beasts_floor2 --assets <P1-assets> --units <selected-unit-import> --catalog <catalog.json> --purple <Purple-bank> --output <private-output>`.

Focused tests cover altered source populations/weighted cargo rejection, source placement/ground preservation and generator decoding with zero cargo. Local source import hashes are checked against the catalog and every selected unit output before staging.

Local preparation passed at output/p2-beasts-floor2-batch/runs/ecdd10ce4e4c4d87b65f7014c353ef38: 24 decoded actors, two flowers, zero cargo, empty allowed receipts and no Pod/cargo/economy config. Source candidates are (-55,0,75), yaw215 and (75,0,-95), yaw45. Three focused tests passed. No native process was launched.
