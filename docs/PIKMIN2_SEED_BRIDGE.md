# P2 seed selection and native manifest bridge (lane 03, #439)

Opt-in, versioned P2 enemy choices with deterministic native actor bindings.
Consumes the lane 02 roster (#438). Placement belongs to lane 04, content staging
to lane 05, reward semantics to lane 06. This lane owns shared seed/options and
the protocol adapter.

Status: **design slice + tested adapter**. Runtime acceptance needs lanes 02/04/05
and at least one eligible family; no gameplay PASS is claimed here. Ordinary P1
seed generation and legacy seeds are unchanged.

## Module

`experimental/pikmin2_seed_bridge.py`

- `resolve_layout(seed, slot, targets, cohort, roster=None)` → deterministic layout.
- `validate_layout(layout, roster=None)` → raises `SeedBridgeError` on any mismatch.
- `build_bootstrap(layout)` / `parse_bootstrap(text)` → emit/parse the native line.
- `bootstrap_for_manifest(manifest)` → the line for a manifest, or `""` for legacy.
- `roster_revision()` → hash of the current roster's identity set.

## Layout record

```json
{
  "version": "p2-enemy-layout-v1",
  "roster_schema": "p2-enemy-roster-1",
  "roster_revision": "<64-hex>",
  "bindings": [
    {"target": "gen-001", "source_id": 79, "enum_name": "Sokkuri"}
  ]
}
```

Determinism: the layout is a pure function of `(seed, slot, roster revision,
targets, cohort)`. `randomizer.seed.SeedRandom` is seeded with
`"{seed}/p2-enemy-layout-v1/{slot}"`; runtime spawn order, memory addresses and
visit count never participate. The same seed/revisit/restart therefore resolves
to the same identity.

Rejection rules enforced by `validate_layout`:

- Only `enemy`/`boss` classifications may be bound; plants, hazards, projectiles,
  `nest`, `manager_base` and `non_spawnable` IDs are rejected, never substituted
  with a P1 analogue.
- Unknown source IDs, duplicate targets/source IDs and empty cohorts are rejected.
- A saved `roster_revision` that does not match the current roster is rejected, so
  a changed roster invalidates rather than silently re-rolling the seed.
- An empty `cohort` fails generation: lane 03 cannot seed an unadmitted pool.

## Native bootstrap line

```
ENEMY_P2 <protocol=1> <roster_revision> <count> <target> <source_id> ...
```

Example: `ENEMY_P2 1 <hex> 2 gen-001 79 gen-002 30`

**Native parser contract (proposed, lane 01 to integrate under #186).** The
existing parser in `engine/pc_port/pc_randomizer.cpp` reads P1 layout lines at
schema 9. The P2 bridge requires:

1. Bump the bootstrap schema (`schema >= 10`) and advertise `p2-enemy-bridge-v1`
   in `hello.txt`.
2. On `ENEMY_P2`, require the protocol version and `roster_revision` to match the
   compiled roster constant; read `count` `<target> <source_id>` pairs; reject
   unknown/unbindable IDs, duplicate targets and trailing data. Store bindings
   keyed by target.
3. Replace the ordinary P1 pool for bound targets only; leave unbound generators
   as vanilla. Do not mix `ENEMY_P2` with `ENEMY_CAMPAIGN`/`ENEMY_SLOTS`.
4. Reject a bootstrap without `END` or with `ENEMY_P2` repeated.

The roster hash constant is generated separately from lane 02's
`docs/PIKMIN2_ENEMY_ROSTER.json`; the native side must compile the same revision
or fail closed.

## AP/CLI glue (proposed)

- New AP option `P2EnemyRandomizer` (Toggle, default off), mutually exclusive with
  the P1 `campaign_enemies`/`per_spawn_enemies`/`group_spawn_enemies` layouts.
- Seed schema bump with a `p2_layout` field and `p2_bootstrap` line; `validate`
  accepts exactly one of the P1 layouts or `p2_layout`.
- CLI: `--p2-enemies` plus an admitted cohort source (lane 02 evidence overlay or
  an explicit allowlist) and lane 04 binding targets.
- Only a seed whose `p2_layout` validates generates a session; otherwise
  generation fails with the offending target/source identified (no silent P1
  substitute).

These wiring changes touch shared seed/options semantics and should land as a
small focused commit reviewed by lane 01, after lane 04/05 supply real targets and
staging.

## Validation

```powershell
py -3.12 -m pytest tests/test_pikmin2_seed_bridge.py -q   # 10 passed
```

Covered: determinism across seed/slot, cohort coverage, rejection of
non-bindable/unknown/duplicate IDs, stale-revision rejection, bootstrap
round-trip, malformed-line rejection, and legacy manifests emitting no line.

## Remaining work

- Lane 04: real binding targets and legal placement.
- Lane 05: stage assets keyed by `source_id`/`enum_name`.
- Lane 06: reward/corpse semantics for bound identities.
- One eligible family to move the first admitted cohort from `denied` to
  `admitted` in the #438 evidence overlay.
- Native parser seam (schema >= 10) and AP option wiring, reviewed by lane 01.
