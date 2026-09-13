# Hole of Beasts checkpoint adapter proposal

Reference-only scope #154/#132. No shared campaign, ledger, runner or native
protocol changes are made. `experimental/pikmin2_beasts_lifecycle_reference.py`
reads the actual local US disc parameter archive and existing source catalog;
its output is `output/p2-lifecycle-batch/beasts-reference-01/audit.json`.

## Source floor contract

The first three forest_1 definitions cover floors1,2,3 individually. All three
have f007=0 (no escape fountain) and f010=0 (unclogged hole). These fields are
named in `native/pikmin2-research/include/Game/Cave/Info.h:164` and `:168` and
constructed in `src/plugProjectKandoU/gameCaveInfo.cpp:225`. Floor2 descends to3;
it must not inherit the tutorial runner's exit-on-floor2 behavior. Floor3 is
also not the final cave floor.

Floor2 selects `1_units_cent2_tsuchi.txt`. The bounded imported room has two
source type8 candidates at (-55,0,75)/yaw215 and (75,0,-95)/yaw45. These are
flower candidates, not entrance or descent anchors. The existing profile's
captain(-180,0,-180), Pod(-260,0,0), and ship(260,0,0) are engineering anchors.
Retail captain/hole placement remains generated from assembled map units;
this reference does not invent their coordinates. Floor3 uses
`2_ABE_norhiba_blkhiba_tsuchi.txt` and still needs its own assembled profile.

## Two Violet conversions

Actual `enemy/parm/enemyParms.szs:pom/enemyparm.txt` has proper ip01=5. The base
parameter block also has ip01=0: parsing must select the proper block, not the
first matching key. Source `Pom.cpp:265` uses this normal capacity and multiplier1.
Two spawned BlackPom therefore support at most10 net non-Purple conversions,
with no population multiplication. `Pom.cpp:297` refunds a used slot for a Purple
fed to a Purple bud. Repeated same-color processing is not new Purple credit.

`PomMgr.cpp:39` additionally suppresses BlackPom when the current zero-based
floor index is below2 (or cave ID t_01) and global plus saved cave Purple count
is at least20. Hole of Beasts floor2 is index1. A future profile must snapshot
that global context at floor generation and persist which buds actually
spawned. Missing global context must be an explicit unsupported gate, not an
assumption of zero. The current20-Red fixture is valid only with zero stored
Purple context.

Reference tests validate per-instance budget, duplicate witness rejection,
same-color refunds, casualties, and rejection of population/species growth.
These witnesses are proposed trusted-native events; current native handoffs
report only a squad, so the tests do not establish actual conversion provenance.

## Minimal future adapter

Introduce a separate profile-bound adapter selected by versioned content
identity. Leave schema1/tutorial behavior and old save identities intact.
The profile maps explicit floor IDs to staged assets, next destination,
allowed receipts, native entry/descent anchors, and actual spawned conversion
budgets. It should expose validation, entry serialization, transfer application,
and staging to the existing single authoritative SurfaceLedger/SurfaceRunner.
Do not add a second checkpoint writer.

The minimal floor1->2->3 contract is:

- Token binds content/profile, trip, source floor and expected revision. An
  exact replay returns the committed result; changed payload or stale token
  conflicts. Floors advance only along the declared edge.
- Native handoff carries survivors with species/maturity and normalized captain
  health. Zero survivors/health remains terminal. No incoming species/population
  increase is accepted without an explicit conversion or other supported witness.
- Floor2 carries two stable bud IDs and consumed slot counts within this visit.
  Replaying the same boundary must not reset capacity. Same-color inputs refund
  slots. A new generated visit may legitimately reset buds, subject to the
  source global-population birth gate.
- Cumulative receipts remain monotonic by stable instance ID/value. Floor2 has
  no treasure receipts; do not create dummy treasure to initialize a receiver.
  Egg drops and population rewards require their own supported contracts.
- Floor1 commits revision1/active floor2; floor2 commits revision2/active floor3.
  A prepared-but-unimplemented floor3 must stop durably before launch. It must
  not become a synthetic return or claim the full cave is playable.
- Per-floor generation identity and its conversion context are persisted before
  native launch. Relaunch uses the same generated content and receipts. Existing
  pending-command/atomic-ledger replay tests should run unchanged through the
  adapter interface before production adoption.

Native currently constrains tutorial floor IDs/receiver initialization and has
no conversion-witness channel. Extending those is a separate approved interface
change, not part of this audit. Four reference tests and the actual source audit
pass; no native process was launched for this batch.
