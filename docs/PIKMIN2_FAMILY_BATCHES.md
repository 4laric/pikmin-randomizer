# P2 enemy families — 3-batch work plan

One working session per batch, three families per batch. Each session drives its three families through the import-pipeline steps ([PIKMIN2_ENEMY_IMPORT_PIPELINE.md](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)) using the ownership rules of the 2026-09-13 revision (#186): family owners own extraction, conversion, native modules, narrow additive registration hooks, private builds and runtime evidence.

Live tracking: [PIKMIN2_FAMILY_STATUS.md](PIKMIN2_FAMILY_STATUS.md). Assets and engine runbook for every session: **[PIKMIN2_BATCH_RESOURCES.md](PIKMIN2_BATCH_RESOURCES.md)** — read it before starting (disc paths, P1 assets path, build commands, arena/preview launch, serialized-resource rules).

## Shared rules for every batch session

- Private disc copy: `output/pikmin2-runtime/pikmin2-source-test.iso` (GPVE01 rev 0). Never commit extracted assets, models, executables or saves.
- Shared, serialized resources: the maintained `native/` build and any real-GL runtime fixture. Private per-family worktree builds are fine in parallel; coordinate before touching `native/` or `engine/`.
- Never push native origin. Root source is exported with `py -3.12 scripts/export_native_source.py` and committed/pushed from the root repo.
- One issue per bounded slice; record progress, commit SHA, exact commands and raw evidence on the issue.
- Stay inside your three families' files. Do not edit another batch's or another family's modules.
- New files are family-prefixed (`experimental/pikmin2_<family>_*`, `tests/test_pikmin2_<family>_*`, `docs/PIKMIN2_<FAMILY>_*`, `native/pc_port/pc_p2_<family>*`).

## Batch 1 — Native-display trio

Families: **Aquatic** (#167/#347/#374), **Flying** (#166/#348/#375), **Snagret** (#174/#351/#376).

Start state: source contract + converted assets done; install + arena done; shared family-owned native registration candidate `pc_p2_batch3` exists in the private worktree `output/native-p2-batch3` (branch `opencode/p2-batch3-native`, commit `131f1c3f`), full `pikmin_pc` build validated.

Next steps:
1. Export `pc_p2_batch3` into root `engine/pc_port` + CMake/wiring and commit on a private worker branch; keep `native/` shared checkout untouched.
2. Per family, run a spawn fixture/arena with the installed `p2-<family>-actors.txt`/`-bank.txt` and capture `P2_BATCH3_BIND`/`P2_BATCH3_DRAW`, exact identities and effective XYZ.
3. Record the six arena gates; target **Native display**.

## Batch 2 — Hard lanes

Families: **BombSarai/Dirigibug** (#244), **Fuefuki/Antenna Beetle** (#245), **BigTreasure/Titan Dweevil** (#246).

Start state: native FSM/policy/probes and runtime evidence exist in per-family worktrees (`output/native-bombsarai-policy`, `output/native-fuefuki`, `output/native-bigtreasure`); install + arena Python layers added this cycle (commit `2d1838b`).

Next steps:
1. Integrate each family's native module into a shared registration pass (serialized), then build.
2. Run the lane's real-GL runtime fixture and record the gate table.
3. Close remaining lane-specific gaps (BombSarai kamu_jnt1/visual bank; Fuefuki follow-locomotion/claim persistence; BigTreasure motion staging beyond 2/29 clips).

## Batch 3 — Batch-2 visuals (north)

Families: **Ground invertebrates** (#165/#346), **Blowhogs/dweevils/hazards** (#170/#349), **Cannon larvae/projectiles** (#169/#350).

Start state: source contract + converted assets; install + arena and native registration `pc_p2_batch2` were produced by another inflight agent (`native` commit `219f7abc`), not yet exported to root.

Caution: another agent is/was mid-flight on these families — read [PIKMIN2_FAMILY_STATUS.md](PIKMIN2_FAMILY_STATUS.md) and confirm no live worker before starting.

Next steps: export `pc_p2_batch2` to root; run per-family spawn fixtures; record gates → Native display.

## Batch 4 — Batch-2 visuals (south)

Families: **Waterwraith/rollers** (#175/#352), **Flora & Candypops** (#171/#353), **Long Legs/Man-at-Legs** (#173/#312).

Start state: Waterwraith and Flora have source contract + install/arena under `pc_p2_batch2`; Long Legs has source profile + install/arena but no native draw path yet.

Caution: same as Batch 3 for Waterwraith/Flora.

Next steps: export/validate `pc_p2_batch2` for Waterwraith/Flora; add a native draw path for Long Legs (bind-pose meshes, not a `.mod` pose bank); run fixtures.

## Batch 5 — New families

Families: **Bulblax & larvae** (#172/#217/#120), **Jellyfloat** (#243), **Bumbling Snitchbug/Demon** (#215–#242).

Start state: Bulblax has assets/bank/behavior modules and `pc_p2_bulblax_visual` but no install/arena; Jellyfloat and Demon have native worktrees/branches but no install/arena pipeline entry.

Next steps: finish/verify source contract; add install + arena for each; add native registration; run fixtures. These are the least advanced — start at pipeline §1 for the weakest.
