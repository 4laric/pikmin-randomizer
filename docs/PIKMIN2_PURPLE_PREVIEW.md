# Experimental Purple Pikmin

Implementation owner: Codex, assigned through 4laric in [#113](https://github.com/4laric/pikmin-randomizer/issues/113). Native source: `6a1c352be46e`. This is the first Purple increment of the separate Pikmin 2 experiment, outside the Pikipelago v0.1 release.

## Scope

The opt-in room preview starts with twenty Reds, two Violet Candypop stand-ins and the Spherical Atlas. Each flower converts five Pikmin total, including across partial batches. It closes after five seconds of interaction or when full. Replacement sprouts are allocated before consuming the original Pikmin; allocation failure releases the original. Plucking preserves an explicit Purple identity. There is no Purple Onion.

Purples use the actual locally extracted P2 model and leaf/bud/flower attachments. Twelve immutable poses each are sampled from the source idle, walk and attack animations, with their original clip durations. Other states currently use the idle pose; animation blending, throw/death/pluck motions and source animation events are not implemented.

The source disc parameter files specify movement factor 0.8, carrying speed power 0.6, attack power 20 and throw height 49. These retail values differ from several C++ constructor defaults. Purple carrying strength is ten, independently of speed and occupied carrying slots. The Atlas is equipment `map01` from `us/item_config.txt`, worth 200 Pokos and requiring 101 strength with 101 available slots. The native slot bitset now accommodates 128 physical slots.

The preview scales P1's carry-stall threshold for these slower loads. A stationary load still times out. This reduces premature drops, but the final native run still dropped and automatically reacquired the Atlas once on the Pod approach; smooth heavy-haul completion remains a polish item. Carried captains are explicitly recognized by the Pod and return without money, repairs or seed production.

Purple is its own held-selection and disband class. Legacy three-color arrays still use a Red compatibility index, with a separate species flag on active Pikmin and sprouts. Purple does not inherit Red fire immunity. This is a bounded preview representation, not the final campaign storage schema. The window title reports the Purple field count; the original HUD still displays the legacy color icon.

## Local preparation

Use a user-owned supported Pikmin 2 disc image and the existing P1 assets; extracted content stays local.

```powershell
python -m experimental.pikmin2_purple --iso <local-disc.iso> --output <purple-output>
python -m experimental.pikmin2_pod --help
python -m scripts.preview_pikmin2_emergence --help
```

The preview command accepts `--purple <purple-output>` together with `--pod <atlas-output>`. Its asset manifests record source hashes. Every launch creates a disposable run directory; the Pod receipt ledger is not a cave or squad save. Automated native fixtures force SDL's dummy audio backend while the separate continuous-tone report [#116](https://github.com/4laric/pikmin-randomizer/issues/116) is investigated.

## Remaining acceptance

- Purple landing damage, impact/stun, source throw physics beyond height, and complete animation coverage.
- Ship inventory, color-specific population UI and checkpoint/descent/reload preservation, coordinated with #112.
- Source Violet flower model, effects and exact P2 flower behavior; current flowers are tinted P1 actors.
- Source treasure collider dimensions and full cave roster/layout integration.
- Manual controller playthrough, natural recruitment and durable campaign acceptance. Automated transport assignment does not substitute for these.

The first increment does not close #113 or enable Purples in normal P1/AP seeds.

## Snow and carry-display polish (#119)

Native `85074274` removes the PC carry gauge's 99 clamp and centers all digits. This changes presentation only: the Atlas still requires 101 strength. Console matching paths retain their original behavior.

The static importer now preserves source blend/depth/alpha state, draw categories and hierarchy order. For recognizable untransformed UV0 diffuse stages it uses the diffuse texture instead of the first input, which can be a procedural noise texture. The snow's view-dependent sparkle calculation is still omitted; this remains an approximation of original J3D shading. Terrain geometry and collision are unchanged. Assembled floors retain these per-instance material settings and order.

Updated local launcher: `output/pikmin2-polish119/Play.cmd`; the previous Purple preview remains available. Production executable SHA256: `E181BC6A272646EF8935E3E468BDAC0BAB4306647BE196F23490E7D44B8FD843`.

Validation: Windows production/fixture builds; native flare UV/count/centering assertions at 0, 9, 10, 99, 100, 101 and 1000; Purple conversion, 100/101 strength boundary and 200-Poko delivery; ordinary room movement, combat and corpse transport regression. Final snow captures before/after camera-follow movement were inspected in `output/pikmin2-polish119/final-render/89f148f1bccd4843a491ddc112318628`. All eight unit conversions preserve geometry/texture chunks and byte-identical collision; only material and joint draw-order chunks differ. Earlier diagnostic renders exposed missing snow and were superseded by diffuse-stage selection. Full physical camera-sweep acceptance remains for playtesting.

## Validation

- 49 focused Python tests passed, including BCA frame sampling, rejected scale/skeleton/truncation, source color/stats, Atlas equipment catalog lookup and local Violet generator preparation. Tests requiring user-owned assets skip in a source-only checkout.
- 13 existing color-stat/progressive-stat tests passed.
- Windows production build and the isolated native fixture build passed.
- Native run `1ad07e5156c348638f5c4e6ca84cbe77` completed real throws, partial flower batches, ten Purple sprouts, captain plucking plus automatic plucking, twenty conserved Pikmin, distinct selection identity, physical slot 100, strength 100 failing to lift 101, mixed strength 101 succeeding, and Atlas delivery for 200 Pokos without P1 repairs. A direct carried-captain return-hook check preserved that balance.
- The ordinary no-Pod regression `25172743294c4830aca725116c200456` passed movement, treasure carrying, combat and corpse delivery with the Purple hooks disabled.
- Native captures were inspected for the Purple body, source leaf attachment and violet sprouts. Materials remain simplified and notably flatter than P2's original shading.

The fixture assigns transport actions explicitly and parks only the captain away from the cargo route after testing plucking. It does not teleport carriers or treasure. Final run `219f70f5dc70402f8afc5a0c020472e8`, using native `6a1c352be46e` and the speed-scaled detector, also passed the complete loop and captain return hook. It recorded one drop/reacquisition on the approach before successful delivery. Logs, binaries and captures remain in ignored local output directories.

Final Python regression: 156 tests and eight subtests passed (output/pikmin2-polish119-tests-final.log).

Subsequent #112 integration: [two-floor cave checkpoints](PIKMIN2_CAVE_CHECKPOINTS.md) now persist squad identity, maturity, health and receipts together at floor boundaries. Standalone preview launchers retain their earlier save behavior.
