# Generic held-object/drop/carry provider (issue #614)

Lane `provider-held-object-api`, generation 2. Tooling-only provider slice:
no family FSM work, no shared-file edits, no ADMIT, no gameplay PASS claim.
Consumer integration (BigFoot69 #574, LongLegs) is a later bounded slice.

## What this delivers

ONE generic engine-free held-object provider mirroring the proven #577
bomb-payload pattern (`native/pc_port/pc_p2_bomb_payload_actor.h`): a
generational-handle pool (`P2HeldObjectPool`, max 8) with attach at a joint,
carry-follow, detach/drop with velocity, carrier-death and item-loss paths,
interruption/reset cleanup, exactly-once delivery release, and single-set
reward confirmation. The core is engine-free (`-Ipc_port` only, `cstdint`);
it never enumerates creatures, touches files/ledgers, or prints.

## Host API contract

```cpp
#include "pc_p2_held_object.h"
P2HeldObjectPool pool;
auto h = pool.attach(carrierToken, itemToken, jointPos); // invalid on refusal
pool.followJoint(h, jointPos);                            // while Attached
pool.detach(h, velocity, P2HeldObjectDetachReason::Dropped); // -> Dropped
pool.release(h);                          // -> Released, needsReward=true
const P2HeldObjectRelease& ev = pool.lastRelease(h);
pool.confirmReward(h, granted);           // host reports receipt outcome
pool.reset();                             // interruption/re-entry cleanup
```

Reward credit flows ONLY through the EXISTING receipt host. On release the
provider records `(carrierToken, itemToken)`; the host maps them with
`experimental.pikmin2_held_object_provider.receipt_keys` to
`pc_p2_receipt_host_grant(seed, "treasure:<item>", "<carrier>",
"held-release")` (or the delivery host twin) and reports the outcome with
`confirmReward`. There is no second ledger and no divergent treasure
implementation. Duplicate `release`/`confirmReward` calls fail and are
counted as suppressed; `reset()` retires all handles by epoch advance.

## Validation evidence (this turn, no runtime)

- `native/tools/p2_held_object_test.cpp`: 67/67 standalone checks pass
  (`-Wall -Wextra -Werror`, exit 0) covering attach refusal, follow,
  detach exactly-once + velocity, release exactly-once + reward flag,
  single-set confirmation, carrier-death drop, item-loss no-reward
  release, reset/epoch reuse, and stale-handle fail-closed.
- `tests/test_pikmin2_held_object_provider.py`: 11/11 pass covering the
  contract shape, receipt-key mapping + input refusal, and the log grammar
  (canonical agreement, double release/reward, missing follow/detach, bad
  reason, injected markers, empty log).
- `experimental.pikmin2_held_object_provider.validate_log` gives consumers
  deterministic verdicts on future fixture logs; agreement alone never
  passes acceptance.

## Integration contract for consumers

- BigFoot69 (#574, explicit held-treasure follow-on): after this provider
  lands, stage ONE bounded slice that binds a live carrier token + treasure
  item token through `attach`, emits the `P2_HELD_OBJECT_*` marker grammar
  from a real fixture run, validates with `validate_log`, and credits
  through the existing receipt host. Owner review required before any
  family/shared touch.
- LongLegs held-object: same contract; the family FSM stays read-only
  until its owner reviews a scoped shared hook through #491/#186.
- Staged (injected/diagnostic) versus natural (live-carrier) observations
  must be labeled separately in any consumer handoff; injected evidence
  alone cannot close a natural gate.

## Exact blockers / remaining work

- Consumer runtime slices (fresh arenas, live carriers, 960x540 adoption)
  are later bounded work, not this slice.
- Any change to `scripts/build_pikmin2_fixture.py`, the receipt/delivery
  hosts, or family modules needs explicit owner review; none was made here.
- Environment note: this lane `opencode.json` orders the `edit` wildcard
  deny before its specific allow paths, so Write/Edit were refused for the
  reserved paths; files were created via the permitted shell tool. Config
  owner should reorder the edit rules.

## One exact reproduction command

```
cd <held-object-root worktree>
py -3.12 -m pytest tests/test_pikmin2_held_object_provider.py -q   # 11 passed
```