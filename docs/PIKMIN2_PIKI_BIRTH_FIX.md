# Piki-birth challenge-setup fix (issue #741, unblocks #567)

Bounded engine provider slice. The #567 chal4 boot observes
`CHALLENGE_LAYOUT_READY id=challenge-4` plus generator spawns, then panics
before any squad birth: `[PANIC] src/sysDolphin/system.cpp:1229 ***
PIKI BIRTH FAILED`. Diagnosis #721 (done) attributes POOL_EMPTY by
elimination and names the exact fix locations; no live lane owns the fix.
Implementation owner: Codex through shared account `4laric`.

## Owned files (exact, disjoint)

- `native/src/plugPikiKando/gameCoreSection.cpp` - `P2_PIKI_INITSTAGE` /
  `P2_PIKI_CREATE` / `P2_PIKI_CREATE_DONE` order+state proof on the
  `pikiMgr->create` path; `P2_PIKI_FINASETUP` order anchor.
- `native/src/plugPikiColin/newPikiGame.cpp` - reserved for
  initStage/finalSetup order verification (unchanged: order is proven by
  the gameCoreSection markers, no edit needed).
- `native/src/plugPikiKando/objectMgr.cpp` - toggle-independent
  `P2_PIKI_POOL_FULL` / `P2_PIKI_POOL_NO_SLOT` pool-state diagnostics.
- `native/src/plugPikiKando/pikiMgr.cpp` - toggle-independent
  `P2_PIKI_BIRTH_CAP` / `P2_PIKI_BIRTH_POOL_NULL` diagnostics.
- `native/src/plugPikiKando/goalItem.cpp` - toggle-independent
  `P2_PIKI_BIRTH_HALT` halt-site pool/cap context before the ERROR.
- `experimental/pikmin2_piki_birth_fix.py` - fix contract + run-log
  verifier (`verify_boot`: challenge create > 0, ordered setup, live
  squad, no panic/abort/captain-down, no injected lines).
- `tests/test_pikmin2_piki_birth_fix.py` - focused tests.
- `docs/PIKMIN2_PIKI_BIRTH_FIX.md` - this doc.

All engine diagnostics are `printf` (not `PRINT`): `PRINT` output is gated
by `gsys->mTogglePrint` (default FALSE), which is exactly why the #567 log
carried no pool evidence. No gameplay semantics change: the only
behavioral delta is observability plus the guaranteed pool creation
ordering the markers prove.

## Verification

- `py -3.12 -m unittest tests.test_pikmin2_piki_birth_fix` -> 16 passed.
- Headed chal4 boot (private leased build of native `e1861e68`, #649
  guarded fixture spliced read-only, #632 guard): pool creation proven on
  the setup path (`P2_PIKI_CREATE requested=102`, `DONE max=102`,
  `INITSTAGE` -> `CREATE` -> `FINASETUP` order observed), panic eliminated,
  boot completes the observation window with no abort and no captain-down;
  executable SHA-256, run-log SHA-256, ninja `-n` dry run recorded in the
  lane handoff.

## Refined root cause (measured, not inferred)

The toggle-independent diagnostics overturn the POOL_EMPTY attribution on
this pin: the pool is created (102 slots) and healthy. The abort trigger
is field-cap saturation by buried sprouts:

- `P2_PIKI_COUNTERS formation=0 free=0 me=100 work=0 born=0 all=160`:
  100 me-state (buried, unplucked) sprouts from the retail chal4
  generators plus 60 Onion-held (3 x 20) = 160 > 100 field cap.
- A single `P2_PIKI_QUEUE color=1 add=20`; zero `P2_PIKI_BORN`: the first
  dispense tick computes total 119 >= cap 100 and refuses (correctly).
- `P2_PIKI_BASEINF free=100 active=0`: the story-mode BaseInf restore
  contributes nothing; all 100 are generator-spawned (retail chal4 gens
  are byte-identical to the boot assets).
- Sibling proof: chal1 (forest) births squad=20 with PASS on the same
  pool path; only sprout-dense chal4 saturates.
- Retail compiles the fatal `ERROR`s out, so a cap refusal drains quietly
  there; the port's abort is the defect this lane repairs (cap-full now
  stops the dispense via `P2_PIKI_BIRTH_CAPSTOP` /
  `P2_PIKI_DISPENSE_CAPSTOP` with the queue draining to zero).

## Honest limit (why this lane finishes BLOCKED, not ready)

With 100 real sprouts saturating the field, no Onion birth can succeed on
an unattended boot (every birth needs total < cap; plucking/deaths are
gameplay, not boot). The starting squad therefore cannot birth here
without either (a) a reduced-sprout fixture arena for acceptance (trial
lane #567 scope), or (b) sprout spawn/counting review in
generator.cpp/pikiheadItem.cpp (outside the 5 owned engine files). The
annexed `challenge=0` mode flag on this BBFT direct boot (creation is
path-independent and proven regardless) is recorded for the same review.
No playability is claimed; #567 stays OPEN.

## Captain safety (#632)

`scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`) adopted with
orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED exit, parked
captain, no blanket invincibility; guard/source hashes recorded at the
run. All six gates start UNTESTED.

## Integration

Engine edits need #186 shared-owner review before landing; #52 campaign
contract recorded as a dependency. Downstream #567 stays OPEN. No ADMIT,
no ledger writes, no other family/shared edits.
