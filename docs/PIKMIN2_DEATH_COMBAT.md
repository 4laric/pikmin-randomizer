# P2 combat availability during death (#1064)

Implementation owner: Codex through shared GitHub account `4laric`.

Source-bound P2 Teki stop being combat targets when health reaches zero or their
host death state starts. Existing Pikmin detach, later object/mouth attachments
are refused and attacks cannot queue damage. `isHostAlive()` preserves the alive
option needed for death animation, family registration and corpse production.
Unbound P1 Teki retain their original alive-option semantics.

## Reference and integration

Read-only reference: `native/pikmin2-research`, roster reference revision
`632af93787b9c95b63f0c13be32b161375ce3a96`. P2 `EnemyBase::deathProcedure` calls `setAlive(false)`
at `src/plugProjectYamashitaU/enemyBase.cpp:2525-2529`; P2 `ActAttack::exec` exits
on a nonliving target at `src/plugProjectKandoU/aiAttack.cpp:192-195`.
KurageState.cpp:75, HoudaiState.cpp:36 and BigFootState.cpp:35 invoke that procedure.

The shared port query is `BTeki::isAlive`. It now checks the production P2 source
registry and health/death state. `InteractAttack::actTeki` and direct `BTeki::interact`
refuse post-death attacks; `Creature::startStick` rejects new Pikmin attachments.
`startStickMouth` handles death-race refusal before its broken-link error path.
`BTeki::update` detaches Pikmin before and after species ticks, saving the next
intrusive-list link, using mouth/object release as appropriate and preserving
non-Pikmin attachments.

Kurage/OniKurage revoke, Breadbug/Giant Breadbug drawing and death bookkeeping,
Antenna Beetle drawing, Titan setup and Bulborb off-grid updates use host lifetime
where a combat query would prematurely cut off death processing. The admitted
Wtank OWN draw branch already handles its FSM clip before the legacy proxy fallback;
the retired proxy branch is outside the current admitted pool and was not edited.

## Validation

Native candidate: `e3892778ea9668d4fd0d9bb396036b6594de371f`, clean private `output/native-death-1064`.
Root pool/tooling pin: `e77be0b39e5d8d194f2c0eadb0f353f6f1af7925` (42 admitted identities).
Private build: `output/native-death-1064-build`, Ninja and MinGW GCC/G++, six jobs.
Final production SHA-256: `8e9bf1d3456400451ce59e77457b8df50208901445b6e865b3604d5a280d9a79`.
Final dry run: `ninja: no work to do.` Per-attempt commit, executable hash and dry
run evidence is retained under `output/codex-1064-build-attempt1` through `attempt5`.

Engine-linked headless fixture: `native/tools/test_p2_death_combat.cpp`.
Fixture SHA-256: `7938c92ad6acc11db9de08cdb71abb0107906ddcee5b554b3d8516370d43c4a8`.
Built provenance: `output/codex-1064-fixture3/provenance.json`.
Run: `output/codex-1064-headless-attempt2.log` and
`output/codex-1064-headless-attempt2-result.json` (42/42 PASS).

Each row binds a constructed Teki through the production source registry and
uses concrete Piki subclasses with scene-independent render/message callbacks.
Injected health and host death state verify targeting availability, wrapper/direct
attack rejection without stored damage, late object/mouth refusal, detachment of
two Pikmin including mouth-flag clearing, retention of another attachment,
idempotent release, revival/slot reuse and unchanged unbound P1 semantics.
The first run failed because the fixture omitted scene-initialized attachment
fields; its failure log is preserved, as is the first rejected compile attempt.

These rows audit the shared host contract. They do not run each complete species
FSM, natural combat, rendered death clips, corpse delivery, teardown/re-entry or
a full campaign. Those gameplay gates remain UNTESTED by this fixture.

## Fixture baseline

Observed PASS in fresh private `output/codex-1064-baseline-arena1`, regenerated
with the current `preview_pikmin2_room.overlay` and its `ensure_pikmin_squad`.
The generated stage contains 20 Red records at the guide default positions.
The custom startup mirrors production window sizing/centering after settings reload.

