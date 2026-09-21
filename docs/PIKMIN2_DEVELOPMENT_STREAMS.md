# P2 development streams: inventory, routing and activation

Tracking issue: **#859** (owner Codex through shared account `4laric`; OpenCode
executing worker). Coordination and shared-semantics review: **#186**.

This document is the current routing manifest for the three user-authorized
development streams. It records what has actually been **provisioned** (branches
and private worktrees) separately from what is **staffed/active** (a live,
generation-fenced owner running one bounded batch). Provisioning a branch is not
staffing and is not maintained delivery.

Stream state lives in the shared registry under an isolated
`development_streams` section via `workflow.development_streams`. Stream-local
candidate receipts are **never** canonical `done`/`integrated`: the module never
calls `Registry.integrate`, never dispatches and never wakes a maintained
consumer. Final merges, maintained builds/exports, integration receipts and
gameplay admission stay with the existing sole integration owner.

## Verified maintained sources and observed dirty baselines (2026-09-21)

| Source | Repo | Ref | Commit | Observed dirty baseline |
|---|---|---|---|---|
| Root | `output/p2-main-review` | `codex/p2-main-review` | `8f790eb464ffa4dc567f5a07709a3ca2da19084c` | recorded, not required clean |
| Native | `output/dsw/native-wave` | `claude/p2-deepseek-wave-native` | `a53a8bb96820d478410686dfc694650254084cdd` | recorded, not required clean |

`observe_maintained_sources()` reads the real Git HEAD and `git status
--porcelain` from the configured `integration_lines` outside any registry lock.
A stream-local submission is rejected while the observed HEAD differs from the
recorded maintained base; the base must be refreshed explicitly
(`configure(..., supersede=True)`), which marks older candidates `stale`.

The setup worktree is `output/development-streams/setup-root` on
`codex/development-stream-setup`.

## Provisioned streams

All six paired worktrees descend from the maintained pins above. Each stream is
`awaiting-controller-assignment`: no live owner is bound and no candidate is
`ready`. Branches were **not** pushed; no build directory or lease was created.

| Stream | Root branch / worktree | Native branch / worktree | Owner state | Ready batch |
|---|---|---|---|---|
| `actors-assets` | `codex/stream-actors-assets` / `output/development-streams/actors-assets/root` | `codex/stream-actors-assets` / `output/development-streams/actors-assets/native` | awaiting-controller-assignment | none |
| `world-content` | `codex/stream-world-content` / `output/development-streams/world-content/root` | `codex/stream-world-content` / `output/development-streams/world-content/native` | awaiting-controller-assignment | none |
| `campaign-product` | `codex/stream-campaign-product` / `output/development-streams/campaign-product/root` | `codex/stream-campaign-product` / `output/development-streams/campaign-product/native` | awaiting-controller-assignment | none |

Future private build directories are reserved as
`output/development-streams/<stream>/build` and require an exclusive `build:`
lease plus the aggregate heavy-build budget.

## Per-stream scope and shared-hook boundaries

A stream owns only its own stream-local source slices. Shared engine hooks are
**requested**, never owned by a stream; every shared-hook change needs focused
`#186` shared-semantics review before it can be part of a maintained delivery.

| Stream | Scope | Shared-hook boundary |
|---|---|---|
| `actors-assets` | Actor FSM/behaviour, receivers, lifecycle and squad/asset adoption slices | Requests actor registration hooks through `#186`; does not edit maintained engine sources |
| `world-content` | Cave/overworld geometry, placement, generation and challenge/area content | Requests cave transfer/generation hooks through `#186` |
| `campaign-product` | Campaign/product integration, goal lifecycle, staging and packaging | Requests campaign scripting hooks through `#186` |

## Current work candidates (references, not duplicates)

