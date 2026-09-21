# Review packets (#186)

A review packet derives a #186 verdict (APPROVED or CHANGES_REQUIRED per gated item)
from committed git objects. It is declarative JSON, evaluated by
`workflow/review_packet.py`. No packet code runs. A packet never approves on its own:
only the controller turns a verified evaluation into an approvals-ledger decision.

## Where a packet lives

Commit it under `tools/review_packets/<schema>.json` in the workflow checkout, starting
from `tools/review_packets/template.json`. Packets are always read from a commit.
Without `--commit`, `HEAD` is used, and it is refused while the working copy of that
path differs from `HEAD`. `verify` evaluates any such commit. `repin`, `request` and the
controller's decision accept only a packet commit that is on the declared root
integration line (`integration_lines.root` in the controller config), so a packet
variant on a lane branch or a dangling commit can neither re-pin nor decide. With no
root line declared they refuse. A packet's identity is `packet:<schema>@<blob id>`.
That string is the `decided_by` stamped on every decision the packet produces.

`consumers` (the lanes the packet decides for) and `landers` (the integrators who land
on the maintained lines) must both be nonempty.

## Declaring inputs

- **Candidate** inputs (`role: candidate`) have `repo` (a worktree path relative to the
  workspace root), a full `commit` and a `path`. They are read with `git cat-file` at that
  commit and pinned by blob id. An optional `blob` must match. The candidate worktree's
  own working copy is never read, so an uncommitted edit there changes nothing.
- **Maintained** inputs (`role: maintained`) name the consuming line with
  `line: {repo, ref}`. `repo` is the worktree that has branch `ref` checked out, for
  example `{"repo": "output/dsw/native-wave", "ref": "claude/p2-deepseek-wave-native"}`.
  Each read observes the branch tip and records `{commit, blob, region_sha256}`.
  `region: {begin, end}` delimits the reviewed part of the file. The region runs from
  the unique `begin` anchor through the next `end` anchor, normalized to LF line ends
  with trailing whitespace stripped. Without `region`, the whole file is the region.
  Set `optional: true` when the file may be absent on the line.
- A maintained read refuses (`DriftError`) and hashes nothing when any of these holds:
  - the path is dirty, untracked or ignored in the line worktree;
  - the path is inside a nested repository that the line does not track (a gitlink, or
    a directory with its own `.git`);
  - the line worktree has another branch checked out;
  - the file is missing from the line and the input is not optional.

## Declaring items

Each item has an `id`, a `gate` and a `missing_change`. Its fields:

- `candidates`: the candidate inputs it reads. `candidate_tokens` must appear somewhere
  in them.
- `maintained`: the maintained inputs it reads. `required_tokens` must already be in
  their regions.
- `integration_tokens`: must all be in the maintained regions for APPROVED.
- `built_by: true`: use this when the gate is build-relevant. Each present maintained
  path must then be named in a command of the line's `CMakeLists.txt` at the observed
  commit. Line and bracket (`#[[ ]]`) comments do not count, `set_source_files_properties`
  does not list a file, and a path also named in `list(REMOVE_ITEM|FILTER ...)` or with
  `HEADER_FILE_ONLY` is not built. A different build manifest can be set per input with
  `manifest: <path>`. A dirty manifest refuses.

An item is APPROVED only when every integration token is present and no problem was
found. The packet is APPROVED only when every item is.

## Pins and audited re-pins

Maintained pins live only in the registry's `packet_pins` records, keyed by the
packet schema, the input's declaration and the packet's `consumers` and `landers`.
Changing either list therefore needs fresh pins. A packet evaluates only when two
things hold for each maintained input:

- its current blob and region hash equal those of the latest record for that key;
- the recorded commit is an ancestor of the line tip.

Commits elsewhere on the line do not matter. A changed blob does, and so does a
rewritten line (amend, rebase, reset): it needs a re-pin even when the blob is the
same.

```
py -3.12 scripts/workflow_module.py review_packet repin --root <root> --request repin.json --show-diff [--dry-run]
```

`repin.json` is `{packet, input, actor, actor_generation, evidence {path, sha256},
approve, region_diff_sha256}`. `--show-diff` prints the diff between the old and new
pinned regions, and the record stores that diff's sha256. `--dry-run` computes the
diff and its `region_diff_sha256` without authenticating and records nothing. The
actor always authenticates like any reviewer: the command runs inside the actor
lane's own live launch session.

