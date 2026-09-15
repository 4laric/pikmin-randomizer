# Floor 4 engineering assembly and native traversal (#330)

Owner: Codex using shared 4laric account. Root base is frozen #328,
`b177632fbb9a070b3f8380bb36135ba1eebaeb0f`. Source package #318 is read-only at
`output/p2-cave-lane/output/beasts318/final-a`. This milestone surveys floor4
geometry; it does not implement floor4 campaign entry or change native source.

## Assembly

The source floor4 pool supplies two rooms, a straight corridor and five item-cap
instances. This authored placement matches opposite source door directions and
positions, including the north room's offset door; no source edge is invented.

| Unit | Quarter turns | Center X/Y/Z |
|---|---:|---|
| room_mid1_6_tsuchi | 0 | 0 / 0 / 0 |
| way2_tsuchi | 0 | 0 / 0 / -680 |
| room_north3_1_tsuchi | 0 | 170 / 0 / -1020 |
| item_cap_tsuchi | 1 | 510 / 0 / -340 |
| item_cap_tsuchi | 1 | 510 / 0 / 340 |
| item_cap_tsuchi | 2 | 0 / 0 / 680 |
| item_cap_tsuchi | 3 | -510 / 0 / 340 |
| item_cap_tsuchi | 3 | -510 / 0 / -340 |

All eight cell footprints are nonoverlapping; all ports are paired. Seven seams
pass **273 floor probes**, sampling a 50-unit-wide, 60-unit-long strip. All **27
merged waypoints** reach the engineering return target. Directed source links
and prior source-backed local waypoint grounding are retained. The north room's
one-way route sequence is preserved, rather than repaired into all-pairs paths.
Geometry has 1,458 vertices, 2,495 triangles, 35 shapes and 18 textures.

The #318 floor4 source definition and prepared room hashes are checked against
the catalog; actual model archives and catalog sources are verified against the
disc. Two assembly builds produced six byte-identical files. Parameterization of
the shared builder preserves all six frozen #306 floor3 assembly files exactly.
Independent read-only review found no blocker in transforms, ownership, hashes
or default preservation.

## Native survey and boundary

Fresh engineering overlays restore ten Reds/ten Purples with mixed maturity and
health 0.625. Twelve controller goals walk from the mid room through both
corridor seams into the north room, then back. Both native runs passed with
native ground checks at every survey update, unchanged party/health/repairs,
zero Pokos, unchanged input/executable hashes and no transfer file.

The stage uses the existing **tutorial floor2 party-only loader**. Geometry floor4
is explicit in `survey.json`; `campaign_entry=false`, `native_ready=false` and
`party_restore_protocol_floor=2` remain. No ledger token or native floor4 profile
is accepted. Source enemies/plants, treasures, actors, carrying, floor4 checkpoint
and descent are omitted. Individual squad seam traversal is not asserted.
The inspected capture shows the room/party, approximate materials, legacy P1 UI
and camera occlusion; no visual-fidelity or natural-gameplay sign-off is claimed.

## API and reproduction

`experimental.pikmin2_beasts_floor4` provides:

- `build(iso, catalog, units, final_package, output)` → assembly report.
- `stage(assets, assembly, purple, pod, output, party)` → fresh UUID run directory.
- `fixture(source, output)` → fresh external C++ survey file.

All path arguments are `Path` objects. `party` follows the existing 20-member
Red/Purple `{health, squad}` contract. Use `final_package` at the #318 path above,
units `output/p2-mapcode0-batch/import`, the established Purple/Pod imports and
read-only P1 assets `C:/Users/alari/bbft/dist/cohesion/pikmin/assets`.

The external fixture links the **unchanged**, completed private native build at
`a9627bebf79445dfff0253992a1f72e0926d955a`. From the private root worktree, link a
generated fixture with `scripts.build_pikmin2_fixture`, source
`../native-beasts-floor3-failure`, build `../native-beasts-floor3-failure/build-failure`,
the exact native head above, and a fresh output directory. Launch the returned
stage through the shared runner:

```powershell
python -m experimental.pikmin2_beasts_floor3_runtime run --exe PATH_TO_FIXTURE --stage RETURNED_STAGE
python -m pytest -q tests/test_pikmin2_beasts_floor4.py tests/test_pikmin2_beasts_floor3_assembly.py tests/test_pikmin2_beasts_floor3_runtime.py tests/test_pikmin2_beasts_floor3_entry.py tests/test_pikmin2_beasts_floor3_failure_runtime.py
```

**15 tests and 38 subtests passed.** Coverage includes the offset room door,
five caps, nonoverlap, rejection of floor3 evidence for floor4 goals, bad source
package provenance, and prior entry/failure/survey regressions.

Assembly outputs: `output/floor4-330/{first,repeat}`. Manifest SHA256:
`b36841f817b7b68c4bd2edafd68098fd6c80eceaecde4169214faf4f6ee0bb66`.
Collision-bearing MOD SHA256:
`521503a0e7a9652eca625dd11989c8d52a556277a68f522e6309548714df3efe`.
All hashes and floor3 default comparison: `output/floor4-330/package-verification.json`.

Fixture SHA256:
`3531e450ffd1e6c44bab1698926785c21fd76c846c065b5bbd926bc981fde740`.
Provenance: `output/floor4-330/linked/provenance.json` (Ninja freshness observation,
not historical compilation certification). Native runs under `output/floor4-330/runs`:

| Run | Native log SHA256 |
|---|---|
| 0b328d59ecfc4940b2420289cd21285a | `469c596ebe992689f344adae6f0eb8e920975aecffc7ee3dbac2403abbf2ba42` |
| 29380d7b00d7413f9445495e4e427520 | `1f3ee662ecd770f3914d62f3c8199cb31268f83bd60e4f379ff4edac379fd226` |

Runtime hashes: `output/floor4-330/runtime-verification.json`. Submitted source,
builds and QA packages remain frozen. No shared native/build/save writes occurred.
