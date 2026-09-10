# Pikmin Randomizer development track

Independent source snapshots for the Pikmin Randomizer task, separated from ongoing BBFT work on 2026-09-10. Both repositories use branch `codex/pikmin-randomizer`; existing Git history and uncommitted source changes were preserved. `snapshot.json` records source commits and SHA-256 hashes. No original checkout was modified.

## Working directories

- `native/`: Open Nectar native PC port, including Pikmin adapter and native progression hooks. See `native/BBFT.md` for current behavior and build instructions.
- `bbft/`: preserved BBFT logic, conductor, transport and tests needed by the current adapter. This is an isolated dependency snapshot, not yet a standalone Pikmin AP world.

Use these copies for this task. They have independent Git indexes, working files and branches. The local clone origins point to the original source repositories for provenance; do not push back to them. Integrate selected changes deliberately after review.

## Inherited progress

Full progression mode starts day two in Forest of Hope with red Pikmin. It reports 28 ship parts outside Impact Site plus Yellow and Blue Onion discovery, gates later areas, and supports received color unlocks. BBFT shared-capability mode maps blue unlock to Zora Tunic and gates bomb rocks with Bomb Bag. Route logic includes refined color requirements and compatibility for earlier seeds.

Key files:
- `native/pc_port/pc_bbft.cpp` and `.h`: native adapter.
- `bbft/worlds/bbft/pikmin_progression.py`: dependency-free part catalog and requirements.
- `bbft/worlds/bbft/test/test_pikmin_routes.py` and `test_pikmin_skip_tutorial.py`: AP integration coverage.
- `bbft/scripts/test_pikmin_progression.py`: opt-in native smoke.

## Next implementation milestone

The standalone AP world/session runner now exists; see DEVELOPMENT.md. Next, audit actual part-placement slots and carry routes, implement validated relocation, and finish native campaign resume. Current standalone defaults are the Forest of Hope day-two profile, 25 repair rewards plus five unlocks, and a repeating safe day-29 calendar. Physical sunset and complete-seed acceptance remain pending.

This separation does not claim a standalone playable randomizer. Native collection, save/reconnect behavior and route assumptions still require gameplay validation. Previous build outputs, assets, saves, generated seeds and ignored evidence logs were not copied. Build into a new directory under `native/`; never reuse the original CMake cache. Do not run inherited launch scripts until their absolute paths and output/save directories are adjusted to this workspace. AP integration tests need an isolated Archipelago setup; do not repoint the shared installation's world link.

## Specification and issue tracking

Private planning repository: https://github.com/4laric/pikmin-randomizer

Implementation spec: [SPEC.md](SPEC.md). Roadmap: https://github.com/4laric/pikmin-randomizer/issues/1 . Eleven scoped implementation issues (#2 through #12) contain dependencies and acceptance criteria. The GitHub repository currently holds planning documents only; native and BBFT source snapshots remain local. Local issue links are recorded in `github-issues.json`.

## Standalone implementation

See [DEVELOPMENT.md](DEVELOPMENT.md) for the implemented solo/AP foundation, local build, tests and launch commands. Physical placement is still pinned pending route validation; exact native campaign resume is not yet implemented.
