# BlueKochappy44 generated-identity gate-1 observer (shard lane, #461)

Worker: Muse Spark 1.3 (`opencode-go/muse-spark-1.3-contributor`, lane
shard-enemies-5-bluekochappy44-observer, generation 2). Implementation owner:
Codex through shared account `4laric`. Parent #167; family lane #461.
Source ID 44 BlueKochappy (Dwarf Orange Bulborb) is the slice target.

## Scope result

Tooling-only slice: a correlated gate-1 observer over the three native
birth-marker legs (seed-resolve manifest, generated-placement bind,
dwarf-orange actor binding) plus focused negative tests. Existing partials
(dwarf_orange install/arena/profile/bank modules and roster evidence) are
preserved and NOT redone. Gate 1 generated-identity correlation stays
BLOCKED until a real generated run is observed by a runtime lane; no natural
PASS is invented; no ADMIT.

## Source ID

```
Source ID: 44 `BlueKochappy`
```

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED (generated correlation; roster PASS preserved per partials) | `experimental/pikmin2_bluekochappy44_observer.py` observer contract; `output/qa-dwarf-orange/restart-asg5fix3/evidence.json` historical chain (read-only reference, not a fresh run) | unobserved by this slice |
| 2. Movement and animation | PASS (natural, arena scope per partials) | `output/qa-dwarf-orange/restart-asg5fix3/evidence.json` POS rows; preserved, not relabelled | natural |
| 3. Attacks and receivers | PASS (natural, arena scope per partials) | `output/qa-dwarf-orange/restart-asg5fix3/evidence.json` attack-state rows; `docs/PIKMIN2_DWARF_VARIANTS.md` identity row; preserved, not relabelled | natural |
| 4. Death and corpse | PASS (natural, arena scope per partials) | `output/qa-dwarf-orange/restart-asg5fix3/evidence.json` death/corpse chain; preserved, not relabelled | natural |
| 5. Transport and reward | BLOCKED (per partials; route acceptance conditional) | preserved partials; no new claim | unobserved by this slice |
| 6. Cleanup and re-entry | BLOCKED (per partials; revisit within one process open) | preserved partials; no new claim | unobserved by this slice |

Gate detail:

- Gate 1: roster-level identity is PASS at arena scope per the #461 partials
  (restart-asg5fix3 evidence: `P2_ENEMY_READY species=BlueKochappy
  source_id=44 generator=3670065 health=250`, stable across two runs). The
  generated-identity correlation this observer checks (same UID across
  seed-resolve manifest, placement bind, and family binding rows, with
  placeholder-0 rows never counting) is BLOCKED: no fresh generated run was
  observed by this tooling slice, and the historical logs are read-only
  references, not fresh evidence.
- The observer contract (`experimental/pikmin2_bluekochappy44_observer.py`):
  manifest leg (source_id/generator/expected XYZ/health, fail-closed on
  malformed/zero UID), placement leg (`P2_ENEMY_READY` parse; single nonzero
  UID; health/XYZ match; source-swap rejection), binding leg
  (`P2_KOCHAPPY_STATE/POS/DEAD` same-UID requirement; route evidence of
  >=3 POS rows with >=5.0 displacement), taint rejection (`INJECT`,
  `TELEPORT`, `FORCED_BIRTH`, `mHealth =` writes), stray-placeholder
  rejection. CLI: `py -3.12 -m experimental.pikmin2_bluekochappy44_observer
  --manifest <spawn.json> --log <native.log>` prints the JSON verdict.
- Honesty notes: the planned native bind route (`pc_p2_generated_bind`
  source-44 route) does not exist yet in the shared checkout, so leg 3
  currently means family behavior markers, not the planned route; the
  observer will bind the route markers once the family owner lands them
  (validator patterns are data, not shared edits). No file here fabricates a
  run: all positive test logs are synthetic and labeled as such.

## Source IDs and files owned

- Source IDs: 44 BlueKochappy (slice target).
- Root (worktree `output/workflow/autofill/planning-shards/enemies-5/prepared/bluekochappy44-observer-root`,
  branch `codex/shard-enemies-5-bluekochappy44-observer`):
  `experimental/pikmin2_bluekochappy44_observer.py` (new),
  `tests/test_pikmin2_bluekochappy44_observer.py` (new),
  `docs/pikmin2_bluekochappy44_observer.md` (this file).
- Existing dwarf_orange install/arena/profile/bank modules and roster
  evidence were read, never edited. No native worktree in this slice.

## Ordered commits (dirty: clean)

Root (`codex/shard-enemies-5-bluekochappy44-observer`, base `36b868391e62cccf37d992aa2f796f3cc9c6dc31`):
- TBD observer + negative tests + spec doc (#461)

## Interfaces / hooks touched

- None in shared engine code. No native changes; a defect needing shared
  changes would be filed as a focused request with the defect (none found).

## Build evidence

Tooling-only: no native build, no fixture, no executable. Focused pytest only.

## Fixture baseline adoption

N/A (tooling-only observer; no runtime launch, arena, squad, or window).

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_bluekochappy44_observer.py -q` ->
  14 passed (contract accept plus 13 negative classes: swapped source,
  slot/generator mismatch, three missing legs, malformed manifest,
  unmapped slot, placeholder-only and stray-placeholder identity, health
  mismatch, XYZ mismatch, missing/static route, three taint markers).

## Gate-check output

```
$ py -3.12 scripts/check_p2_handoff_gates.py docs/pikmin2_bluekochappy44_observer.md
44 BlueKochappy (role=source):
  1. identity_spawn     ignored [BLOCKED]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [BLOCKED]
  6. cleanup_reentry    ignored [BLOCKED]
```