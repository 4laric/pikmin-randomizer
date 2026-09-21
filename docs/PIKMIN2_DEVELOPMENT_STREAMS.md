# P2 development streams: inventory, routing and activation

Tracking issue: **#859** (owner Codex through shared account `4laric`; OpenCode
executing worker). Coordination and shared-semantics review: **#186**.

This document is the current routing manifest for the three user-authorized
development streams. It records what has actually been **provisioned** (branches
and private worktrees) separately from what is **staffed/active** (an explicitly
bound owner running one bounded batch). Provisioning a branch is not staffing and
is not maintained delivery.

Stream state lives in the shared registry under an isolated
`development_streams` section via `workflow.development_streams`. Stream-local
candidate receipts are **never** canonical `done`/`integrated`: the module never
calls `Registry.integrate`, never dispatches and never wakes a maintained
consumer. Final merges, maintained builds/exports, integration receipts and
gameplay admission stay with the existing sole integration owner.

## Verified maintained sources (inspection, 2026-09-21)

| Source | Repo | Ref | Commit | Dirty baseline |
|---|---|---|---|---|
| Root | `output/p2-main-review` | `codex/p2-main-review` | `8f790eb464ffa4dc567f5a07709a3ca2da19084c` | clean (0 porcelain) |
| Native | `output/dsw/native-wave` | `claude/p2-deepseek-wave-native` | `a53a8bb96820d478410686dfc694650254084cdd` | clean (0 porcelain) |

These are the configured `integration_lines` in
`output/workflow/controller/config.json`. The setup worktree is
`output/development-streams/setup-root` on `codex/development-stream-setup`,
based on canonical root HEAD `fdd558123223f94d706b9a00973037553e864756`.

## Provisioned streams

All six paired worktrees were created from the maintained pins above. Each stream
is `awaiting-controller-assignment`: no lane has been bound and no candidate is
`ready`. These branches were **not** pushed and no build directory was created.

| Stream | Root branch / worktree | Native branch / worktree | Owner | Ready batch | Status |
|---|---|---|---|---|---|
| `actors-assets` | `codex/stream-actors-assets` / `output/development-streams/actors-assets/root` | `codex/stream-actors-assets` / `output/development-streams/actors-assets/native` | awaiting-controller-assignment | none | provisioned |
| `world-content` | `codex/stream-world-content` / `output/development-streams/world-content/root` | `codex/stream-world-content` / `output/development-streams/world-content/native` | awaiting-controller-assignment | none | provisioned |
| `campaign-product` | `codex/stream-campaign-product` / `output/development-streams/campaign-product/root` | `codex/stream-campaign-product` / `output/development-streams/campaign-product/native` | awaiting-controller-assignment | none | provisioned |

Future private build directories are reserved as
`output/development-streams/<stream>/build` and require an exclusive
`build:` resource lease plus the aggregate heavy-build budget before use.

## Per-stream scope and shared-hook boundaries

A stream owns only its own stream-local source slices. Shared engine hooks are
**requested**, never owned by a stream; every shared-hook change needs focused
`#186` shared-semantics review before it can be part of a maintained delivery.
The current shared-review routing hooks are
`native/pc_port/pc_p2_cave_transfer.h`, `native/pc_port/pc_p2_cave.cpp` and
`experimental/pikmin2_campaign.py`.

| Stream | Scope | Shared-hook boundary |
|---|---|---|
| `actors-assets` | Actor FSM/behaviour slices, receivers, lifecycle and starting-squad/asset adoption for existing lane work | Requests `pc_p2_actor_slots.h`/actor registration hooks through `#186` review; does not edit maintained engine sources |
| `world-content` | Cave/overworld geometry, placement, generation and challenge/area content slices | Requests cave transfer/generation hooks through `#186` review; does not own shared cave routing |
| `campaign-product` | Campaign/product integration, goal lifecycle, staging and packaging slices | Requests campaign scripting hooks through `#186` review; does not own maintained campaign export |

## Current work candidates (references, not duplicates)

