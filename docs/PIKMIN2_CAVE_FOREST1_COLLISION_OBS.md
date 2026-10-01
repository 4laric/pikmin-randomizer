# forest_1 P1 criterion-3 collision/routes/births observation (#773)

Bounded runtime observation slice for issue #773 (OPEN, assigned 4laric;
downstream #154 criterion 3). Follows the gen-13 evidence
(prepared/forest1-p1-root/out/gen13-final-report.md): boot PASS, criteria
1/2/4 PASS, criterion 3 UNTESTED for lack of actor-walking observations.
No ADMIT. No ledger writes. All six gates stay UNTESTED unless genuinely
observed; criterion 3 is PASS only if observed, else UNTESTED.

## Method (reuse read-only, observe with a new guarded fixture)

Reuse the gen-13 staged arena + canonical exe pattern read-only: the
P0-derived input package (p2-cave-entry.txt + p2-cave-generate.txt +
p2-cave-runtime-inputs.json), staged geometry, 960x540 centred startup and a
starting squad of 20 reds. Drive actors walking the staged rooms with the new
guarded fixture native/tools/p2_forest1_collision_obs_fixture.cpp (owned),
built under the canonical leased CLI with the live elastic build cap and
adopting scripts/p2_fixture_captain_guard.h (#632, sha256
d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474, read-only).

The fixture observes, with receipt-parseable P2_FOREST1_* markers:
actor births (new live teki identities), collision contact (live actors with
finite positions resting on sampled ground via mapMgr->getMinY), and route
traversal (live actors displaced from first-seen positions). It requires a
live squad plus at least one birth, one contact and one traversal before
emitting PASS FOREST1_COLLISION_OBS (exit 0). Guard runs before every
observation; CAPTAIN_DOWN exits BLOCKED (86) with no PASS. Timeout FAIL (2).

## Files (owned, all new)

- experimental/pikmin2_cave_forest1_collision_obs.py: dependency-free run-log
  reader + chain validator (ENTRY_READY then BIRTH + CONTACT + TRAVERSE then
  PASS, exit 0, no captain-down; fail-closed on malformed/missing input).
- tests/test_pikmin2_cave_forest1_collision_obs.py: 8 focused hermetic tests
  (parse, pass, captain-down/negative, missing-marker, bad-exit, malformed).
- native/tools/p2_forest1_collision_obs_fixture.cpp: replacement-main guarded
  observer described above; no engine/family/shared edits.

## Evidence (leased private build + run)

Recorded in the lane handoff (prepared/forest1-collision-obs-out): configured
+ built pikmin_pc with ninja -n no-work, fixture exe SHA-256, guard self-test
exit 0, negative guard exit 86 (no PASS), and the observed marker log with
births/contacts/traverses plus the reader verdict. Criterion 3 PASS only if
observed; otherwise UNTESTED with the exact defect.
## Observed result (generation 2, leased private build): criterion 3 UNTESTED

Built pikmin_pc + linked fixture in output/forest1-collision-obs-build
(lease-held; ninja -n no-work); fixture exe + guard self-test exit 0 +
negative exit 86 (no PASS). Ran over the gen-13 staged arena
(run-forest1-collision, assets reused read-only) with the #632 guard.

Observed (run-collision2.log, ~20k ticks): P2_CAVE_READY floor=1 survivors=20,
ENTRY_READY, exactly ONE actor birth (teki at 173.6/-143.2, grounded y=0.0),
ONE collision contact (grounded), ZERO route traversals, live squad 0 from the
first check, no captain-down, clean engine shutdown (no fixture PASS/FAIL).

Reader verdict on the real log: UNTESTED (missing P2_FOREST1_TRAVERSE;
births=1 contacts=1 traverses=0). Fail-closed holds on real data.

Exact defect for #154: the staged floor-1 manifest requests 10 spawns
(UjiA6/UjiB4) but only one live actor ever appears and it never displaces
(stationary over 20k ticks, so no route traversal is observable); the
P2_CAVE_READY survivor count (20) never materializes as live Piki actors
(live squad 0 throughout; no spawn/death traces in the engine log), so no
sustained observation with a live squad is possible on this native line.
Criterion 3 stays UNTESTED. No playability claim; no ADMIT.
