# P2 families — blockers to full implementation

Integration #422 reconciles the pushed family candidates onto the maintained line.
See [combined integration evidence](PIKMIN2_INTEGRATION_422.md) for current merge
status and validation; older handoff sections below retain their historical bases.


Companion to [family issue coordination](https://github.com/4laric/pikmin-randomizer/issues/186). "Full implementation" = the pipeline's **Family complete** level: every parent identity implemented as source P2 behavior (FSM, animation events, collision, receivers, rewards, lifecycle) passing the arena gates in mixed scenes.

Current levels are visual/display only unless noted. The dominant blocker everywhere is **source-behavior translation**: most families render as P1 proxies with sampled visuals and have no source FSM, receivers or reward logic. Issues: [#186](https://github.com/4laric/pikmin-randomizer/issues/186) (coordination/acceptance), [#128](https://github.com/4laric/pikmin-randomizer/issues/128) (converter/animation/material pipeline), [#397](https://github.com/4laric/pikmin-randomizer/issues/397) (non-invincible cleanup/re-entry fixture).

## Per-family blockers

| Family | Current | Blockers to full implementation | Key issues |
|---|---|---|---|
| Ground invertebrates (#165) | Native display; Sokkuri + Armor source FSMs done (#407) | Source FSM for ElecBug, Imomushi, TamagoMushi and Hana (Sokkuri implemented in #407; Armor combat FSM + animation-event bite/eat in #407); animation-event execution (damage/drop/eat/spark/flick); ElecBug discharge + child variants; Imomushi climb/attack; Hana `ChappyBase` FSM + wake; TamagoMushi manager limits; corpse/carry/reward; Piklopedia; cleanup/re-entry; Armor `dmg1` receiver rule and bridge states | #165, #346, #388, #407 |
| Flying (#166) | Native display | Source Mar/Hanachirashi FSM; wind attack; flick/shake-off; corpse/reward; ShijimiChou runtime ownership (colour/nectar, owned by its family); blowhog btk/brk preservation; cleanup | #166, #348, #375 |
| Aquatic (#167) | Native display | Source FSM: Catfish (KochappyBase host + shadow), Tadpole (water leap/escape), Jigumo (owns `PanHouse`/nest), UmiMushi boss; shared `UmiMushi::Mgr` base/blind parameter split; water receivers; eat/flick; corpse/carry; cleanup | #167, #347, #374 |
| Cannon / projectiles (#169) | Native display | Projectile lifecycle: `Rock`/`Bomb`/`Egg`/`Stone`/`FminiHoudai` birth→homing→collision→damage; buried/burrow FSM; damage receivers; Gatling Groink pedestal + fire lives in the Groink lane; BombSarai projectile contract cross-ref; cleanup | #169, #198, #204–#210, #350 |
| Dweevil / elemental (#170) | Native display | Proxy damage path diagnosed and observed in #408 (queued damage requires active host updates); source Dweevil receivers remain unimplemented; elemental receivers/immunities (fire/water/gas/elec); BombOtakara payload; dweevil FSM/base sharing; fixed hazards `Hiba`/`GasHiba`/`ElecHiba` activation/emission; cleanup | #170, #349, #388 |
| Flora & Candypops (#171) | Native display + lifecycle (Pelplant proxy) | Pelplant poses convert (10/10) and a non-invincible Pelplant proxy passes spawn/draw/injected-death/cleanup/generator-respawn/tolerant-rebind-re-entry (#397, [doc](PIKMIN2_FLORA_LIFECYCLE_RUNTIME.md)); still open: source Pelplant FSM + pellet capture/release receptor + Pikmin transport/Pod reward, Candypop conversion/refund, plant/seed lifecycle, HikariKinoko shape-matrix type 1; native `pc_p2_batch2_rebind()` candidate (`opencode/p2-lifecycle-native` @ `5c9492c6`) pending export/#186 review | #171, #353, #397, #405 |
| Bulblax & larvae (#172) | P2 mechanics | King WarCry + cross-Emperor behavior, bomb-target determinism; Baby attack/capture; #239 host lighting/BTK + material fidelity; #128 animation bank; mixed-family performance; native export reconcile | #172, #217, #256, #289, #239 |
| Long Legs (#173) | Native display | Source FSM (Beady/Raging movement, stomp, knock-off), Man-at-Legs projectile + leg attacks; damage receivers; cleanup/re-load; leg performance | #173, #312, #397 |
| Snagret (#174) | Native display | Source `SnakeJointMgr` FSM (burrow/emerge, 5-way bite, `run1` jump) and `DangoMushi` roll/turn/flick; falling Rock/Egg spawner; White Flower Garden `mWFGHealth` override; corpse/carry; cleanup | #174, #351, #376 |
| Waterwraith / Titan (#175) | Native display | cleanup/re-entry (#397); Titan motion staging beyond 2/29 + unconverted lloozy model + ballistics/damage receivers + FSM host; BlackMan retained-asm FSM; Tyre roller lifecycle; boss performance | #175, #246, #352, #397 |
| Dirigibug (BombSarai) (#244) | P2 mechanics | Visual bank + `kamu_jnt1` capture-joint transform (#128 converter); multi-carrier pool/induction; persistence | #244, #128 |
| Antenna Beetle (Fuefuki) (#245) | P2 mechanics | Source `keyEvent`/animation bank (#128); follow-locomotion; true panic staging; claim persistence across day/cave | #245, #128 |
| Titan Dweevil lane (#246) | P2 mechanics | Motion staging 2/29, lloozy unconverted, damage receivers, FSM host, mixer performance | #246, #128 |
| Jellyfloat (#243) | Playable proxy | Install + arena (none yet), then native registration; capture/ingest lifecycle; kurage material/opacity | #243 |
| Bumbling Snitchbug / Demon (#215–#242) | P2 mechanics | Consolidate forced-drop/capture gates; native drop interruption + generation teardown; mouth attachment rig; captain bridge | #215–#242 |
| Beetles / Breadbug / Mamuta (#168) | P2 mechanics | Mamuta bury/99-cap and death/corpse runtime gates PASS ([PIKMIN2_MAMUTA_DEATH.md](PIKMIN2_MAMUTA_DEATH.md)); remaining: beetle reload/re-entry, contested cargo/nest ownership + Giant Breadbug scoring (breadbug), mamuta adversarial flick/territory + day/floor/save-load/Piklopedia | #219–#221 |
| Snow Bulborb (#120) | P2 mechanics | Reference lane; natural combat/carry/re-entry parity for the bulborb family remains | #120 |

## Cross-cutting blockers

1. **Source-behavior translation (largest).** Most families still use P1 proxy AI. Implementing each species' `*State.cpp` FSM, animation-event semantics and receivers is the bulk of remaining work — it is per-family and mostly unstarted.
2. **#128 converter/animation/material pipeline.** Blocks visual banks and fidelity everywhere: `.btk`/`.brk`, shape-matrix-type-1 (e.g. HikariKinoko), missing normals, material/TEV parity, retail event playback for unconverted clips. Singular animation scales are handled by the #405 opt-in policy (see [PIKMIN2_SINGULAR_SCALE.md](PIKMIN2_SINGULAR_SCALE.md)).
3. **Damage receivers and elemental routing.** Source receivers are not wired for most P2 species. #408 distinguishes queued proxy damage from source receiver implementation; its active-host damage and Pikmin immunity probes pass.
4. **Cleanup / re-entry fixtures (#397).** #397 now provides a non-invincible fixture; #422 observes Pelplant proxy forget/respawn/rebind. Other families and full scene teardown still require their own evidence.
5. **Rewards / corpse delivery.** P2 carcass, pellet drops, enemy-held treasure and Pod economy per family.
6. **Mixed-scene performance.** No family has frame/memory budgets at full roster density.
7. **Shared semantics review (#186).** Save/reward, captain state, generic damage/physics, actor lifetime and ID-conflict changes require focused integration review.
8. **Serialized build/export.** Maintained `native/build-randomizer` + `export_native_source.py` stay integration-owned; builders must use private environments (see [AGENTS.md](../AGENTS.md#build-isolation-required)).