Observed client size 960x540, position (373,263), display bounds (0,0,1707,1067).
Observed 20 live reds, captain HP 100, Walk state and five active gameplay frames,
without immediate extinction. The bounded canonical fixture runner exited 0 in
12 seconds. Forced captain-down exited 86 and emitted `P2_FIXTURE_CAPTAIN_DOWN`
without a baseline PASS. The guard is unprotected and does not change health.

Evidence: `output/codex-1064-baseline-arena1/arena.json`, `native.log`,
`run-inputs.json`, `run-result.json`; `output/codex-1064-baseline-build2/provenance.json`;
`output/codex-1064-baseline-negative.json` and its log. Baseline executable SHA-256:
`3a6753e85756c9c95cc5c991bd5eaa0f77ea2692ceca274336d3bebb56c1d8ca`.
The locally generated baseline driver is `output/codex-1064-baseline.cpp`.
This establishes fixture startup adoption, not species combat or corpse gameplay.

## Per-admitted-species shared-host audit

| Source | Species | Shared host regression |
|---|---|---|
| 2 | Red Bulborb (`Chappy`) | PASS |
| 15 | Cloaking Burrow-nit (`Armor`) | PASS |
| 25 | Watery Blowhog (`Wtank`) | PASS |
| 26 | Water Dumple (`Catfish`) | PASS |
| 27 | Wogpole (`Tadpole`) | PASS |
| 28 | Anode Beetle (`ElecBug`) | PASS |
| 30 | Empress Bulblax (`Queen`) | PASS |
| 31 | Bulborb Larva (`Baby`) | PASS |
| 32 | Bumbling Snitchbug (`Demon`) | PASS |
| 33 | Fiery Bulblax (`FireChappy`) | PASS |
| 34 | Burrowing Snagret (`SnakeCrow`) | PASS |
| 35 | Spotty Bulbear (`KumaChappy`) | PASS |
| 38 | Breadbug (`PanModoki`) | PASS |
| 40 | Giant Breadbug (`OoPanModoki`) | PASS |
| 41 | Antenna Beetle (`Fuefuki`) | PASS |
| 43 | Hairy Bulborb (`YellowChappy`) | PASS |
| 44 | Dwarf Orange Bulborb (`BlueKochappy`) | PASS |
| 53 | Emperor Bulblax (`KingChappy`) | PASS |
| 54 | Mamuta (`Miulin`) | PASS |
| 57 | Lesser Spotted Jellyfloat (`Kurage`) | PASS |
| 58 | Careening Dirigibug (`BombSarai`) | PASS |
| 59 | Fiery Dweevil (`FireOtakara`) | PASS |
| 60 | Caustic Dweevil (`WaterOtakara`) | PASS |
| 61 | Munge Dweevil (`GasOtakara`) | PASS |
| 62 | Anode Dweevil (`ElecOtakara`) | PASS |
| 63 | Hermit Crawmad (`Jigumo`) | PASS |
| 66 | Man-at-Legs (`Houdai`) | PASS |
| 67 | Bulbmin (`LeafChappy`) | PASS |
| 68 | Mitite (`TamagoMushi`) | PASS |
| 69 | Raging Long Legs (`BigFoot`) | PASS |
| 70 | Pileated Snagret (`SnakeWhole`) | PASS |
| 71 | Ranging Bloyster (`UmiMushi`) | PASS |
| 72 | Greater Spotted Jellyfloat (`OniKurage`) | PASS |
| 73 | Titan Dweevil (`BigTreasure`) | PASS |
| 75 | Armored Cannon Beetle Larva (`Kabuto`) | PASS |
| 76 | Dwarf Bulbear (`KumaKochappy`) | PASS |
| 78 | Gatling Groink (`MiniHoudai`) | PASS |
| 79 | Skitter Leaf (`Sokkuri`) | PASS |
| 84 | Creeping Chrysanthemum (`Hana`) | PASS |
| 93 | Volatile Dweevil (`BombOtakara`) | PASS |
| 94 | Segmented Crawbster (`DangoMushi`) | PASS |
| 101 | Toady Bloyster (`UmiMushiBlind`) | PASS |
