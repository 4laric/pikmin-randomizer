# Native source provenance

`engine/` is a source-only snapshot of the isolated Open Nectar/BBFT-derived native checkout used for this randomizer, at native commit `9783304e`. It includes the inherited native compatibility and adapter code, standalone randomizer integration, health-gauge fix, guarded day-end saves, collection-check hooks, configurable starting Flarlic, and seeded per-color stats with weighted carrying. The native source history is retained locally; this directory is a snapshot, not a submodule.

Upstream: https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port (itself based on https://github.com/projectPiki/pikmin). The original local upstream boundary was `71db8405b78d5ae5765ac5d5f71d3305ca67c1ef`; upstream main through `18ce1303b488bc906721d1389143b65ace345695` is now merged and validated. Local BBFT-derived changes are included in the engine source; standalone play does not require the BBFT conductor or its separate repository.

Original `LICENSE.MD`, `LEGAL.md`, and per-file notices are preserved. The inherited engine README and BBFT notes describe upstream or historical workflows; the root README is authoritative for building and running this randomizer.

The export copies only Git-tracked text files, excluding the upstream portable archive, formatter executable, CI workflows and editor settings. It never copies extracted assets, untracked runtime files, saves, build outputs or nested Git history. `scripts/export_native_source.py` refreshes this snapshot from the maintainer's ignored `native/` checkout; it is not required to build a public checkout. Review deletions manually when refreshing a later snapshot.
