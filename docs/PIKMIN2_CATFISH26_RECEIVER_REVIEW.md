# Catfish26 receiver registration review (issue #641)

Lane `enemies-5-catfish26-receiver-review`. Implementation owner: Codex
through shared GitHub account 4laric; contributor Muse Spark 1.3 via
OpenCode. Private worktree `.../prepared/catfish26-receiver-root`.
Read-only review; no runtime, no native build, no shared edits, no ADMIT.
All six gates UNTESTED. This answers the #374 lane stated dependency from
the Catfish side without touching that lane.

## 1. Evidence reviewed (read-only)

- Legacy lane l16 (`output/deepseek-wave/handoffs/l16.md`): family #167
  (Frog 17, MaroFrog 18, Catfish 26, Tadpole 27, Jigumo 63) exercised the
  Frog 17 / MaroFrog 18 chain only. Catfish26 six-gate table: all gates
  UNTESTED; gate 1 cites "native FSM `pc_p2_catfish.cpp` present, not
  exercised this pass"; gate 5 cites "no transport/receipt observation".
- Native `pc_p2_catfish.cpp` (28279 B, read-only reference checkout):
  full attack paths exist and are marker-observed — `P2_CATFISH_BIND`
  (`generator=`, `source_id=26`), `P2_ENEMY_READY species=Catfish`,
  `P2_CATFISH_BITE`, `P2_CATFISH_EAT ... slot=<n>` (exactly one
  InteractKill per captured Pikmin at the swallow event), `P2_CATFISH_FLICK`
  (InteractFlick on mouth Pikmin and in-range Navi),
  `P2_CATFISH_ATTACK_NAVI ... damage=`, `P2_CATFISH_DEAD ... health=0`,
  plus `pc_p2_catfish_forget` / module reset accounting.
- Completed-family comparison (same checkout): Sarai emits
  `P2_SARAI_CORPSE_READY ... receipt=corpse:sarai:<gen>`; Kurage emits
  `P2_KURAGE_CORPSE_READY ... receipt=corpse:kurage:<gen>`; Fuefuki,
  BombSarai and Groink emit `P2_*_CORPSE*` markers. Catfish emits NO
  `P2_CATFISH_CORPSE*` marker and NO `receipt=corpse:catfish:` token.
  Therefore a natural Catfish death can never reach the Pod receipt
  ledger today.

## 2. Exact additive registration (mirrors the TEKI_Mar pattern)

Receiver present in source but unregistered in the routing table:

1. In the death path that emits `P2_CATFISH_DEAD` (beside
   `transition(s, CATFISH_DEAD, ...)` in `pc_p2_catfish.cpp`), emit once
   per natural death:
   `P2_CATFISH_CORPSE_READY generator=<gen> source_id=26
   receipt=corpse:catfish:<gen>`.
2. Track corpse registrations (actor -> generator) with cleanup in
   `pc_p2_catfish_forget` and the module reset, mirroring the sarai
   `corpses` set, so a forgotten/recreated actor cannot double-report.
3. **Family-owner review REQUIRED before any shared edit**: the
   `corpse:catfish:` receipt namespace touches the shared Pod ledger
   contract owned elsewhere. This review names the registration; it does
   not implement it.

## 3. Reusable checker and tests

- `experimental/pikmin2_catfish26_receiver_review.py`: `review_log`
  reports binding generators, four attack legs, death generators,
  corpse-registration verdict, taint lines and classified findings
  (`absent-markers` / `missing-registration` / `injected-taint`).
  `gate_claim` is always `"none: review only"`.
- `tests/test_pikmin2_catfish26_receiver_review.py`: 8 focused tests
  (full chain without corpse, corpse receipt, unbound, missing legs,
  wrong source id, taint, empty log, other-family isolation). 8/8 pass.
- Evidence: `output/.../catfish26-receiver-output/checks.log`.

## 4. Answer to the #374 dependency (Catfish side)

The umimushi71 lane asked for a lane-16 receiver review. From the Catfish
side: Catfish receiver paths (Flick/Attack/Kill) exist in source and are
marker-observable, so a natural receiver observation is enabled pending a
run; the full death-to-receipt chain additionally needs the corpse
registration named in section 2 (family-owner review first). No lane-16
files were touched; gates 3/5 for Catfish remain UNTESTED here.

## 5. Six-gate evidence (honest, review-only)

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | l16 table: native FSM present, not exercised | natural (no claim) |
| 2. Autonomous movement and animation | UNTESTED | not in review scope | natural (no claim) |
| 3. Attacks and receivers | UNTESTED | receiver paths exist in source, unobserved in a run | natural (no claim) |
| 4. Death and corpse | UNTESTED | death marker exists; corpse registration missing (section 2) | natural (no claim) |
| 5. Actual transport and reward | UNTESTED | no transport/receipt observation possible yet | natural (no claim) |
| 6. Cleanup and re-entry | UNTESTED | forget/reset exist; re-entry unobserved | natural (no claim) |