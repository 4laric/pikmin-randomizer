# P2 workflow: family ownership and a small integration queue

**GL scheduling update (#462, user-authorized):** use [GL-A / no-input GL-B leases](PIKMIN2_GL_LANES.md). One interactive run and one reviewed hidden autonomous fixture may run together; acquire both leases for exclusive/performance runs. This supersedes older blanket one-GL wording below. Unreviewed fixtures remain A/exclusive.

Current operating policy, 2026-09-13. Owner: Codex using shared GitHub account
4laric, [#186](https://github.com/4laric/pikmin-randomizer/issues/186).
User direction: widen parallel work and reduce close integration supervision now
that the import paths have been demonstrated. This document supersedes older
coordination text requiring integration permission for every native hook or batch.

## What is slowing delivery

- **Implementation authority stops too early.** Beetle, Giant Breadbug, Mamuta
  and Bulblax workers delivered assets/installers, then waited for root-owned
  native bindings or mechanics (#228–235). Adding more extraction-only workers
  would grow that same queue.
- **Handoffs are smaller than useful outcomes.** The Demon sequence #215–242
  contains necessary research and tests, but repeated contract/fixture/review
  boundaries also create waiting. The family owner can take several related
  steps before returning a playable candidate.
- **Root repeats too much acceptance work.** Worker tests, private fixtures,
  root inspection, another combined build, and another package can all occur
  before independent QA starts. Review must focus on what changed in combination.
- **The shared native checkout and exported engine copy are a serial resource.**
  Private worktrees already solve much of this. Serialization belongs at the
  maintained merge/build, not throughout family development.
- **Status mixes delivery levels.** Open umbrellas and delivered child work are
  interleaved; an asset or display handoff can look like a blocked whole family.
  Some ownership tables still describe earlier batches. Use issue claims and
  acceptance levels instead of treating every open issue as active work.
- **QA needs navigable fixtures.** Cave QA reached a real floor-2 checkpoint but
  stalled finding the exit. The diagnostic package now exists; repeatable spawns,
  starting squads and observable targets should be part of worker delivery.

These are observations from the current docs, issue handoffs and integration log,
not a measured throughput study. Staffing targets below are planning estimates.

## Family owners deliver through the native runtime

One owner takes a family from source audit through models, pose banks, materials,
native AI/receivers, installation, private build and arena evidence. The owner
may use the established proxy path or implement P2-specific behavior. They record
which level is delivered; they do not need root to implement the C++ half for them.

Claim the issue, intended milestone and file scope before starting, as AGENTS.md
requires. The same scoped issue can cover several implementation steps. Create
another issue when scope or ownership actually changes, not for every fixture.
Owners may continue through the claimed milestone without a new permission check
after each commit. While a candidate awaits merge, continue independent work on
the same branch or a clearly identified dependent branch. Freeze the submitted
commit and QA package; mark later work with its own commit.

Workers may edit their own family modules, tests, profiles and launchers and
include narrow additive CMake/setup/update/draw/reset registration in a private
native worktree. Include those hook hunks in the candidate instead of requesting
that root reimplement them. Preserve existing IDs; record any new reservation in
the coordination issue and check for conflicts before implementation and merge.

## Review follows the affected behavior

| Change | Worker authority and review |
|---|---|
| Family modules, profiles, material tuning, tests, private fixtures | Owner implements and validates; ordinary review at delivery |
| Additive family hooks using existing interfaces | Owner includes complete patch; integration checks collisions/order in the combined candidate |
| New converter capability with unchanged defaults | Owner or toolchain lane supplies an opt-in implementation and baseline evidence; focused toolchain review |
| Generic physics/damage, captain states, manager/heap lifetime, save/reward protocols, converter defaults | Identify the affected contract early; a relevant engine owner/peer reviews the semantic change before shared integration |
| Maintained branch, shared build directory, player release or fixed QA package | Single integration writer; immutable delivered packages |

A request for specialist review is not a request for root to write the code.
Known lifecycle gaps can remain disabled in an experimental candidate with clear
limits. They must be resolved before enabling the affected production path. For
example, Demon #242's scene lifetime and external-transition physics questions
remain real engineering work under this policy.

Do not edit a neighbor's live checkout. Do not push the separate native
repository to a guessed remote. A worker may export its own native source into
its own root branch using explicit source/destination paths and submit a complete
source-only candidate. Root applies that candidate to the maintained snapshot.
Private builds can run in parallel within each host's CPU/memory budget; only
the shared build directory has a single writer. Heavy builds and runtime QA can
be spread across the user's other machines.

## Integration becomes merge, combined validation and packaging

The ready handoff is short: issue/owner, exact base and candidate commits, changed
shared hooks, delivered acceptance level, test/build results, one runnable private
fixture with provenance, and remaining gaps. Link detailed logs rather than
repeating them in every status comment.

Use these statuses in the current family issue: **working**, **ready for review**,
**ready for QA**, **blocked on a named dependency**, or **parked**. A blocker names
the needed API/behavior and owning issue, not simply "waiting on native/root."
Milestone completion and actionable blockers trigger coordination; routine
healthy progress does not need close polling.

Root takes independent ready candidates in a batch, resolves conflicts, runs
the combined build and tests for affected shared behavior, then publishes a
fixed candidate. Reuse worker evidence tied to the exact commit; rerun a test
when a merge changes its inputs, a failure requires investigation, or the
combination introduces an untested interaction. Do not replay every successful
conversion and fixture by default.

Independent QA concentrates on natural gameplay, mixed families, teardown,
performance and campaign boundaries. A worker's scoped runtime smoke should
already pass before it reaches QA. A single QA session need not manually sign
off every pose bank; visual evidence and peer review can run per family.

Close delivered child issues against their stated acceptance. Leave family
umbrellas open for unfinished behavior. Do not inflate a source-only or display
milestone into complete-family status, or keep unrelated workers idle behind it.

## Suggested wider allocation

Start with roughly **8–10 implementation owners**, plus independent QA and one
integration owner. This is a suggested project-wide allocation across sessions
and machines, not a claim about any app's concurrency limit or measured hardware
capacity. Increase it when ready work is landing faster than it accumulates.

- Retain the existing Kimi owners for Bulborb variants, beetles, Breadbugs,
  Mamuta and Bulblax; permit end-to-end native work within their claimed family.
- Retain the hard-enemy task for Demon/Sarai; Groink revival stays parked under
  the user's earlier direction.
- Split the root-owned continuation work into independent aquatic/hopping,
  Blowhog, and Honeywisp/ambient scopes where shared resource/FSM ownership is
  disjoint. Check current claims before assigning any new worker.
- Reserve an engine/toolchain owner for reusable animation/material and
  receiver/lifecycle work. This owner reviews cross-family semantics and builds
  missing shared capabilities, rather than owning every family's implementation.
- A cave/content owner can advance room/navigation/content integration in
  parallel with enemies. Ready-family roster boundaries keep that work concrete.

The exact allocation is flexible: combine small scopes, or replace one family
slot with cave work. New independent families can include Water Dumple/Wogpole,
Crawmad, and the separate ground-invertebrate/disguise groups when claimed.
Waterwraith/Titan and other multi-system bosses need explicit shared dependencies;
they do not become cheap merely because another session is available.

Success means more playable families and shorter ready-to-merge waits, not more
simultaneous audits. Review the queue after the next two combined candidates:
if hooks still wait, move that implementation/review authority to the relevant
owner; if QA or build capacity backs up, allocate a machine/worker there.

No new sessions or family claims were created by this workflow review. Existing
owners retain their work. The AFK runner was observed paused; this policy does
not resume it. Its saved prompt should be aligned before its next activation.