- **Region unchanged** (only bytes outside the region moved, or the line was
  rewritten). Any authenticated lane may record the re-pin, including the consumer.
  The record's approval is `region-unchanged`.
- **Region changed, or a first pin.** The record needs `approve: true` and the
  `region_diff_sha256` of the diff the reviewer read. If the line moved since, the
  refusal prints the current value. The actor must meet all of these conditions:
  - it owns the workstream of, or holds the exact delegated assignment for, a
    declared consumer that holds a shared_hook this packet covers;
  - it is not in the packet's `consumers` or `landers`, and holds no shared_hook of
    the packet's issue;
  - it did not author or produce the commits that touched the path since the old pin
    (the whole bounded history for a first pin or a rewritten line);
  - it did not land an integration receipt for those commits: the receipt's recorded
    lander, its `claimed_lander` or its batch integrator.

  A self re-pin is refused. A touching commit that no lane record attributes counts
  as landed by the declared `landers`. The record stores how many there were.

Hand-editing pins is not possible, because the packet file holds none.

## Verifying and deciding

```
py -3.12 scripts/workflow_module.py review_packet verify --root <root> --packet tools/review_packets/<schema>.json
```

`verify` is side-effect free. It reads the registry through a read-only snapshot and
prints the evaluation. It exits 2 on any refusal, and the JSON error has
`drift: true`.

To get a decision, a lane holding a structured `shared_hooks` dependency (or a
reviewer on its behalf) runs `review_packet request --root <root> --request <json>`
with `{requester, requester_generation, packet, lanes [{key, generation}], hook}`.
This records only a request, and it is refused unless all of these hold:

- the packet commit is on the root line;
- the packet covers the hook. An `item_id` hook must name a packet item. Every file
  of a `files` hook must be an input path of the packet in the same repository
  (`native/` files: the declared native line repository);
- every named lane is a declared consumer that holds the hook;
- a live controller runs a recorded release that contains this evaluator.

Each requester may have at most 3 open requests. A request stores only the packet,
commit, blob, hook id and lanes, and closed requests are pruned after 14 days. Both
`packet_requests` and `packet_pins` live in the registry's meta document. Moving them
to their own document sections would be a separate storage migration.

The controller then evaluates the oldest open request. It checks for open requests at
most once every 30 s and evaluates one request per check. It runs
`approvals.packet_decision`, which refuses in every process except the registry's
running controller. An `item_id` hook is decided on that item alone; a `files` hook
on every item. The evaluation JSON is written under
`<controller output>/review-packets/` and becomes the decision's hashed evidence. The
controller then records a `shared_hook` ledger row (`source: review_packet`,
`decided_by: packet:<schema>@<blob>`) for each requested lane:

- APPROVED becomes `approved`.
- CHANGES_REQUIRED becomes `rejected`, with each missing change as a condition.

A lane is skipped, with the reason listed in the request's `skipped`, when any of
these holds:

- it no longer holds the hook at that generation;
- it is not a declared consumer;
- it approved a pin the decision uses;
- a reviewer's rejection stands at its current pins and no reviewer re-pin postdates
  it.

A drifted, unpinned or uncovered packet marks the request `refused` and records
nothing. So does any other failure on the third attempt, such as a missing repository
or commit. Earlier attempts are retried every 5 minutes. Like any shared-hook
decision, the row holds only at the lane's current pins, and it wakes the blocked lane
once.

## Migrating a legacy packet

Older packets are Python modules that hash working-copy files. Report what their
inputs would return under these rules:

```
py -3.12 scripts/workflow_module.py review_packet_migration --root <root> --legacy <packet.py> \
    --maintained native=native --line native=output/dsw/native-wave@claude/p2-deepseek-wave-native
```

The module is parsed for literal assignments and is never executed. For every input,
the report shows:

- the repository chain and any nested untracked repository;
- whether the path is dirty;
- whether the pin names the claimed commit's blob, uncommitted bytes or
  checkout-converted (CRLF) bytes.

For every item, it shows the refusal reasons at the maintained checkout and what the
consuming line would need.
