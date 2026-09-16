# Pikipelago: additional Challenge layouts (post-v0.1)

Issue #100. This is an experimental first slice, not part of v0.1 and not yet an AP option. It reuses the Challenge layouts as additional story destinations; the separate timed/scored Challenge campaign remains #52.

## What works in this branch

The experimental registry contains ten distinct keys: campaign and challenge variants of impact, forest, navel, spring and trial. Native area IDs remain 0–4 because several engine arrays depend on that range. A level key must therefore accompany an area ID in future checks and save routing.

The preview selects the actual `stages/chal0.ini` through `chal4.ini` StageInfo nodes by filename. These are separate native list entries (16–20 in the audited retail stage list). It stays in story mode and starts with all three Onions and 20 stored Pikmin per color for exploration. It uses neither an AP connection nor campaign check observations. Each launch has a fresh output directory and private card path. No release defaults or existing seed contracts change.

All five use the same terrain model as their campaign counterpart, with different generator placements. Each Challenge directory has default.gen and plants.gen, with no init/day-specific generator files. Audited day multipliers are Impact 0.8, Forest 1.4, Navel 1.2, Spring 1.4 and Trial 1.0. These are file values, not validated real-world duration or route feasibility estimates.

## Try a layout

Build the native executable from this branch, then run from the repository with the MinGW runtime on PATH:

```powershell
python scripts/preview_challenge_level.py --assets C:/path/to/assets --exe native/build-stats/bin/nectar.exe --level challenge:navel
```

Other level keys: challenge:impact, challenge:forest, challenge:spring, challenge:trial. Close the game after exploring; persistent campaign travel/save/resume is not supported by this preview. It intentionally does not replace the current playtest launcher.

To audit local assets without launching:

```powershell
python scripts/preview_challenge_level.py --assets C:/path/to/assets --audit output/challenge-assets.json
```

Only paths, hashes and metadata are written to the audit. Extracted assets are never bundled or edited.

## Remaining implementation batches

1. Ten-destination navigation: extend the five-button map selection, append five AP access items, negotiate a new capability, carry a level key through launch and travel. Retain existing stage IDs for native terrain/AI dispatch. No challenge start until routes are audited.
2. Independent persistence: expand the five cache slots and update card format/validation, stage flags, obstacle state and resume destination. Round-trip campaign Navel to Challenge Navel and back across saving/reload without sharing completion. Do not merely increase the enum count; current arrays also encode campaign-specific behavior.
3. Checks and logic: inventory actual generators/resources/obstacles, assign new location IDs, qualify bestiary sources by level, and decide which population checks remain global. Do not fabricate ship parts or copy campaign route assumptions into layouts that lack them.
4. Enemy randomization and reachability: add Challenge generator sources to the seeded placement model; audit hazards, carrying routes and guaranteed population production before filling progression.
5. Full playtest: travel through all ten destinations, save/reload both variants, verify AP reconnect and check deduplication, then publish a separate post-v0.1 seed.

The native startup smoke test verifies the selected stage filename, loaded Challenge generator and several rendered frames for each layout. It does not establish save correctness, all obstacles, enemy AI or complete playability.
