# Cave save/checkpoint provider contract review for P1 phases (issue #132)

Read-only contract review. Implementation owner: Codex through shared account
`4laric`; executing worker muse-l62 (generation 2). No implementation, no
builds, no shared edits, no ADMIT. All six runtime gates UNTESTED; no level
acceptance claimed. Issue #132 stays OPEN.

## 1. What was audited (read-only, pinned worktree @ 33fa7a91)

- `experimental/pikmin2_cave_restart_runtime.py` ? lane-11 two-process
  write/read validator (entry squad 16 red + yellow + purple + Bulbmin,
  phase env `P2_LANE11_PHASE`, exit 42 on write, `PASS P2_LANE11_RESTORE`).
- `engine/tools/test_p2_cave_transfer.cpp` ? 8 transfer-schema asserts
  (schemas 1-3, old-reader rejection, trailing-data rejection, bump rule,
  round trip).
- `engine/pc_port/pc_p2_cave_transfer.h:17-121` ? the exact wire format both
  use (reviewed against the main native checkout, read-only).
- `native/pc_port/pc_p2_cave.cpp:123-169` ? `pc_p2_cave_checkpoint`
  (reviewed against the main native checkout, read-only).
- `experimental/pikmin2_campaign.py:32-155` ? supervisor
  validate/entry_text/transfer_schema/transition.