| Stream | Existing lane / issue references |
|---|---|
| `actors-assets` | `rd-p2-sarai-natural` (#830), `rd-p2-kurage-natural` (#832), `rd-p2-kogane-natural` (#831), `rd-p2-minihoudai-admission` (#847), converter/animation (#128) |
| `world-content` | `shard-caves-forest-forest1-p1` (#154), `shard-caves-yakushima-yakushima4-p1` (#161), `p2-cave-tutorial_2-p1-later-floors` (#747), `p2-overworld-yakushima-p1-native-runtime` (#150) |
| `campaign-product` | `rd-p2-campaign-goal-lifecycle` (#836), `rd-p2-campaign-fixture` (#837), `rd-p2-sarai-goal-census` (#843), `codex-p2-ap-campaign-821` (#821) |

## Staffing: prepared activation requests (not executed)

No supported development-stream owner role exists. Ownership is lane-scoped and
issue-backed, executed only by the sole controller. Worker availability and the
exact blocker are recorded in `output/stream-rollout/staffing.md`.

| Stream | Activation issue | Candidate worker | Current safety | Packet |
|---|---|---|---|---|
| `actors-assets` | #861 | `muse-l71` (implementation) | 1 blocked lane; controller must park/reuse first | `output/stream-rollout/activation/actors-assets.json` |
| `world-content` | #862 | `muse-l72` (implementation) | 1 blocked lane; controller must park/reuse first | `output/stream-rollout/activation/world-content.json` |
| `campaign-product` | #863 | `muse-l73` (implementation) | 1 blocked lane; controller must park/reuse first | `output/stream-rollout/activation/campaign-product.json` |

Each packet contains a full `register_request` (issue, worker, stream
worktrees, maintained-base pins, honest dirty baseline) and a `bind_owner_request`.
They are staged for the existing controller/coordinator, which must park/reuse
the candidate worker, register the lane and bind it. Central integrator approval
is pending. No running lane is stolen or reassigned.

The unsupported stream-owner role itself is tracked as bounded follow-on #864
(controller worker adaptation). Until that lands, streams stay provisioned-only.
The three streams are also recorded **inactive** in the shared
`development_streams` section (`status: awaiting-owner`, zero active, zero ready
batches) using the verified `configure` operation; no owner is bound and no
controller configuration is changed.

## Module contract (v1)

Operations (`python -m workflow.development_streams --root <root> --request <json>`):

| Operation | Effect |
|---|---|
| `configure` | Upsert stream definitions (worktree paths + expected branches); refuses a silent maintained-base move unless `supersede=true`, which stales older candidates and clears the ready slot |
| `bind-owner` | Bind one existing **live** lane at its **mandatory current generation**; one owner per stream, one stream per lane |
| `submit-candidate` | Record a stream-local candidate; the caller must name the current bound owner lane and integer generation; observes real Git HEAD, rejects stale maintained base, rejects resealed maintain/pin drift, and rejects duplicate candidate IDs |
| `retire-ready` | Fenced **abandon** of the ready batch (reason required); releases the slot without claiming delivery; idempotent for the exact reason, conflicting replay refused |
| `validate-sources` | Fail-closed check of observed maintained HEAD and both stream worktree identities |
| `canonical-receipt` | Read-only snapshot of a lane's real canonical `lane.integration` record, if any |
| `receipts` | Read-only historical receipt references for a stream (normally empty) |
| `status` / `manifest` | Inventory with `owner_state` (`awaiting-controller-assignment`, `assigned-live`, `assigned-not-live`, `assigned-stale-generation`, `assigned-terminal`) |

Fail-closed guarantees:

* every owner operation names an existing, live, unfinished lane and its current
  integer generation; a request from an older generation cannot write after an
  owner rebind, and a stored owner label is not authority;
* candidate IDs are immutable: a recorded ID can never be overwritten, so a
  ready candidate cannot be demoted to draft and a closed ID cannot be reused;
* the ready slot can always be released through a reasoned `retire-ready`
  abandon, so a stream can accept a second batch;
* v1 has **no writable maintained-delivery disposition**: an unrelated valid
  canonical integration cannot be attached to a stream candidate. Canonical
  maintained receipts are exposed read-only via `canonical-receipt`, and
  abandonment grants no acceptance;
* both paired stream worktrees must exist as real git worktrees on their
  recorded branch and descend from the maintained base; the observed maintained
  HEAD must equal the configured ref, and dirty state is recorded, never
  required clean;
* stream-local status never records canonical integration, dispatches or wakes a
  maintained consumer.

## Status vocabulary

* `provisioned` / `awaiting-owner` — branch and worktree exist; no staffed owner.
* `active` — a live existing lane is bound at its current generation; at most
  one `ready` batch.
* `stale` candidate — its pinned maintained base or observed HEAD moved; it must
  be resubmitted, never promoted or silently rebased.
* `abandoned` / `maintained` candidate — a closed ready batch; history retained.
* `maintained_receipts` — read-only references to canonical integration records.

Tooling-only scope: this setup does not build, launch, export or accept gameplay.
No stream is staffed or active as of this revision.
