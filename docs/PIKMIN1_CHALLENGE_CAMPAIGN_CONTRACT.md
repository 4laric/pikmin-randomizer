# P1 Challenge Mode campaign contract (#52, first bounded slice)

Lane `p1-challenge-campaign-contract`. Implementation owner: Codex through
shared GitHub account 4laric; contributor Muse Spark 1.3 via OpenCode.
Private worktree `output/workflow/prerequisites/p1-challenge-campaign-contract/root`.
No native work, no runtime, no Archipelago changes, no ADMIT. Tooling-only.

## 1. Five-stage audit (observed facts, legal P1 asset tree read-only)

| Slot | Area | day rate | ini (bytes/sha12) | map file |
|---|---|---|---|---|
| chal0 | Impact (id 0) | 0.8 | 2475 `6cfb79ea204c` | courses/practice/practice.mod |
| chal1 | Forest (id 1) | 1.4 | 2471 `54b3e0a5f84a` | courses/stage1/forest.mod |
| chal2 | Navel (id 2) | 1.2 | 2465 `1a16d0e61c19` | courses/stage2/cave.mod |
| chal3 | Spring (id 3) | 1.4 | 2485 `d1b0537e22c6` | courses/stage3/yakusima.mod |
| chal4 | Trial (id 4) | 1.0 | 2484 `424771962bb0` | courses/laststage/garden.mod |

Generator inventories (`default.gen` / `plants.gen`, template counts):

- chal0: 80 records (meti 10, ikip 3, tlep 53, iket 11, krow 1, ssob 2);
  plants 30 `tnlp`. gen sha `eeb58bacfb1d` / `5c317737c442`.
- chal1: 79 records (meti 15, ikip 3, tlep 23, iket 33, krow 4, ssob 1);
  plants 30 `tnlp`. gen sha `a1515c81281f` / `0ad664331ca8`.
- chal2: 98 records (meti 14, ikip 3, iket 19, tlep 50, krow 5, ssob 7);
  plants 38 `tnlp`. gen sha `de45c8afcb6a` / `0ce5e8423bba`.
- chal3: 87 records (meti 11, ikip 3, tlep 19, iket 42, krow 4, ssob 8);
  plants.gen `0b02213aa3c3` is an UNDECODED framing variant (hash-pinned,
  not skipped). gen sha `6950b4406584`.
- chal4: 63 records (meti 13, ikip 15, iket 15, tlep 11, ssob 6, krow 3);
  plants 49 `tnlp`. gen sha `8ec896e7e210` / `8e06be7ca271`.
- All `navi_start` are `0.0 0.0` in every stage ini.

Full machine-readable audit: `output/workflow/prerequisites/
p1-challenge-campaign-contract/out/audit-five-stages.json`.

## 2. Deterministic campaign contract (pure rules, no gameplay)

- Stage access: five fixed slots `chal0..chal4` in area-id order; unlocks
  are persistent (`unlocked_stages`).
- Attempt identity: `<seed>/<slot>#<n>` (seed non-empty string, n >= 0).
- Checks are one-time: `<slot>:<kind>:<name>`; `CheckLedger.award`
  returns False on replay, so re-clearing a threshold never duplicates its
  reward. Reloading awarded sets preserves them (reconnect-safe).
- Attempt-local (reset every attempt): population, score, timer,
  enemy/resource runtime state, squad. Persistent: unlocks, awarded checks,
  met thresholds, upgrades. Anything else is out of scope and rejected by
  `classify_state`.
- Reward thresholds are data records with `achievability: unevaluated`.
  No target in this slice is claimed achievable.

## 3. Explicitly unsupported facts (NOT claims; follow-on scopes)

- Scoring formula and exact timer seconds per stage (needs engine/decomp
  confirmation or timed runtime observation).
- Starting-squad composition per stage (Piki template counts observed as
  `ikip` rows, not as a proven starting squad).
- Native retry/reset semantics (what the engine actually resets).
- Upgrade carry-over rules (colors, Flarlic, stat upgrades, time
  increases) and queued-consumable handling across retries.
- Guaranteed-resource analysis (which drops/routes are deterministic) and
  achievable population/score targets with playtest evidence.
- chal3 `plants.gen` framing variant decode.
- Native timed attempts, stage transitions, AP reconnect/item replay,
  multiworld remote-upgrade demonstration, named playtest seed.

## 4. Concrete follow-on scopes with dependencies

1. Resource/timing audit per stage (guaranteed drops, practical routes,
   achievable targets + playtest seed) — needs runtime fixture + #632
   captain-guard adoption; consumes this contract's IDs and ledger.
2. Native timed-attempt/transition/retry harness — needs #6 persistence
   semantics for attempt-local reset vs receipt preservation.
3. Story-destination vs timed-campaign mode separation and upgrade
   carry-over rules — needs #100 destination contract coordination.
4. AP reconnect/item-replay + multiworld remote-upgrade demonstration —
   needs shared Archipelago owner coordination (this lane never touches
   the shared installation).
5. chal3 plants.gen variant decode — shared `.gen` framing question for
   the fixture-builder owner.

## 5. Validation evidence

- `tests/test_pikmin1_challenge_campaign_contract.py`: 17 passed +
  5 subtests (stage table, deterministic IDs, real-asset audit incl. the
  chal3 pinned variant, state boundary, exactly-once ledger incl.
  reload, threshold data model).
- `check_p2_handoff_gates.py` is family-lane scoped and not applicable;
  no gate PASS is claimed anywhere (tooling handoff, all runtime gates
  UNTESTED, fixture adoption N/A).