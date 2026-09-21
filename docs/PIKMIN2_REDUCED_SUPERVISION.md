# Bounded reduced-mode supervision (#829)

The sole controller can run `reduced_supervision` with configuration:

```json
{"reduced_supervision":{"enabled":true,"interval_seconds":300,"max_per_tick":2}}
```

Every five minutes it checks at most two pending reduced-mode handoffs, rotating
through the queue. An existing `output/reduced/<lane>/receipt-request.json` is
replayed only after worker/resource liveness checks, and through `Registry.receipt`:
generation, validation hashes, ancestry, actual landed bytes and approval ledger
remain authoritative. It never creates validation/export claims or approves reviews.
Without a request it inspects the destination to distinguish missing source from
missing review/receipting. Invalid evidence remains a visible operator action.
No source merging or gameplay admission occurs inside this loop.

The compact result is `output/workflow/controller/reduced-supervision.json`.
Read it directly or use `py -3.12 -m workflow.reduced_supervision --root <root>`
from the deployed release. Counts describe the snapshot at the beginning of the
cycle; successful receipts appear in `checked` immediately and counts catch up
on the next cycle. `review_ready` outcomes remain operator decisions.

Reduced lanes finishing blocked record a fingerprint of their source heads,
normalized dependencies, referenced producers' source/delivery/disposition and
their approval ledger IDs. All subsequent blocked launch intents require a change
to these inputs. Reason, prompt, generation and backoff expiry do not grant a retry.
Existing blocked lanes without this baseline can receive one legacy attempt; their
next blocked finish establishes it. Live/reconciling recovery is unaffected.

For a deliberate operator check, use reason `operator: <specific reason>` and
`carry.operator_retry_evidence = {path, sha256}` in the existing `plan_launch` API.
The evidence must exist and hash correctly. This is audited as `operator_retry`;
all normal ownership, process and WIP checks still apply. Do not use it for a timer
retry. A prerequisite needs an actual recorded source/delivery or reviewed decision.

An hourly strong-agent check reads the compact report and exits promptly when
unchanged. It handles integration judgments and concrete scope decisions, while
the existing inexpensive managed agents implement, build and test. No planner
pool is enabled. Natural gameplay and species-specific acceptance remain separate
from source delivery; e.g. an idle-squad Kogane observation does not prove player
throws fail or justify converting its flip/drop behavior into health damage.
