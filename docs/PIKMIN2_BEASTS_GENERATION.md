# Hole of Beasts Violet generation gate (#269)

Implementation owner: Codex using shared GitHub account 4laric, cave lane under
#129/#154. Dependent branch `codex/p2-beasts-violet-gate` follows frozen #267.
Native fixture-only commit: `2abe125e7a5d0e25f36a6cfa81e252d7666012e4`.

## Source contract and implemented scope

Local read-only decomp `native/pikmin2-research/src/plugProjectNishimuraU/PomMgr.cpp`,
`Game::Pom::Mgr::birth`, lines 31–46, checks story mode and being inside a cave.
For BlackPom, when the zero-based floor index is below 2 or the cave ID is
`t_01`, `GameStat::getAllPikmins(Purple)` plus saved cave Purples at least 20
suppresses birth. Hole of Beasts floor 2 has index 1, so the gate applies.
Source-file SHA256:
`28a861eadf5a8f7351970eda41ac8479379e06b01e5d98a9f326b61f18512bd5`.
The prior parameter audit records five slots per Violet; it remains unchanged.

This implementation is deliberately scoped to story `forest_1` floor 2. It
does not generalize the rule to other caves, species or modes. The host staging
function accepts an explicit nonnegative signed-32-bit integer snapshot of
global-plus-cave Purple population, keeps IDs 62000/62001 with five slots each
below 20, and removes both generated actors at or above 20. Both source spawn
candidates and their provenance remain in the readiness report even when no
flowers are selected. A count of 19 may legitimately produce ten new Purples:
the gate is a birth-time decision, not a conversion-time ceiling of 20.

The versioned generation metadata records the caller-supplied snapshot, selected
stable IDs, budgets and source-rule scope. `generation_identity` fingerprints
that context; it is not a complete campaign/seed identity. The readiness hash
and per-file input hashes bind the tested geometry, generators and other inputs.
Changing the snapshot changes its identity even if the actor selection is the
same. Nothing writes or migrates a campaign save.

The native fixture version-2 marker includes the declared count, independently
derives the expected flower count and compares it to living native actors. Its
log echoes the **declared** count; it does not measure native global storage.
`native_global_population_verified=false` and the caller-context label remain
in acceptance. The fixture always starts with twenty engineering Reds; any
declared stored Purples are not materialized in this test. A future campaign
adapter must obtain and persist the real birth snapshot from authoritative
state before this can be considered campaign integration.

## Runtime behavior and compatibility

Below the threshold, the existing native throw/conversion/pluck checks remain:
both source-position flowers, five conversions per flower, ten sprouts, then
ten Reds and ten Purples with unchanged repairs and zero cargo/receipts.
At/above the threshold, the fixture observes zero flowers, twenty Reds, zero
sprouts/cargo/rewards for 300 update frames and checks unchanged repairs.

The runner requires `--global-purple-count`; it never silently uses zero when
that input is absent. It rejects malformed context, wrong context fingerprints,
unexpected selected IDs, mismatching native declarations and any conversion,
throw, flower or reward evidence in a suppressed run. The generator decoder
checks the expected zero/two flower count and exactly one of each anchor.

Old prepare-only calls without context retain policy `P2_BEASTS_FLOOR2_PREPARE_3`
and both flowers, with an explicit unknown-context limitation. Explicit-context
calls use `P2_BEASTS_FLOOR2_GENERATION_1`. No prepared file is rewritten in place.
The native fixture still understands the historical version-1 marker; current
runner acceptance requires version 2 evidence and rejects a stale executable.

## Reproduction

From `C:/Users/alari/pikmin-randomizer/output/p2-cave-lane`:

```powershell
python -m experimental.pikmin2_beasts_floor2_runtime --root ../.. `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --exe output/beasts269-final/linked/fixture.exe `
  --output output/beasts269-repro --global-purple-count 19
```

Repeat with `--global-purple-count 20` for suppression. The `--root` prepared
inputs and silent, fresh UUID runtime staging are as documented for #263.
Both executable and all staged overrides/configs must remain hash-identical
during each run. `acceptance.json` carries the native observations, input hashes,
context and log/capture hashes. Ordinary preparation remains `native_ready=false`.
`output/beasts269-final/linked/provenance.json` records the private native source,
compiler/link inputs and two successful no-work freshness checks.

## Validation and remaining work

45 focused tests and 60 subtests pass, covering threshold values 0/19/20/21,
the maximum valid count, missing/invalid context, omission of flowers, conflicting
native evidence, existing conversion/entry references, generator pose, fixture
linking and cargo-free native policy. No shared gameplay source changed.

Final fixture SHA256:
`532a23d589b624a65644adc334bdaf12d64f74a19900bcdde78514debe694fd2`.
All three fresh final native runs passed:

| Run under `output/beasts269-final/` | Declared count | Observed result |
| --- | --- | --- |
| `count19/99b0e7b09e324c50b52b2706559d7979` | 19 | Two flowers; five conversions each; ten Reds plus ten Purples |
| `count20/4a4f21422a97454c84ea6a26e332689e` | 20 | No flowers; twenty Reds unchanged for 300 update frames |
| `count20/8d49ab600f3548a8a1f0c003cc1a20f2` | 20 | Same suppressed result on repeat |

All runs had zero cargo/rewards, unchanged repairs, and unchanged executable
and staged-input hashes. The repeated count-20 readiness SHA256 is identical:
`5b767a933022790ab526a04832e37e9f6dd49cfe1922af92a7f62afcd891f4ce`.
Count-19 readiness SHA256 is
`25e1a8a009a5426f4505fb16cf0fda3514182eff0317a793a991b081a0d97a85`.
The run logs and captures have individual hashes in their acceptance records.
Earlier probes at 19 and 20 also passed and remain in `output/beasts269-probe`;
the final results above use the committed native source.

Real generation/save context, durable conversion witnesses, floor descent,
Egg/plant content, source yaw application, retail room generation and full P2
Candypop behavior remain open. This is a source-backed host generation policy
with native actor validation, not a complete cave or population/save system.
# Native witness follow-up

The current runtime CLI additionally requires [per-conversion native diagnostics](PIKMIN2_VIOLET_WITNESSES.md)
from #276. Use its executable for new acceptance runs; earlier #269 evidence
remains tied to the executable and runner revision recorded below.
