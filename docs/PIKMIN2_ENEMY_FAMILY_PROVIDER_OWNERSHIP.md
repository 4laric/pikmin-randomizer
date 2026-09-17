# Enemy family/provider ownership map (#637)

Lane `enemy-family-provider-ownership`, issue #637 (OPEN, parent #586).
Implementation owner: Codex through shared account 4laric. This review
resolves the ownership gap reported by enemies-1 (IDs 14/22/39/47/80/89 with
no lane, no ledger row, or denied gates) and enemies-3 (13 families with no
bounded child issue) with a machine-readable map. No runtime work is
fabricated: `remaining_gates` is null where no overlay row exists (unknown),
never upgraded; no gate is flipped and no admission is claimed.

## 1. Method and sources (all read-only)

- Decompilation (`native/pikmin2-research`): `include/Game/enemyInfo.h`
  enum names/common names; `src/plugProjectYamashitaU/enemyInfo.cpp`
  (`gEnemyInfo` parent/flags, shift_jis); `generalEnemyMgr.cpp`
  manager-case switch (94 cases); family FSM sources as cited per record.
- `docs/PIKMIN2_CONTENT_INVENTORY.json` `enemy_ids`/`treasure_ids` token
  counts per enum name.
- Newest acceptance overlay
  (`output/p2-main-review/docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json`):
  eligibility, owner lane, native module, per-gate status.
- Live registry lane ownership (`owned_files`) for module-holder checks.
- Family lane table (`docs/PIKMIN2_IMPLEMENTATION_FANOUT.md`).

## 2. First-priority audit (IDs 14/22/39/47/80/89)

| ID | Identity | Source family (verified) | Owner / boundary |
|---:|---|---|---|
| 14 | Tobi (Shearwig) | Sheargrub; NishimuraU `Tobi(.cpp/Mgr/State)` | Lane 13 (#120/#197), flight consult lane 15. NO module anywhere; boundary: NEW additive `pc_p2_tobi.{h,cpp}`. Follow-on TOBI14-P0 below. |
| 22 | ElecHiba (Electrical wire) | Hiba; NishimuraU `Hiba`+`ElecHiba`+`GasHiba` FSMs | Lane 22 (#170/#408). Module `pc_p2_hiba` claimed in overlay, no registry holder (worktree copies only). Gates open: identity_spawn, attacks_receivers, cleanup_reentry. Follow-on HIBA22-GATES below. |
| 39 | PanModokiNest (Breadbug Nest) | Nest alias: no info-table row, no manager case | Lane 18 nest infra (#220). No actor, no module boundary needed; generic alias rule resolves it. |
| 47 | Clover | Flora (Pom/pelplant generic; no dedicated FSM found) | Lane 23 (#171). `pc_p2_plant` claimed. Only identity_spawn open. Within-family follow-on. |
| 80 | Tukushi (Horsetail) | Flora (Pom generic) | Lane 23. No overlay row, no module; follow-on inside lane-23 family. |
| 89 | Chiyogami | Flora, HasNoInfo (Pom generic) | Lane 23. No overlay row, no module; follow-on inside lane-23 family. |

## 3. Enemies-3 families (unowned bounded scope)

Frog17 (lane 16), Tank24 (lane 22), Queen30/Baby31 (lane 24, Baby dependent
birth), Demon32 (lane 30), TamagoMushi68/Hana84 (lane 14), Qurione16
(lane 15, module held done), BigTreasure73 (lane 32), Egg37 (lane 20;
shared-projectile-module decision belongs to lane-20 review),
BlueChappy42 (lane 13; YamashitaU FSM verified; queued P0 candidate),
Ooinu_s49/KareOoinu_s91 (lane 23, HasNoInfo), JigumoNest64 (alias, no row,
no manager; Jigumo63 itself is lane 16). Each record carries its remaining
gates or null where unevidenced. No new module is proposed for any of them
in this slice; their follow-ons live with the named owners.

## 4. Kogane / Long Legs overlap routing (explicit, no duplicates)

- Wealthy10 shares held `pc_p2_kogane.{h,cpp}` (muse-kogane, done):
  ROUTED to lane 17 (#168/#219); any Wealthy variant slice belongs to the
  Kogane owner with review, never to a new module. Recorded as
  `shared_module` with the holder cited.
- Damagumo56 and BigFoot69 share held `pc_p2_long_legs.{h,cpp}`
  (muse-longlegs, done; live `damagumo-family-staging-provider`
  running): ROUTED to lane 26 (#173). Recorded as `shared_module`.
- The validator enforces shared-module consistency (a file shared by
  in-map records must be declared on each) plus unique IDs, vocabulary,
  alias/nonactor discipline, parent resolution (UmiMushiBase100 kept as
  the structural nonactor parent), and follow-on completeness.

## 5. Actionable follow-ons specified (exact files + acceptance)

- TOBI14-P0 (primary): `experimental/pikmin2_tobi14_audit.py`,
  `tests/test_pikmin2_tobi14_audit.py`, `docs/PIKMIN2_TOBI14_AUDIT.md`.
  Decode the Tobi definition from the NishimuraU FSM plus the enemyInfo
  row (hashes or exact missing bytes); isolated adapter + malformed tests;
  P1 blockers with owner refs (lanes 13/15); gates UNTESTED; no ADMIT.
  Owner: lane 13, flight consult lane 15.
- HIBA22-GATES (secondary, routed): complete/prove `pc_p2_hiba.{h,cpp}`
  under lane-22 ownership with natural identity_spawn, attacks_receivers
  and cleanup_reentry evidence; owner review required; no ADMIT.

## 6. Module and tests

`experimental/pikmin2_enemy_family_provider_map.py` (`load_map`,
`validate_map`, `--report` CLI): 24 records (6 + 17 + structural base
100). `py -3.12 -m pytest
tests/test_pikmin2_enemy_family_provider_map.py -q` → 19 passed,
4 subtests (valid map, per-rule negatives, routing assertions, follow-on
exactness, deep-copy isolation).

## 7. Blockers and honesty notes

- No bounded child issue is created here; follow-ons name exact files,
  acceptance and owners for the coordinator/integrator to dispatch.
- BlueChappy42 and Egg37 need source-depth decisions (unused-variant
  status; shared-vs-family projectile module) inside lanes 13/20 before
  any module proposal; recorded, not disguised as closed.
- Captain-safety #632 not applicable (no runtime run; recorded N/A with
  the guard reference scripts/p2_fixture_captain_guard.h for future work).