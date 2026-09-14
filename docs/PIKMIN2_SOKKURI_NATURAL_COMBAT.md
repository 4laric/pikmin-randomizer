# Sokkuri (79) natural-combat death observability

Issue [#165](https://github.com/4laric/pikmin-randomizer/issues/165), parent
[#407](https://github.com/4laric/pikmin-randomizer/issues/407). Follows
[the Sokkuri native slice](PIKMIN2_SOKKURI_NATIVE.md).

## Gap

Before this slice the Sokkuri module could not tell a **naturally fought**
death (real Pikmin attack damage reduced `mHealth` through positive values) from
a **fixture-injected** death (a single write `mHealth=0`). Both paths emitted
only `P2_SOKKURI_DEAD ... health=0`, so a downstream accepting agent (lane 33)
could not distinguish natural combat evidence from injected diagnostics.

## Change

`pc_port/pc_p2_sokkuri.cpp` (native `0ec890de`) now tracks the previous frame's
health per registered actor and emits two additive, read-only markers:

| Marker | Meaning |
|---|---|
| `P2_SOKKURI_DAMAGE generator=%u source_id=79 health=%.1f` | An incremental, still-positive health decrease — real attack damage from thrown/retaliating Pikmin. |
| `P2_SOKKURI_NATURAL_DEATH generator=%u source_id=79 natural=0/1` | Emitted beside `P2_SOKKURI_DEAD`; `natural=1` when at least one `P2_SOKKURI_DAMAGE` was observed before death, `natural=0` otherwise (single-step injection). |

A single injected jump `120 -> 0` never passes through a positive health value,
so `naturalCombat` stays false and the death marker correctly reports
`natural=0`. No other family's module is touched; unregistered actors are
no-ops.

## Root tests / validator

`experimental/pikmin2_ground_lifecycle_behavior.validate()` and
`tests/test_pikmin2_ground_lifecycle_behavior.py` now require the injected run
to report `natural=0` (the death is honestly labelled non-natural) and record
`P2_SOKKURI_DAMAGE`/`natural=1` as the separate natural path. 114 family tests
pass (sokkuri/armor/elecbug/imomushi/hana/tamago/ground-lifecycle).

## Status

- Natural Pikmin-attack death for a *harmless* disguised Skitter Leaf is not yet
  observed in a bounded run: it needs real thrown-Pikmin input and a live GL
  fixture (host capacity), and is reported by the runtime run as natural or
  injected, never assumed.
- The marker fires for the ElecBug (28) reverse path too if adopted there; this
  slice scoped it to Sokkuri only.
