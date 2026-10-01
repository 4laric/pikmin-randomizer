# P2 challenge persistence/natural-acceptance provider audit (#136)

Lane `p2-challenge-persistence-provider-pin-discovery` (tooling, generation 2).
Bounded coordinator prerequisite recovery for the challenge-0 consumer
`p2-challenge-ch_mat_route_rover-p1` (#561), request
`8ca13176ff5db693346ccde96cafd041c3e975087be0b9d00accd1778a8c44e3`, report
`d5b1fa4070774c6ea631974c33c2915236dbf7eb1b6d458e9e880776631e701a`.
Root-only: no native/shared/CMake/manifest edits, no runtime, no ADMIT.

## What this audit found (declared vs landed)

The challenge framework contract (#136) DECLARES that save/unlock persistence
for challenge clear flags and highscores is supplied by the #132 surface-saves
provider:

- `experimental/pikmin2_challenge_framework_contract.py:134` (pin
  `b9bb55f0`): `'surface_saves_132': 'Day/save persistence incl. challenge
  clear flags and highscores (PlayCommonData).'`
- `experimental/pikmin2_challenge_framework_contract.py:158`: owner assignment
  `saves_unlocks='#132'`.
- `docs/PIKMIN2_CHALLENGE_FRAMEWORK_CONTRACT.md:50`: the contract lists
  "unlock persistence wiring (#132)" under **Unsupported (no port evidence -
  do not claim)** (line 46).

The three landed #132 save-progression contracts contain **zero**
challenge/highscore/unlock anchors (verified absent this turn):

- `docs/PIKMIN2_SURFACE_SESSION_CONTRACT.md` (`#132` @ `7b6d25df`,
  sha256 `12c4a76a...`)
- `docs/PIKMIN2_CAVE_SAVE_PROVIDER_REVIEW.md` (`#132` @ `8aaf6cf6`,
  sha256 `b43be487...`)
- `docs/PIKMIN2_SAVE_DAYCLOCK_ANCHOR_AUDIT.md` (`#132` @ `4fff74c7`,
  sha256 `7a3f7b85...`)

Conclusion: the challenge persistence adapter is a **missing provider**. #132
is a completed backlog epic (done lanes: cave-save-contract-review,
surface-session-provider-contract, provider-save-dayclock-anchor-audit,
overworld-save-progression-contract, cave-multifloor-identity) and is therefore
**not an input producer**; no live lane produces this runtime slice.

## Missing provider + owner

- Provider key: `challenge_persistence`.
- Missing input: challenge-stage save/unlock persistence adapter - challenge
  clear flags, highscores and saved stage unlocks (PlayCommonData) wired
  between the challenge stage flow and the port save layer.
- Concrete owner: new bounded lane `p2-challenge-persistence-wiring` under
  issue **#136**, root-only first slice, consuming the #132 contracts and the
  #136 framework contract read-only. Any native save-layer hookup needs the
  #132 save owner contract plus the **#186** shared-hook review; route through
  coordinator **#570**.

## First bounded executable slice

- Item `p2-challenge-persistence-wiring-v1` (issue #136, implementation,
  existing_content, heavy false). Owned files:
  - `experimental/pikmin2_challenge_persistence.py`
  - `tests/test_pikmin2_challenge_persistence.py`
  - `docs/PIKMIN2_CHALLENGE_PERSISTENCE.md`
- Deliverable: map the 30 challenge stages to their clear-flag/highscore/
  saved-unlock persistence keys against the landed #132 save contracts and the
  #136 framework contract; fail closed on drift; name the exact native
  save-layer owner and #186 review needed for engine hookup.
- Downstream consumer: **#561**
  `p2-challenge-ch_mat_route_rover-p1`. Its boot/staging gap is resolved
  (#699) and its content-loading input has a live producer
  (`challenge-content-loading-validate-land-native`, #701, landing #694);
  persistence/natural acceptance is the remaining named input.
- Non-overlap: none of the owned files are owned by #561, #132, #136, #694 or
  #701 lanes; the audit asserts this at runtime.

## Checker

`experimental/pikmin2_challenge_persistence_provider_audit.py` loads every
pinned blob read-only by exact commit, verifies the object id and content
sha256, asserts the four required framework anchors by file:line, proves the
challenge anchors are absent from the three #132 docs, and emits a
machine-readable verdict with the provider decision, the first slice and the
downstream consumer. Any drift fails closed with `AuditError`. The audit for
the real pins is also exercised by a repo-present integration test.

## Captain safety (#632)

No runtime run in this lane (tooling audit). The proposed slice is root-only
and executes no runtime fixture. Any future runtime spec must adopt
`scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`) or a
tested equivalent with orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED
exit, a parked captain, no blanket invincibility, and recorded guard/source
hashes.

## Gates

All six runtime gates (`identity_spawn`, `movement_animation`,
`attacks_receivers`, `death_corpse`, `transport_reward`, `cleanup_reentry`)
remain UNTESTED. No gameplay acceptance, no ADMIT.