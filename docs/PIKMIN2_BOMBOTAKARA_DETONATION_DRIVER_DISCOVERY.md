# BombOtakara93 detonation-driver pin registry (#806, consumer #573 gate-3)

Bounded DIAGNOSIS for lane `shard-enemies-3-bombotakara93-detonation-discovery`
(issue #806). Pins the exact detonation driver callsites, build membership
and owner routing for the #186 shared-hook review of
`enemy-bombotakara93-payload` gate-3. Consumes the DONE
`bombotakara93-bridge-pin-audit` (#791) and `provider-bomb-mgr-birth` (#616)
read-only; never duplicates them. No engine edits, builds, runtime runs,
shared edits or ADMIT. All six gates UNTESTED.

## Reference pins (verified read-only this turn)

- Maintained native `a95040b6`: `pc_p2_bombsarai_blast.h:55`
  (`p2_bombsarai_route_blast` PRESENT), `pc_p2_batch2.h:8`
  (`pc_p2_batch2_forget` PRESENT); `pc_p2_bombotakara.cpp` ABSENT,
  `pc_p2_bomb_mgr_birth.cpp` ABSENT.
- Owner-573 tree (`output/autofill-native-573/pc_port`):
  `pc_p2_bombotakara_policy.h:96` (`DetonationResult`), `:101`
  (`inline DetonationResult detonate`);
  `pc_p2_bombotakara.cpp:80` (`BlastOwner::doKill` no-op), `:93`
  (`applyBlast`), `:134` (`p2_bombsarai_route_blast` call), `:146`
  (`InteractBomb`), `:158` (`detonate(Unit&,Trigger)`),
  `:194` (`TriggerDeath`), `:197-200`
  (`TriggerPress`/`TriggerEarthquake`/`TriggerContact`).
- Birth reference (native @ `6d4cbc4a`, #616 DONE):
  `pc_p2_bomb_mgr_birth.h:106` (`int detonate`), `:122`
  (`blastCount`), `:128` (shared-hook contract comment);
  `pc_p2_bomb_mgr_birth.cpp:195` (`P2BombMgr::detonate`), `:218`
  (route call), `:268` (`blastCount`), `:407` (lane-07 Teki seam);
  `pc_p2_bomb_payload_actor.cpp:153`
  (`P2BombPayloadPool::detonate`), `:150` (Death trigger).
- Current wave tip `db85b2f9` carries the #616 birth files and the #573
  payload files (integrated, not admitted); the reference verdicts above are
  pinned to `a95040b6` per the brief.

## Driver boundaries and contracts

| Boundary | Driver callsite(s) | Owner (issue) | Verdict | Shared-review contract |
|---|---|---|---|---|
| Payload detonate gate | policy.h:101 + bombotakara.cpp:158/93/80 | enemy-bombotakara93-payload (573) | ABSENT in maintained; PRESENT in owner-573 | #573 ownership + #186 (payload driver on shared blast path) |
| Birth-hook detonate | birth.h:106/122 + birth.cpp:195/268 + payload_actor.cpp:153 | provider-bomb-mgr-birth (616) | ABSENT in maintained; PRESENT in #616 ref | #616 ownership + #186 (birth hook on shared BTeki path) |
| Shared blast primitive | blast.h:55 `p2_bombsarai_route_blast` | projectiles/BombSarai (169) | PRESENT in maintained | #169 owns the primitive + #186 |
| Teki forget seam | batch2.h:8 / batch2.cpp:198 `pc_p2_batch2_forget` | shared engine seam (tekibteki) | PRESENT in maintained | #186 (TekiMgr forget path) |

## Downstream consumer commands (#573 gate-3 rerun)

Consumer lane `enemy-bombotakara93-payload` replays gate-3 over the landed
drivers (the rerun itself is the consumer lane's action):

- `scripts/run_pikmin2_fixture.py --arena <bombotakara-arena> --fixture <bombotakara-gate3-fixture.exe> --seconds <budget>`
- Expect `P2_BOMBOTAKARA_DETONATE exactly_once=1` on the fatal trigger plus
  `DETONATE_SUPPRESSED` on reruns; `P2_BOMBOTAKARA_BLAST` routed via
  `p2_bombsarai_route_blast` (or `BLAST_BLOCKED` on invalid blasts);
  `P2BombMgr::detonate` binding with a single `blastCount` increment.
- Bridge refusal (`speciesFromSource` 59-62 only, -1 for 93) stays with the
  #791 audit + #616 birth path and is NOT re-derived here.

## Tooling

- `experimental/pikmin2_bombotakara_detonation_driver_discovery.py` verifies
  all four boundaries fail-closed and emits
  `bombotakara93-detonation-driver-registry.json` (refuses to overwrite).
- `tests/test_pikmin2_bombotakara_detonation_driver_discovery.py`: focused
  pin/owner/helper tests plus live pin checks against the reference trees.
