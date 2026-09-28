# P1 Challenge Impact — P0 source audit and import contract (issue #565)

Lane `p1-challenge-impact`, worker muse-l76 (Muse contributor; implementation
owner Codex through shared account 4laric). **Expansion P0 candidate**:
integrator prioritizes existing work; cherry-pick only the reserved changes
into the chosen integration branch, never merge this worktree's history into
the species wave. No claim of playability; full content issue stays OPEN.

Reserved files (only these):

- `experimental/content_lanes/p1-challenge-impact.py` — isolated audit adapter
- `tests/content_lanes/test_p1_challenge_impact.py` — 13 focused tests
- `docs/content_lanes/p1-challenge-impact.md` — this spec

## 1. Source identity

| Field | Value |
|---|---|
| Level key | `challenge:impact` (native area 0, shared with campaign impact) |
| Source entry | `stages/chal0.ini` (StageInfo index 16) |
| Assets root (read-only) | `C:\Users\alari\bbft\dist\cohesion\pikmin\assets` |

Actual SHA-256 (local legal source, measured 2026-09-16):

| File | SHA-256 | Bytes |
|---|---|---:|
| `dataDir/stages/chal0.ini` | `6cfb79ea204ce5f5e032c5d6f250f820300e60da13ec78ffb7f7270b304c51f9` | 2475 |
| `dataDir/stages/chal0/default.gen` | `eeb58bacfb1dc7235a99c95ac6d5e019ed09547aab066cf8f9132edc43ff9972` | 14665 |
| `dataDir/stages/chal0/plants.gen` | `5c317737c4427c39d9631b01f5aa1a0eeb8481dc5b67990afc6a7772050803ff` | 4944 |
| `dataDir/courses/practice/practice.mod` | `873abade86d4fb7f40633993c206a5a97ebcccf3b756a5f783fb031908f2ee0a` | 4554426 |

## 2. Decoded definitions (actual file values)

`chal0.ini`: `navi_start 0.0 0.0`; `map_file courses/practice/practice.mod`
(shared practice terrain — level keys must stay qualified downstream);
`day_multiply 0.8`; `dayMgr` with 5 timesettings (night/morning/day/evening/
movie, count verified against `numsettings`); one `new_room` (index 0,
radius 4.0, centre 0,0).

Generator framing (existing `scripts.preview_pikmin2_room.records`
splitter; raw 4-byte type tags only, no actor-count semantics):

- `default.gen`: 80 records — `meti` 10, `ikip` 3, `tlep` 53, `iket` 11,
  `krow` 1, `ssob` 2.
- `plants.gen`: 30 records — `tnlp` 30.

Weighted definition rows remain definitions: the adapter emits counts and
hashes only, never runtime placements.

## 3. Floor coverage

Single-course layout: no floor list, no day-specific generator files — only
`default.gen` + `plants.gen` (matches the lane plan's "—"). Complete coverage
is the one course plus its full closure above. No init/day-specific files
exist to cover.

## 4. Import contract

`audit(assets)` returns level key, native area, stage-info index, source
path, decoded definitions, hashed closure, per-file framing summaries and
the floor/coverage record. `decode_stage_ini` rejects missing/malformed
`navi_start`, `map_file`, `day_multiply` and timesetting-count mismatch with
`ValueError`. Any absent file (ini, generator, geometry, assets root) raises
`MissingPrerequisite` naming the exact expected rel paths. Identity is
cross-checked against `experimental.levels.BY_KEY['challenge:impact']` and
the checked-in lane-plan entry (source, issue 565, area 0, index 16, owned
files) in tests.

## 5. Exact native/framework blockers (for P1, not waived)

- Story-destination navigation/persistence/checks: #100 (ten-destination map,
  level-key-qualified saves, new location IDs).
- Timed/scored AP Challenge campaign contract: #52 (roster/sprays/timers,
  retry/reconnect semantics).
- Campaign resume/save primitives: #6.
- Enemy admission for any unadmitted generator species before promotion
  (preparatory metadata is unaffected).
- P1 Challenge preview startup already exists (`scripts/
  preview_challenge_level.py`, `docs/CHALLENGE_LEVELS.md`); the host `chal0`
  fixture is story-mode exploration, not timed-mode evidence. Do not repeat
  preview-only import.

## 6. Validation

- `tests.content_lanes.test_p1_challenge_impact`: 13/13 OK (synthetic trees
  only; malformed/missing-input boundaries; plan/registry sync). Log:
  `output/workflow/content-expansion/p1-challenge-impact/tests-p0.log`.
- `scripts/check_content_import_lanes.py`: PASS (53 lanes intact; untouched).
- `tests.test_content_import_lanes`: 15/15 OK.
