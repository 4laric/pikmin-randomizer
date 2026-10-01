# Multi-floor checkpoint identity for P1 cave saves (issue #132)

Lane `cave-multifloor-identity`, issue #132 (P2 campaign saves/story
progression). Implementation owner: Codex through shared account `4laric`;
executing worker muse-l61 (generation 2). This slice closes the save-review
floor-{1,2} gap: the transfer schema and supervisor framing now carry floor
ids 1..N with a per-floor revision chain, while every legacy rule and byte
format is preserved. No level run here; P1 save transport stays UNTESTED.
No ADMIT, no admission-ledger writes. Issue #132 stays OPEN.

Excluded: #468 (unassigned per-treasure hazards), carry-state (#488 scope),
day/surface state and durable saves beyond transfer+ledger (recorded as
remaining work, not expanded into).

## Owned files (exact)

- `native/pc_port/pc_p2_cave_transfer.h` (shared: schema + floor-id range)
- `experimental/pikmin2_campaign.py` (shared: validate/transition/entry
  framing for floor ids beyond 2)
- `tests/test_p2_cave_multifloor_identity.py` (new)
- `docs/PIKMIN2_CAVE_MULTIFLOOR_IDENTITY.md` (this spec)

`native/` names refer to the private native worktree, never the shared
checkout. No other files. Shared-file edits REQUIRE existing-owner review
(#186 request filed from the save-review draft pattern; never merge shared
changes without approval).

## Wire format (native header, additive only)

The species-schema versions are untouched (`P2_CAVE_{ENTRY,TRANSFER}_1..3`;
an unknown version is still rejected explicitly, never treated as latest).
The legacy floor range {1,2} and every parse clause are untouched.

A chained multi-floor payload keeps the same species-schema header, carries
the real header floor 1..`P2CaveMaxFloors` (16: covers the 9-floor P0 maximum
with headroom), and appends exactly one identity line:

```
P2_CAVE_CHAIN <floor> <revision>
```

`<floor>` repeats the header floor; `<revision>` is this floor's checkpoint
revision (non-negative). The ordered checkpoint sequence across floors is the
chain; the wire carries the current link. Revision monotonicity belongs to
the supervisor, which holds the prior checkpoint.

Old-reader behavior (bump rule preserved on both paths):

- A chained payload is trailing data to an old reader: rejected explicitly.
- An unchained floor beyond 2 still fails the legacy {1,2} range: rejected
  explicitly as a header error.
- Payloads without the chain line parse byte-identically to before
  (`p2_cave_parse` delegates with maxFloor=2, no chain).

New API (all in the header, engine-free):

- `p2_cave_parse_chained` / `p2_cave_parse_entry_chained` /
  `p2_cave_parse_transfer_chained`: parse with floor 1..16 plus the required
  chain line; any malformed tail reports `"trailing data"`, the same clause
  an old reader reports.
- `p2_cave_format_chained_transfer` / `p2_cave_format_chained_entry`:
  base payload plus the current revision-chain link. Callers pass in-range
  values; the supervisor enforces the cave's floor count and monotonicity.

## Supervisor framing (`experimental/pikmin2_campaign.py`)

`validate(state, floors=2)`, `transition(..., floors=2)`,
`entry_text(state, token, floors=2)`, `load(path, content, floors=2)`.
Defaults preserve the legacy Emergence loop exactly (byte-identical entry
text for floors 1-2; `transition` on floors=2 behaves as before).

Extended rules (floors=N, 2 <= N <= 16):

- Floor must satisfy 1 <= floor <= N; revision must satisfy 0 <= rev <= N.
- Phase rule unchanged in shape: revision == floor-1 while active,
  revision == floor otherwise; `exited` requires floor == N.
- `transition` accepts an optional single trailing `P2_CAVE_CHAIN f r`
  line; it must repeat the header floor and equal the checkpoint revision
  (`Cave revision chain broken` otherwise). Beyond floor 2 the chain line
  is mandatory, mirroring the native legacy parser. Legacy tails fail
  closed exactly as before.
- Status: `failed` on empty squad/zero health; `active` while floor < N
  (advancing to floor+1, revision+1); `exited` on floor N.
- Receipt rules (never regress, allowlist for new, bounded values),
  species-increase rules, and the floor-2 purple +10 Candypop headroom are
  unchanged: `after[purple] > before[purple] + (10 if floor == 2 else 0)`.
- `transfer_schema` still accepts only `_1.._3`.

## Verification

- `tests/test_p2_cave_multifloor_identity.py`: 21 tests (schema bump
  preserved, default-range rejection, trailing-data rejection, 7-floor
  round trip with revision chain, purple headroom on floor 2 only,
  revision monotonicity, floors-param bounds, legacy byte-identical text).
- Existing `tests/test_pikmin2_campaign.py` +
  `tests/test_pikmin2_campaign_bulbmin.py`: 12 passed, unchanged.
- Existing native `tools/test_p2_cave_transfer.cpp` asserts: run
  unmodified against the new header -> `PASS P2_CAVE_TRANSFER`
  (unknown-version, floor-3, trailing-data and bump asserts intact).
- Private native build (leased): full `pikmin_pc` link plus
  `ninja -n` -> `ninja: no work to do.` (evidence in the lane out dir).

## #186 review request (filed, pending approval)

Posted on issue #186 following the save-review lane exact draft pattern,
adapted to this slice: sign-off requested on (1) the transfer-header
chained range + chain line + bump preservation with existing asserts
unmodified; (2) the supervisor `floors` parameter with unchanged defaults
and monotonicity/receipt/purple-headroom rules; (3) the rule that these
shared edits are not integrated anywhere until approval. Evidence file:
`out/review-186-request.json` (comment URL + body hash).

## Remaining work (explicitly out of scope)

- Engine consumer adoption: `native/pc_port/pc_p2_cave.cpp` still parses
  entries/transfers with the legacy path, so a floor-3+ chained entry is
  fail-closed there until its owner adopts the chained parser (recorded,
  not implemented: that file is not owned here).
- P1 level runs against the seven P0 cave packets with WRITE/header/
  RESTORE/PASS evidence (needs the provider + runtime dependencies).
- Day/surface state, durable saves beyond transfer+ledger, carry-state
  (#488), confirm-dialog path: unchanged gaps from the save review.
