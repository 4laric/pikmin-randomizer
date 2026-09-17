# Generated-actor claim arm + BIRTH generator field: ownership/pin decision (#644)

Owner: Codex via shared 4laric. Lane `shard-provider-placement-genclaim-644`,
gen 2, issue #644 (OPEN, 4laric), recovery request
`f42ecca0f2b6aad7dc90adcbeda741fb6235f14733d559691f7d626014815985`.
Read-only discovery; no runtime, no shared edits, no ADMIT. All six arena
gates UNTESTED. Helpers: `experimental/pikmin2_generated_claim_ownership.py`;
tests: `tests/test_pikmin2_generated_claim_ownership.py` (stdlib only).

## (a) Claim-arm owner: enemy-waterwraith99-generated (#572), itself

- `output/autofill-root-572/docs/PIKMIN2_WATERWRAITH_GENERATED_ACCEPTANCE.md:117`:
  "Family generated-claim arm (this lane owns pc_p2_waterwraith_actor /
  encounter files)". Self-assignment by the blocked consumer lane.
- Surface (lane-owned, registry `enemy-waterwraith99-generated`, blocked gen3
  rev7): `native/pc_port/pc_p2_waterwraith_actor.cpp/.h`,
  `native/pc_port/pc_p2_waterwraith_encounter.cpp/.h`. All four MISSING at
  canonical HEAD; lane commits `c30fdc82`, `8703c632`, `1b52c776` (base
  `5486ae84`) added only boundary/observer/acceptance files.
- Registry-wide scope scan (516 lanes): no other lane scopes the
  Waterwraith99 generated-claim arm. `muse-waterwraith` (#503, done) is a
  completed movement/encounter contract, not a producer. No open issue names a
  different producer. Conclusion: NEW design slice owned by #572 itself.

## (b) BIRTH-field owner + change surface: same slice (#572)

- Same acceptance doc `:17-23`: `P2_WATERWRAITH_BIRTH` must carry "present
  birth generator field equal to the placement generator"; `:117-120` binds
  the placement-bound seeded Teki as rig owner and logs its generator.
- `planning-shard-provider-actor-birth-projectiles-cycle-13` scope:
  "Generic real engine actor-manager/birth and projectile/payload
  infrastructure ... excludes family-specific consumer FSMs." #608 is
  explicitly excluded as the family-specific producer.
- Change surface: the four actor/encounter files above (new) + generator
  field on the `P2_WATERWRAITH_BIRTH` log line. No existing producer.

## (c) Catalog/bind integration pin: exact carriers (brief shorthand corrected)

The brief/cycle-14 shorthand "(wave line 25af23fc / df4135e2)" is imprecise:

- `25af23fc` = "species-integration: merge bluekochappy44
  generated-identity observer (#461)": 3 observer files, NO catalog content,
  NOT an ancestor of the carrier below, NOT in canonical HEAD.
- `df4135e2` (native) = "species-integration: register Damagumo SPECIES row
  (#638)": 1 file (`pc_port/pc_p2_long_legs.cpp`), NO bind content, NOT an
  ancestor of the carrier below.

Exact carrier pins (verified `cat-file` + `merge-base --is-ancestor`):

- Root catalog: `randomizer/p2_placement_catalog.py` +151
  (`WATERWRAITH_CANDIDATE_SPEC`, slot 568677317) in `7a21ce6a`
  ("enemy-waterwraith99-placement-provider ... (#575)"). Contained in
  `codex/autofill-575`, `claude/p2-deepseek-wave`,
  `codex/enemy-ww99-rerun-root`, et al. ABSENT from canonical HEAD tree
  (`ecf5f53a`); base `5486ae84` is not a HEAD ancestor.
- Root packaging/bind: `experimental/pikmin2_muse_packaging.py` BlackMan99 +
  Tyre98 sidecar content in `04d58d33` ("waterwraith99-packaging-provider ...
  (#576)"). Same container branches. File ABSENT from canonical HEAD.
- Native bind: `pc_p2_generated_placement.cpp/.h` + fixture in `e2aa476e`
  (`codex/autofill-575-native` et al.). NOT in native HEAD (`a95040b6`).

No merged canonical-HEAD pin exists: integration (merge of
`codex/autofill-575` + `codex/autofill-576` and native counterparts) has not
happened. That landing is integrator-owned; #572 dependency 2 names it
("land codex/autofill-576 at a current pin").

## Packet: downstream consumers + next bounded producer scope

Consumers: #572 (blocked gen3 rev7, consumes claim-arm/BIRTH decision);
recovery `f42ecca0...15985` + publication reviewer; #608 actor-birth shard
(generic infra; family FSMs excluded); #575/#576 providers (done; awaiting
integration landing). Next bounded producer scopes: (1) #572-owned claim-arm +
BIRTH design slice with runtime validation; (2) integrator landing of the
three carrier pins at current HEADs. No ADMIT requested or granted.

## Captain safety #632

Not applicable: no runtime acceptance run conducted, launched, or proposed in
this slice. Guard exists at canonical `scripts/p2_fixture_captain_guard.h`.
Prior guard hash `d2f678c9...` (cycle-13 report) is HISTORICAL, not re-verified
here. Any follow-on runtime must adopt the guard (orimaDead/NaviDead/HP<=1,
CAPTAIN_DOWN + BLOCKED exit, parked captain, no blanket invincibility) and
record fresh guard/source hashes.
