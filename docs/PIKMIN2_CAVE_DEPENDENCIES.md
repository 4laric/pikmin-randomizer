# Cave dependency manifests (#129 / #154)

Run after producing a general source cave catalog:

```powershell
py -3.12 -m experimental.pikmin2_cave_dependencies --catalog <catalog.json> --iso <US-disc.iso> --source native/pikmin2-research --output <new-directory>
```

`dependencies.json` joins every floor's ordinary enemies, nonempty cap enemies,
held treasure, loose treasure, gate definitions, unit pool and exit flags into a
source dependency manifest. Definition IDs are stable (`forest_1:definition4:enemy:0`)
and remain distinct from runtime actor or collectible receipt IDs. Multi-floor
ranges remain one source definition rather than silently inventing instances.

The enemy table's model, animation, animation-manager, texture, parameter,
collision and petrification resource-family overrides are retained. Empty aliases
resolve to the enemy's own family. Parent managers and spawned-helper dependencies
are closed transitively. `EFlag_HasNoInfo` is reported independently of
`EFlag_CanBeSpawned`; no-info does not mean nonspawnable. Nonspawnable types may
appear as managers, but direct roster references to them are rejected. Closure
is conservative: a Queen's Baby dependency does not mean every Queen encounter
spawns larvae, and helper quantities are not encounter counts.

The manifest inventories existing files in these resource families, explicitly
listing model archives and external texture files as material dependency
candidates. It does not decode their materials or assert converter/runtime
support. Unit candidates list model/text archive paths. Every cargo archive and
specific model member is checked. JKRArchive::CArcName::store lowercases lookup
names: source `gum_tape_S.bmd` therefore resolves to actual `gum_tape_s.bmd`, with
both requested and resolved names recorded. Missing/ambiguous members reject.

Inputs are tied to the earlier catalog's disc and enemy-table hashes. Unknown
references, stale source inputs, malformed table metadata and duplicate unit
candidates fail closed. Output directories cannot be reused. Assets remain on
the local disc; only metadata is written.

## Audit evidence

All14retail caves /105floor definitions pass. The shared resource index contains
432 entries, including167unique unit candidates. Hole of Beasts (`forest_1`)
correctly adds cap Egg/TamagoMushi dependencies and the Queen-held `radar_a` cargo
on floor5; manager-only Pom appears through BlackPom inheritance. UmiMushiBase is
also classified as a nonspawnable manager in other cave closures.

Six focused dependency/catalog tests and thirteen parser subtests pass. Two real
disc audits produce byte-identical dependency manifests. Source:
`src/plugProjectYamashitaU/enemyInfo.cpp`, `src/JSystem/JKernel/JKRArchivePri.cpp`,
the prior cave catalog and the disc's US runtime pellet catalog.

This is preparation for selective extraction and runtime actor loading. It does
not implement source room selection, selected placements, gate/exit actors,
complete enemy behavior or material conversion. Both roadmap issues remain open.
