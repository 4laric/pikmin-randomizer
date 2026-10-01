# Pom actor-birth provider (issue #448)

Lane `shard-enemies-1-pom-actor-provider`. Owner: Codex through shared
account `4laric`. Issue #448 stays OPEN; this provider does not close it.

## What the adjudication proved (consumed read-only)

`shard-enemies-1-pom-spawn-adjudication` (done) proved gate 1 needs a real
Pom-manager-born actor: generator records name a colored id 3..8
(`EFlag_CanBeSpawned`, no `UseOwnID`), the manager resolves to parent
`EnemyID_Pom` (`enemyInfo.h:204`), and base Pom (82) is not spawnable
("crashes"). Lane 23 substituted a Chappy proxy vehicle, which the
adjudication ruled not source-correct for natural spawn. Marker names
`P2_POM_BIND` (with `host=pom`), `P2_POM_DRAW`, `P2_SEED_RESOLVE` and
`P2_GENERATED_PLACEMENT` are reused from that review.

## What this slice implements

Birth RECORD provider behind a seam, mirroring the accepted #577 Bomb
payload provider shape (contract + ownership machine, strict-compile
proof, seam fixture; stub flow untouched; runtime birth deferred):

- `native/pc_port/pc_p2_pom_actor.h` / `.cpp`: fail-closed resolution
  (colored 3..8 to parent 82; base 82 refused), generational ownership
  pool (single-use bind, exactly-once birth record, recycle-safe
  release), exact marker formatters. Engine-free (`-Ipc_port` only),
  prints nothing.
- `experimental/pikmin2_pom_actor_provider.py`: marker grammar plus
  `validate_log` verdicts for future fixture logs (exactly-once per
  generator, disagreement/injection refused, fails closed on empty).
- `tests/test_pikmin2_pom_actor_provider.py`: 14 focused boundary tests.
- `native/tools/p2_pom_actor_seam_test.cpp`: engine-free seam proof
  (resolve/refusal/ownership/format checks, exit 0 + PASS line).

The lane-23 stub flow (`pc_p2_pom.cpp` Chappy proxy) is untouched. Draw,
mesh, generated-session placement triple and real in-game birth are
explicit follow-ons, not claimed here.

## Scope split (no duplication)

- Family scope (flora/pom lane, #448): Pom actor/manager birth — this file
  set only. No existing-file modifications at all.
- Generated-session placement binding: placement shards, coordinated
  through #570; not duplicated here.
- Shared-owner engine change still needed: teki birth path for a real Pom
  manager birth at runtime. Requested as review, not implemented here.

## Evidence

- Strict compile: `g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port`
  (see `out/strict-compile.log` in the shard `out/` directory).
- Seam test: `p2_pom_actor_seam_test` exit 0 (same log).
- Marker tests: `pytest tests/test_pikmin2_pom_actor_provider.py`
  (see `out/pytest.log`).
- Handoff: `out/handoff.json` (tooling; all runtime gates UNTESTED).

## Next bounded scope (reported to integrator #437)

In-game birth + gate-1 triple: host-side `P2PomActorBirthSeam` binding in
the teki birth path (shared-owner review), then a fresh run emitting
`P2_POM_BIND host=pom`, `P2_POM_DRAW bank=pom`, `P2_SEED_RESOLVE` and
`P2_GENERATED_PLACEMENT bound=1` agreeing on one generator and colored
source id, adjudicated for the gate-1 flip candidate.
