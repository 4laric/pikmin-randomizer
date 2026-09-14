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
| `P2_SOKKURI_DEAD ... health=0 prior_health=%.1f` | Beside the existing death marker; `prior_health` is the health value one update before death, so a single-step injection (large prior_health) is distinguishable from a combat-culminated death (small prior_health). |

Natural-vs-injected is authoritative at the fixture level: the injected lifecycle
fixture emits `P2_LIFECYCLE_INJECT ... not_natural_combat=1`, and the module's
`P2_SOKKURI_DAMAGE`/`prior_health` report the combat facts independently. No
other family's module is touched; unregistered actors are no-ops.

## Observed behaviour (private injected lifecycle run)

The injected ground-lifecycle fixture ran on the current head and, before its
scheduled `mHealth=0` injection, the module logged `P2_SOKKURI_DAMAGE health=105.0`
— the starting squad **naturally attacked** the appearing Skitter Leaf (120 → 105)
with the death marker reporting `prior_health=105.0`. The lethal step itself was
still the fixture injection, so the run is labelled injected for the death gate;
natural combat **damage** is now separately observable.

## Root tests / validator

`experimental/pikmin2_ground_lifecycle_behavior.validate()` and
`tests/test_pikmin2_ground_lifecycle_behavior.py` now record
`P2_SOKKURI_DAMAGE` as a separate combat-damage gate and assert the death marker
carries `prior_health`. 114 family tests pass
(sokkuri/armor/elecbug/imomushi/hana/tamago/ground-lifecycle).

## Status

- Natural Pikmin-attack **damage** on the appearing Skitter Leaf is observed in a
  bounded run and is now distinctly logged. A natural **lethal** death (health
  fully drained by combat with no injection) still needs a run with no
  `P2_LIFECYCLE_INJECT` marker and a small `prior_health`; that stays open.
