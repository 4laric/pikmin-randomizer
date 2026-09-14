# P2 seed selection and native manifest bridge (lane 03, #439)

Opt-in, versioned P2 enemy choices with deterministic native actor bindings.
Consumes the lane 02 roster (#438). Placement belongs to lane 04, content staging
to lane 05, reward semantics to lane 06. This lane owns shared seed/options and
the protocol adapter.

Status: **adapter + wired opt-in generator**. The seed bridge is now reachable
from the real generator (`randomizer.seed.generate` / CLI) and manifests, gated by
lane 02's deny-by-default admission set. Runtime/native acceptance still needs
lanes 04/05 and at least one admitted family; no gameplay PASS is claimed here.
Ordinary P1 seed generation and legacy seeds are unchanged.

## Module

`experimental/pikmin2_seed_bridge.py`

- `resolve_admitted_layout(seed, slot, targets, roster=None)` → product entry
  point; derives the cohort from lane 02's admission set and fails closed when it
  is empty.
- `resolve_layout(seed, slot, targets, cohort, roster=None, *, admitted=None)` →
  deterministic layout; an optional allowlist rejects any unadmitted cohort id.
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

## Product wiring (schema 9, opt-in)

The bridge is no longer preview-only. With `p2_enemies` set, the ordinary
generator writes a `p2_layout` field onto a schema-9 manifest:

- `randomizer.seed.generate(..., p2_enemies=True, p2_targets=[...])` resolves the
  admitted cohort, stores `p2_layout`, and adds the `p2-enemy-bridge-v1`
  capability. It raises a clear `ValueError` when nothing is admitted or when no
  lane 04 targets are supplied.
- CLI: `--p2-enemies --p2-targets gen-001,gen-002`.
- `validate()` accepts `p2_layout` only on schema 9 with `enemy_mask == 0`, no
  P1 `spawn_layout`/`group_layout`/`campaign_layout`, the matching capability, and
  a layout that revalidates against the current roster.
- `randomizer.enemy_slots.bootstrap_slots(manifest)` emits the `ENEMY_P2` line for
  a `p2_layout` manifest, so the ordinary `NativeRun` bootstrap carries it.
- Legacy seeds carry no `p2_layout` and emit no line.

The admission set is empty today, so `--p2-enemies` correctly fails closed. Tests
inject a single admitted cohort (Sokkuri=79) to exercise generation, the
capability, determinism across restart and the bootstrap round trip.

## Native parser (worker branch, lane 01 integration seam)

A native `ENEMY_P2` parser is implemented on private native branch
`opencode/p2-lane03-native` @ `d05902cf` (base maintained `a95040b6`), with a
host-probe test that needs no game assets:

- `pc_port/pc_randomizer.cpp` / `.h`: parses `ENEMY_P2 <protocol> <revision> <count>`
  pairs, rejects wrong protocol/revision/count, unknown/unbindable IDs, duplicate
  targets and mixing with `ENEMY_SLOTS`/`ENEMY_GROUPS`/`ENEMY_CAMPAIGN`; advertises
  `p2-enemy-bridge-v1`; exposes `pc_randomizer_p2_bridge()` /
  `pc_randomizer_p2_source(target)` / `pc_randomizer_p2_binding_count()`.
- `pc_port/pc_randomizer_p2_roster.h`: generated by
  `scripts/generate_pikmin2_roster_revision.py` from the lane 02 roster; the
  compiled revision must match the Python one or the seed fails closed.
- `scripts/test_p2_bridge_native.py` + `--enemy-p2-probe`: parse/bind plus
  unknown-id, wrong-revision, duplicate-target and bad-count rejection.

The parser stores target→source bindings; the generator→target map and actual
P2 actor spawn remain lane 04/family work, and the native branch is not yet
reconciled into the maintained line (no whole-engine export was taken).

## Remaining work

- Lane 04: real binding targets and legal placement.
- Lane 05: stage assets keyed by `source_id`/`enum_name`.
- Lane 06: reward/corpse semantics for bound identities.
- One eligible family to move the first admitted cohort from `denied` to
  `admitted` in the #438 evidence overlay.
- Native parser seam (schema >= 10) and AP option wiring, reviewed by lane 01.