- The seven completed-P0 cave packets (floor/roster metadata the save
  contract must preserve): tutorial_2 (#152, 9 fl), forest_2 (#155, 5),
  forest_3 (#156, 7), forest_4 (#157, 7), yakushima_1 (#158, 5),
  yakushima_2 (#159, 6), yakushima_3 (#160, 7).

## 2. Exact save contract: checkpoint write/read/validate sequence

### 2a. Write (engine, `native/pc_port/pc_p2_cave.cpp:123-169`)

1. Gate on `safeTime()` (:124); captain must be alive (:125).
2. Living-squad census (:127-136): skip dead; dying/dead marks `busy`;
   swallowed/bury/grow/stuck-to-non-pellet marks `busy`; species outside the
   schema range calls `invalid()` (hard abort, :134).
3. Sprout-head busy rule (:137-138): unplucked sprouts block a healthy
   captain with a whistle-out notice; a near-dead captain (health <= 1)
   proceeds with health 0 and an emptied squad (:141).
4. Pod presence required (:143-144); proximity rule (:145-149): hole/geyser
   anchor containment, else within 150 units of the Pod, plus
   `NAVISTATE_Walk` ? unless the run already failed.
5. Confirm dialog (:150-157): "Descend" (floor 1) / "Leave cave" (floor 2)
   with survivor count; warns uncollected treasure stays behind and that
   squad + delivered treasure save together. (The lane-11 fixture passes
   `confirm=false`; the F6 prompt itself is unexercised.)
6. Atomic persist (:158-166): payload
   `P2_CAVE_TRANSFER_<schema>\n<token>\n<floor> <health> <count>\n` plus one
   `<species> <maturity>` line per survivor, written to
   `p2-cave-transfer.tmp` then `rename()`d to `p2-cave-transfer.txt`;
   any I/O shortfall aborts with a stay-and-retry notice.
7. `P2_CAVE_TRANSFER floor=.. survivors=.. health=.. failed=..` marker (:167);
   `completed=true` (:166).

### 2b. Wire (engine-free header, `engine/pc_port/pc_p2_cave_transfer.h`)

- Entry vs transfer headers differ only in name/direction (:17-23); both
  carry the squad. Schema 3 required for Bulbmin; old readers reject
  explicitly (:22-23, :101-111).
- Parse clauses (:59-91): header (schema 1-3, 32-hex token, floor 1-2,
  health in (0,1], count 1-100) else `"header"`; survivors (species
  in-schema, maturity 0-2) else `"Pikmin"`; anything trailing else
  `"trailing data"`. Cap: 100 survivors (:25).
- Transfer schema bump (:104-111, :113-120): never below the entry schema,
  never below any survivor's required schema; formatted at precision 9.

### 2c. Read + validate (supervisor, `experimental/pikmin2_campaign.py`)

- `validate` (:32-62): checkpoint schema 1, 64-hex content identity,
  revision 0-2, floor 1-2, health in [0,1], survivors required iff not
  failed, phase rule (revision = floor-1 when active, floor when exited;
  exited implies floor 2), receipts <= 1024 keys with bounded values.
- `entry_text` (:103-107): minimal schema covering the squad; exact
  `<floor> <health:.9g> <count>` framing the engine parses.
- `transition` (:120-155): token must match; transfer floor must equal the
  checkpoint floor; count bounded by the staged squad; every survivor's
  species in-schema; receipts never regress and new receipts need the
  allowlist; red/yellow/blue never increase, purple at most +10 on floor 2
  (Candypop conversion headroom); status failed (empty squad or zero health,
  squad dropped) / active (floor 1, advances to floor 2) / exited.
- Ledger (`ledger_text`/`read_ledger`, :83-95): `P2_ECONOMY_1` receipt map
  persisted beside the transfer as `p2-economy.txt`.
- Two-process proof shape (`pikmin2_cave_restart_runtime.py:138-160`):
  `P2_LANE11_WRITE ok=1` + exit 42, transfer header `P2_CAVE_TRANSFER_3`
  with `\n2 0.625 19\n`, `P2_CAVE_RESTORE species=5 maturity=0`,
  `P2_LANE11_READ bulbmin=1`, `PASS P2_LANE11_RESTORE`, no abort/extinction
  markers.

## 3. Floor/roster state P1 must persist (from the seven P0 packets)

| Cave (issue) | Floors | Unit pools | Roster notes (P0 packet) |
|---|---|---|---|
| tutorial_2 (#152) | 1-9 (9) | 8 pools (4/8 share hit224) | 79 enemy tokens, 13 treasures |
| forest_2 (#155) | 1-5 (5) | 5 pools | catalogued roster, 5 floors |
| forest_3 (#156) | 1-7 (7) | 7 pools | 10 exact + 3 variant + 6 carrier-candidate tokens, 5 treasures |
| forest_4 (#157) | 1-7 (7) | 7 pools | 28 enemy + 7 treasure tokens |
| yakushima_1 (#158) | 1-5 (5) | 5 pools | 6+8+5+6+5 enemy rows, 8 treasures |
| yakushima_2 (#159) | 1-6 (6) | 6 pools | pools/rosters/treasures + cap tokens |
| yakushima_3 (#160) | 1-7 (7) | 7 pools | floor/token inventory + gates |

The save contract must therefore preserve, per checkpoint: cave identity
(content hash), floor id, living-squad species/maturity list, captain health,
32-hex token, and the receipts ledger ? while the P0 floor/roster metadata
above tells the provider what each floor may legally contain on re-entry.

## 4. Gaps the provider owner must close (findings, not implementation)

1. **Floor identity is capped at {1,2}** (`pc_p2_cave_transfer.h:71`,
   `pikmin2_campaign.py:41`; revision 0-2 two-floor model at :50-51), but the
   seven caves run 5-9 floors. A multi-floor checkpoint identity (floor id
   beyond 2, revision chain per floor) is a P1 prerequisite; the current seam
   only proves the Emergence 2-floor loop.
2. **Day/surface state is outside the seam**: day start/end, sunset losses,
   sprout regeneration and surface time (#132 acceptance 1) have no transfer
   field; `pc_p2_cave_tick` freezes the world clock (:174) rather than saving it.
3. **Durable saves beyond the transfer+ledger pair** (#132 acceptance 2-4):
   areas, captains, debt/equipment, Louie/President progression, quit/crash
   recovery, extinction/abandonment/migration have no provider; the transfer
   covers squad+health+floor+token only.
4. **Carry state at checkpoint time is #488's scope**, explicitly excluded
   here (see section 6).
5. **Confirm-dialog path** (`confirm=true`, :150-157) is unexercised; only the
   guarded `confirm=false` handoff is proven.

## 5. Minimal provider plan (files, order, validation)

Files (all existing; owner wires, this review changes none):
`native/pc_port/pc_p2_cave.cpp` (checkpoint + tick),
`engine/pc_port/pc_p2_cave_transfer.h` (wire, engine-free),
`experimental/pikmin2_campaign.py` (supervisor validate/transition/ledger),
`experimental/pikmin2_cave_restart_runtime.py` (two-process proof shape),
`engine/tools/test_p2_cave_transfer.cpp` (schema asserts).

Order: (a) extend floor/revision identity past 2 with audit998 multis
floor fixtures; (b) add day/surface + durable-save fields behind new
transfer minor version with old-reader rejection per the bump rule;
(c) supervisor transition guards for the new fields (same fail-closed
style); (d) per-cave P1 runs against the seven P0 packets above;
(e) carry-state seam only through the #488 owner.

Validation: transfer asserts stay green; new fields get old-reader-rejection
asserts; every P1 run must show WRITE ok=1, header/token/floor match,
RESTORE with the staged squad, and PASS with no abort/extinction markers;
the read-only checker in this review (`experimental/
pikmin2_cave_save_contract.py`, 6 tests + 15 subtests) screens logs for the
cited markers and rejects malformed transfers.

## 6. Non-overlap statement vs the #488 reentry review

Issue #488 (`cave-reentry-provider-contract-review`) owns **carry-state
re-entry for cave50/51 cleanup_reentry**: its reserved files are
`experimental/pikmin2_cave_reentry_contract.py`,
`tests/test_pikmin2_cave_reentry_contract.py`,
`docs/PIKMIN2_CAVE_REENTRY_PROVIDER_REVIEW.md`, and its scope is the exact
follow-on contract that closes cave50/51 cleanup_reentry for carry state
(per the planning proposal record; its review document was not present at
audit time). This review owns the **general P1 save contract for the seven
completed-P0 cave lanes** (reserved files
`experimental/pikmin2_cave_save_contract.py`,
`tests/test_pikmin2_cave_save_contract.py`,
`docs/PIKMIN2_CAVE_SAVE_PROVIDER_REVIEW.md`). Carry state in transit at
checkpoint time is #488 territory and is excluded from the contract above;
squad/health/token/floor/receipts persistence is this review's territory and
is excluded from #488. Neither review edits shared fixtures.

## 7. #186 review request draft

> To lane-11/shared-semantics owners (#186): please review the cave
> save/checkpoint provider contract for P1 phases (issue #132), published at
> `docs/PIKMIN2_CAVE_SAVE_PROVIDER_REVIEW.md` in this review lane. Exact
> contract seams needing your sign-off before any provider implementation:
> (1) `native/pc_port/pc_p2_cave.cpp:123-169` checkpoint guards + atomic
> write; (2) `engine/pc_port/pc_p2_cave_transfer.h:40-121` wire clauses and
> the schema-3 bump rule; (3) `experimental/pikmin2_campaign.py:120-155`
> transition guards (token/floor/receipts/species-increase) and the floor-2
> purple +10 headroom at :149; (4) the floor-{1,2} cap flagged in section 4
> item 1, which needs your decision on multi-floor identity before P1 runs.
> No shared edits are proposed in this review; implementation stays with the
> future provider owner. Reply with approve / request-changes on this issue.

## 8. Checker

`experimental/pikmin2_cave_save_contract.py` extracts the cited markers
(`P2_LANE11_WRITE`, `P2_CAVE_TRANSFER_3`, `P2_CAVE_TRANSFER floor=`,
`P2_CAVE_RESTORE`, `P2_LANE11_READ`, `PASS P2_LANE11_RESTORE`), validates a
transfer payload against the wire clauses, and checks write/read/validate
order ? stdlib only, no engine import. `tests/
test_pikmin2_cave_save_contract.py`: 6 tests + 15 subtests, all passing.
