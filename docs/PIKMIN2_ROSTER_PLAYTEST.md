# Emergence roster integration

Issue #114 / #111, implementation owner Codex through assigned shared account 4laric. Experimental P2 work, outside v0.1.

This batch connects the prepared source roster to the two engineering rooms. Floor 1 has the Quenching Emblem (100 Pokos, strength 4), Citrus Lump (180 Pokos, strength 15), and four Snow Bulborbs. Floor 2 has the Spherical Atlas (200 Pokos, strength 101), seven Snow Bulborbs and the existing two Violet Candypops. The three treasures total 480 Pokos, plus two Pokos for each returned Snow corpse.

`--roster` requires `--snow`. Preparation installs separately identified treasure generators and models. An optional `p2-cargo.txt` registry maps native generator IDs to floor-scoped instance IDs, model basenames, values, required strength and carrier slots. Delivery receipts use the instance ID, never the shared compatibility model ID. The legacy one-treasure preview path remains available when the registry is absent.

The checkpoint content identity includes the roster policy version, source manifest and all treasure model bytes, in addition to the room, Pod, Purple, Snow and transition assets. Existing saves are not silently migrated to the new roster. Unknown receipts, changed values, duplicate IDs and invalid model paths are rejected.

Placement is deterministic and explicitly engineered from available source candidates. Ground projection and nearby samples, actor/landing/marker clearance and directed waypoint reachability are validated. These checks do not prove every swept carry path or reproduce the retail random placement algorithm. Plants, physical hole/geyser actors and the surface round trip remain incomplete. Snow combat still uses P1 dwarf logic and sampled P2 animation poses.

The F6 amber/cyan marker interactions and atomic floor-boundary save contract remain unchanged. Closing mid-floor restores that floor's entry squad and receipts together. A new player profile is required for this roster.


## Validation

Python suite: 178 tests and 28 subtests passed. Focused host cargo validation also passed after tightening numeric/model uniqueness to match native parsing. Production and native fixture builds passed.

The real native two-floor lifecycle fixture verified separate model/config bindings, constructor-owned parameter links, all three instance receipts, repeated delivery without duplicate credit, 280-Poko descent and 480-Poko saved exit. It retained 19 survivors, ten Purples, maturity and health; repeated reload and extinction tests passed. Collection is invoked directly in that lifecycle fixture, so this is persistence/accounting evidence rather than a full gameplay run.

A separate real transport fixture carried the Quenching Emblem from its new position to the Pod and credited exactly 100 Pokos. It assigns transport AI and parks only the test captain away from the Pod approach; cargo and carriers are not teleported. The initial unparked trial was stopped after stalling and is not reported as a pass. Captures show normal scene rendering; smooth enemy animation and full presentation remain outside this batch.


## Atlas placement exception

The native haul from the source-projected Atlas position `(0,10,640)` consistently dropped near `(-250,555)`, including an isolated run with enemies removed. This is tracked in [#123](https://github.com/4laric/pikmin-randomizer/issues/123). Policy2 places the Atlas at `(-470,25,670)` on the flat landing-side area and retains both source and source-projected coordinates in `p2-roster.json`. This is an explicit engineering workaround, not a fixed native slope interaction or a claim of canonical placement.

A repeat persistence fixture encountered a live-combat busy-Pikmin guard; the isolated version removes enemies without credit before testing checkpoint preconditions. That guard remains active in the player build.


The final-approach investigation identified a shared edge between coplanar floor triangles 9 and 18. The old per-triangle edge test treated this internal seam as an exposed edge and opposed the slow load's movement. The P2 static-map path now uses reciprocal adjacency to suppress interior edge-segment hits only when both triangles share their plane and map code. It preserves boundary edges, endpoints, noncoplanar edges, dynamic platforms and ordinary P1 maps. The extracted production-predicate regression passed, including negative topology/material/plane cases.

Native `44be3224` passed the complete Atlas haul from the policy2 placement to the Pod with ten Purples and ten Reds, awarding exactly 200 Pokos without a forced receipt or cargo/carrier teleport. The fixture removes enemies without credit to isolate transport and parks the test captain away from the approach. The legacy ship retains its normal placement. Evidence: `output/p2-roster-batch/atlas-pod-fix/3be2c8434db843d79de76dd151cac3af/native-atlas.log`.

The earlier steering and Pod-collision experiments did not resolve the stall and were reverted; moving the legacy ship did not resolve it either. The player layout retains its original ship position. The source-slot slope limitation remains tracked independently in #123.

Local player launcher: `output/p2-roster-batch/Play.cmd`, with a fresh `play-session` profile. The production executable SHA256 is `320e647103fe6a2d48d5a3f4bd17114a56cc54faf5ffd8a935c7989bb884e557`. Generated assets, executable and saves remain local; only source is committed.
