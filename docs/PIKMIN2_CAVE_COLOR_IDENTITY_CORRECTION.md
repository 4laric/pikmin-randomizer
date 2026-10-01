# Cave color identity correction v1 (#1125)

Owner: Codex through shared GitHub account `4laric`.

The authoritative cave-entry/native species namespace in `pc_p2_species.h` is
Blue=0, Red=1, Yellow=2. Cave startup restores these IDs through
`pc_p2_set_species`. The ordinary fresh stage default `[[1,0]] * 20` is already
20 Red leaves and must remain unchanged.

## Historical evidence correction

The frozen #1086 fixture counted `pc_p2_species()==2` while printing `red`.
Its actual start was 20 Yellow, conversion produced 15 Yellow / 5 Blue, and
its saved/observed restored squad contained 15 species 2 and 5 species 0.
Controller acquisition and those exact numeric persistence observations remain
evidence; their Red starting-baseline and Red/Blue adoption labels are incorrect.
Do not use the historical labels as proof of Red supply.

This correction supersedes the color/adoption descriptions in the historical
`PIKMIN2_CAVE_COLOR_SUPPLY.md`, fixture log markers, runner disclosures and #1086
reports. It does not rewrite their immutable bytes or integration receipt #1105.

Preserved #1086 pins and handoff:

- Root `3fa46abc7cd9cf54c8d8e4162f07c29de5049a04`, native
  `5c2943a9274473149de291e85d32ef3c1b4dcdd5`.
- `output/cave-color-supply/handoff-01/handoff.json`, SHA-256
  `34cf474169e671c9bfc66ee1704d8baabcad2bdbe757cde4c423231f990f0d0d`.
- `run-supply-04`, `run-restore-04`, `run-negative-04` remain unchanged.

False-positive #1121 attempted to change the already-correct default to species
2. PR #1122 and issue #1121 were withdrawn. Revert
`1dc211367c58d27da383a2b48df461845e64704f` leaves zero net production changes.
Its staging proof used circular color labels and observed no native actors.
Independent review `output/cave-entry-red/review-1121-01.json`, SHA-256
`e69e76838c6813659a80cf16cccf9c2640991ef4602e6ca5e67e45cfa74d5d14`, and
withdrawal `output/cave-entry-red/withdrawal-01.json`, SHA-256
`bf7f0cf8f71f9d0f79abc8fabce8f795571744e105c0c0933003fcc8638fb798`, preserve
the rejected claims and their disposition.

## Corrected verification

The fixture uses named native species constants. The runner exercises ordinary
fresh staging with no injected entry checkpoint, and assesses native Red ID 1
before input, thrown color 1, saved species 1 and restored species 1. Actor
positions, species and states are never changed by fixture input.

Fresh runtime verification is pending. No corrected Red acquisition PASS is
claimed by this source correction alone. Manual pluck, mixed full-squad hazard
crossing, exit UI, second procedural floor descent and campaign continuity
remain outside this slice.