Candidates are represented by **existing** lane IDs and issues. This setup does
not create duplicate work, reassign existing owners or claim unstarted slots; a
stream candidate is only a routing reference until the integrator activates it.

| Stream | Existing lane / issue references |
|---|---|
| `actors-assets` | `rd-p2-sarai-natural` (#830), `rd-p2-kurage-natural` (#832), `rd-p2-kurage-capture-ownership` (#839), `rd-p2-kogane-natural` (#831), `rd-p2-minihoudai-admission` (#847), converter/animation (#128) |
| `world-content` | `shard-caves-forest-forest1-p1` (#154), `shard-caves-yakushima-yakushima4-p1` (#161), `p2-cave-tutorial_2-p1-later-floors` (#747), `p2-cave-tutorial_3-p1-later-floors` (#812), `p2-overworld-yakushima-p1-native-runtime` (#150), planning shards (#593–#610) |
| `campaign-product` | `rd-p2-campaign-fixture` (#837), `rd-p2-campaign-goal-lifecycle` (#836), `rd-p2-sarai-campaign` (#457), `rd-p2-sarai-goal-census` (#843), `codex-p2-ap-campaign-821` (#821), campaign smoke (#186) |

## Activation blockers

1. No owner is bound on any stream (`awaiting-controller-assignment`); owner
   binding must name an existing, live, unfinished lane that owns no other stream.
2. The sole integration line is currently occupied by the integrator takeover and
   export-evidence repair; the bottleneck session owns the surrounding workflow
   repair files. Streams must not contend with it.
3. No candidate is `ready`; a candidate must pin the current maintained base or it
   is rejected as stale (fail-closed), and a stream may hold at most one `ready`
   batch.
4. Future private builds require an exclusive lease and RAM admission; no build
   directory or lease was created during provisioning.

## Exact integrator actions

1. Review the committed setup on `codex/development-stream-setup` (#859).
2. Bind one genuine owner per stream (reconcile existing owners; do not fabricate
   assignments and state unstaffed roles honestly).
3. Activate exactly one bounded batch per stream by submitting one `ready`
   candidate that pins the maintained base; then run normal private
   implementation, shared review and handoff validation.
4. Keep final merges, maintained build/export, integration receipts and gameplay
   ADMIT with the sole integration owner. Do not treat a stream-local receipt as
   integration or as a consumer wakeup.

### Activation command packet

Write an activation request (example) and review it before running:

```json
{
  "operation": "bind-owner",
  "stream": "actors-assets",
  "lane": "<existing-owner-lane>",
  "generation": 1,
  "replace": false
}
```

```powershell
py -3.12 -m workflow.development_streams --root C:/Users/alari/pikmin-randomizer --request output/development-streams/activation.json
```

Promotion request (one ready batch per stream; fails closed on stale pins):

```json
{
  "operation": "submit-candidate",
  "stream": "actors-assets",
  "candidate": {
    "id": "<candidate-id>",
    "title": "<bounded slice>",
    "summary": "<stream-local summary>",
    "references": ["#830"],
    "base": {
      "root": "8f790eb464ffa4dc567f5a07709a3ca2da19084c",
      "native": "a53a8bb96820d478410686dfc694650254084cdd"
    },
    "commits": {"root": [], "native": []},
    "state": "ready",
    "evidence": {"path": "output/development-streams/<stream>/evidence.md", "sha256": "<sha256>"}
  }
}
```

Read-only inventory:

```powershell
py -3.12 -m workflow.development_streams --root C:/Users/alari/pikmin-randomizer --request output/development-streams/status.json
```

## Status vocabulary

* `provisioned` / `awaiting-owner` — branch and worktree exist; no staffed owner.
* `active` — an explicit existing lane is bound; at most one `ready` batch.
* `stale` candidate — its pinned maintained base moved; it must be re-based and
  resubmitted, never promoted or silently rebased by the registry.
* `maintained_receipts` — references only, recorded by an integration-owner lane;
  they never set a stream-local candidate to canonical `done`.

Tooling-only scope: this setup does not build, launch, export or accept gameplay.
No stream is staffed or active as of provisioning.
