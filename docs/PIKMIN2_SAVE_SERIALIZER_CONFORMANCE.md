# Durable save serializer conformance (#712)

Lane `provider-save-serializer-conformance`, issue #712 (OPEN), parent #605,
planner #570. Implementation owner: Codex through shared account 4laric.
Root-only tooling producer. No native worktree, no build, no runtime, no
shared/family/native edits, no save-format change, no ADMIT. All six runtime
gates UNTESTED. Captain safety #632 is N/A (no runtime).

## 1. #658 save-block pins re-verified (read-only)

Research tree read-only:
`native/pikmin2-research/src/plugProjectKandoU/gamePlayDataMemCard.cpp`
(1425 lines as inspected this generation). Each pin was re-checked by reading
the exact line and matching the `void <Symbol>(` definition on it; no pin is
assumed from the #658 report.

| File:line | Symbol | Role | Verdict |
|---|---|---|---|
| gamePlayDataMemCard.cpp:39 | `PlayData::write` | durable save entry | PRESENT |
| gamePlayDataMemCard.cpp:707 | `PlayData::read` | restore entry | PRESENT |
| gamePlayDataMemCard.cpp:1346 | `OlimarData::write` | captain block write | PRESENT |
| gamePlayDataMemCard.cpp:1360 | `OlimarData::read` | captain block restore | PRESENT |
| gamePlayDataMemCard.cpp:1372 | `CaveSaveData::write` | cave payload write | PRESENT |
| gamePlayDataMemCard.cpp:1411 | `CaveSaveData::read` | cave payload restore (size-guarded) | PRESENT |

Observed signatures this turn:

- `void PlayData::write(Stream& output)` (:39)
- `void PlayData::read(Stream& input)` (:707)
- `void OlimarData::write(Stream& output)` (:1346)
- `void OlimarData::read(Stream& input)` (:1360)
- `void CaveSaveData::write(Stream& output)` (:1372)
- `void CaveSaveData::read(Stream& input, u32 size)` (:1411)

Grounded body facts used by the contract below:

- `PlayData::write` opens a version text group (`* Version *`) and writes
  treasure/debt/… fields; `PlayData::read` reads the version first and
  tolerates a mismatched version ID.
- `CaveSaveData::write` writes formation Pikmin, time, course index, cave ID,
  floor, waterwraith state, then version-gated fields; `CaveSaveData::read`
  takes an explicit `u32 size` and only reads the newer field when
  `if ('j009' <= size)`. This is the only size-guarded block of the six.
- `OlimarData::write`/`read` are the two flag bytes (captain block).

No pin required an ABSENT verdict this generation; the `verify_pins`
implementation still returns an explicit ABSENT row (never a silent pass) if
the research tree or a line is unavailable.

## 2. Conformance contract

Contract module: `experimental/pikmin2_save_serializer_conformance.py`.
Abstract block shapes mirroring the observed field order:

- `playdata`: `version`, `treasure_count`, `debt_flags`, `area_records`,
  `squad_records`, `captain_records`.
- `olimardata`: `flags`.
- `cavesavedata`: `formation`, `time`, `course_idx`, `cave_id`, `floor`,
  `waterwraith`, `gated`.

Round-trip rules (per area / per squad / per captain):

1. `serialize(kind, block)` is deterministic (sorted keys) and refuses an
   unknown kind or a block missing a required field.
2. `parse(kind, data, size)` refuses empty input, non-bytes input, malformed
   JSON, a kind mismatch, malformed fields, and any input exceeding the
   declared `size` guard.
3. For `cavesavedata`, `gated` fields are admitted only when the declared
   `size` covers them, mirroring the source `if ('j009' <= size)` gate.
4. `round_trip(kind, block, size)` is `True` only when the parsed fields equal
   the input exactly; a mutated field must not compare equal.

Size-guard / malformed negatives covered by tests: empty, `bytearray()`,
non-bytes, truncated payload, oversize payload, kind mismatch, missing field,
unknown kind.

These are contract-level (abstract block) semantics. They do NOT change or
redefine the retail card format, and this slice performs no engine wire.

## 3. #186 shared-owner review request (before any engine wire)

Exact request, as emitted by `review_request()`:

> Review requested of #186 (shared-owner review): independent per-area /
> per-squad / per-captain save/restore semantics extending the audited card
> format at PlayData::write:39/read:707, OlimarData::write:1346/read:1360 and
> CaveSaveData::write:1372/read:1411 (size-guarded), before any engine wire.
> No save-format change is proposed or made by this slice.

No such review or edit is performed here. #132 remains the saves/progression
owner for any actual wire.

## 4. Downstream consumers

Named and served by this registry: #132, #112, #68, #533, #550, #154, #161.
#132 and #112 stay OPEN; this slice is a producer input, not acceptance.

## 5. Evidence / validation

- Focused tests: `tests/test_pikmin2_save_serializer_conformance.py`, 11 tests
  green (`py -3.12 -m unittest tests.test_pikmin2_save_serializer_conformance`).
- Pin re-verification and test output recorded in the lane handoff evidence.
- All six runtime gates UNTESTED; no build/runtime/ADMIT in this slice.
