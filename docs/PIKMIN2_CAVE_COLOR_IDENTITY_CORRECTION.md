# Cave color identity correction v1 (#1125)

Owner: Codex through shared GitHub account `4laric`.

The authoritative cave-entry/native species namespace in `pc_p2_species.h` is
Blue=0, Red=1, Yellow=2. Cave startup restores these IDs through
`pc_p2_set_species`. The ordinary fresh stage default `[[1,0]] * 20` is already
20 Red leaves and must remain unchanged.

The preview generator writes 2 to the formation-state parameter and 1 to the
color parameter. The rejected interpretation confused state with color; it
does not establish a separate Red=2 cave-entry color namespace.

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

Fresh runtime verification passed in `output/cave-red-identity/`:

| Run | Observed native result |
| --- | --- |
| `run-supply-02` | Ordinary fresh entry: Red ID 1 count 20, Yellow ID 2 count 0, Blue ID 0 count 0. Five actual bud accepts with thrown color 1, five Blue sprouts, mixed recall/west-side movement, actual checkpoint exit 42 in 41.188 seconds. Transfer contains 15 species 1 / 5 species 0; bud usage 5. |
| `run-restore-02` | Actual transfer restores native 15 Red / 5 Blue, exact bud state and empty receipt ledger; exit 0 in 3.766 seconds. |
| `run-negative-02` | Forced captain-down guard, raw exit 86 in 0.954 seconds with no success marker. |

All runs used fresh arenas, the current overlay, a centered 960x540 window,
background SDL controller events and 60-second wall-clock supervision. Native
source pin `961244675a8ad1cd4e5c7bb0fb5f2bfb815d69fe` is clean on base
`2e6efbb1b841c1889d1bbd3b656e44ba6ae3629b`. Private build directory:
`output/native-cave-red-identity-1125-build`; production SHA-256
`100d07a7376e3dd56616878c991695e8f27c1c3655c326379252f8004fe96664`;
replacement-main fixture SHA-256
`0f78d27e421b5e71e03e0201a91f928a0953ff57baec4a03d35d9ca2a8bd8aae`.
Production build and no-work dry run passed; fixture provenance is retained.
Eight bounded cave Python tests pass. Source checks distinguish generator
formation state from color. Reassessment rejects the historical supply/restore
logs under the corrected Red criterion without changing them.

Preserved `run-supply-01` exited 42 after native acquisition but the runner's
post-check failed because fresh stage supplies no receipt sidecar. The runner
now initializes an empty ledger as ordinary supervision does; a new run verifies
the corrected path. This failed assessment is not silently converted to PASS.

The initial squad is the ordinary staged baseline, not natural population
acquisition. Input uses an SDL virtual controller; production bud auto-pluck
remains enabled, exit confirmation is bypassed, and only the captain crosses to
the exit while the mixed squad stays west. Manual pluck, mixed full-squad hazard
crossing, exit UI, second procedural floor descent, full supervisor recovery and
campaign continuity remain outside this slice.
