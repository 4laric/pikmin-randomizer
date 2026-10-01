# Purple natural delivery follow-up

Issue [#1128](https://github.com/4laric/pikmin-randomizer/issues/1128), owner Codex
through shared account4laric. Parent1071 remains incomplete for natural delivery.
The primary review accepted only bounded staged/manual evidence, without source
merge/admission: `output/purple1071-primary-review01.json`, SHA256
`a42131c3097eb2b04de213ead8c9f904bbd8c85dca794179881700aa4aab914d`.
All1071 reports and the user-operated staged smoke remain unchanged.

## Initial bounded scope

Private branches `codex/purple-natural` begin at root3355a25d371417eb3918531907b0e3c74ddee62e
and actual tested native22f52c4e281946e8e149c00ad824894ba1edb1fb.
Owned files are this document and `native/tools/preview_p2_purple_combat.cpp`.
The initialized guard executes immediately after the engine frame, before every
pause/movie/diagnostic or acceptance early return. It checks actual health,
global/manager death, native dead state and missing captain after initialization;
all failure paths exit86. Only the existing narrowly verified sunset teardown
can legitimately lack a previously seen captain.

Negative cases manipulate a real initialized runtime: health0, manager-dead,
global-dead, native dead-state, unavailable Navi manager, health0 with pause and
missing manager with active movie. The old FORCE environment variable now uses
the initialized health case; it no longer exits in main before engine startup.
Each test must show healthy active captain and field20 before injection, raw86
in the same engine frame, centered960x540 and no positive PASS. These are fixture
fault injections, not gameplay death acceptance.

Native candidate46d203e0df0f30145a873a2f4f972fa1ec882a90 adds wall-clock milestones
for window, initialized captain, active gameplay, input selection, native throw,
sprout/pluck, acquired Purple, cargo spawn, approach assignment, attachment,
movement, uptake and verified reward/release. Syntax passes with maintained
MinGW flags, including `-UWIN32`; the initial incomplete syntax invocation omitted
that platform flag and was corrected. Windows36882527234/Linux36882527487 and
fresh runtime evidence are pending. No local heavy build or maintained export.

## Read-only route audit

`output/purple1128-route-audit01.json` reads legal local Forest model bytes and
the actual fresh campaign generator. It finds115route points/201directed links;
waypoints48 and67 match the previous runtime coordinates. The appended Violet
at(-215.754,-37.722,2022.239) is17.53units from edge7→48, whose endpoint corridor
radii are82.71 and45.40. It is78.66units from the prior stationary cargo position.
This corroborates the preserved omitted-Violet A/B, but static proximity is not
an actual collision-footprint or terrain-clearance certificate.

No production placement changes are included. `randomizer/purple_campaign.py`
adds landing-origin+100x in every starting area; only Forest was measured here.
Any correction needs coordinated ownership, physical clearance/carry evidence,
and a versioned placement/session policy so old seeds are not silently moved.
The current child first establishes guard correctness and where natural startup,
conversion/pluck, approach and haul spend their60-second budget. A staged
Purple cannot replace the natural acquisition/delivery gate.

## Preparation follow-up (2026-10-01)

Expanded scope recorded before production edits in #1128 comment5936136031 and
canonical registry revision4: `randomizer/purple_campaign.py` and its main tests
are now owned by this lane. No production placement edit has been made. Version2
sessions must retain exact generator bytes/UID/positions; fresh placement needs
versioned session/staging identity, mismatch rejection and compatibility review.
Only stage1 may change after measured clearance; other stages stay unverified.

Windows run36882527234 passed211 CTests and no-work; eight artifact hashes verified.
Actual compiled merge is67fec12acc4a550a5a74061d075a5b0d80d1bc64 on main
eb8b887bf3f2a0dd5eef2916b4a69d221b5ec881, distinct from producer46d203e0.
Fixture SHA4921a6ae3171b18bcf74668f122079b83d1d2327f2988b5a5a4c7d2c86d0ad8e.

The first initialized-health test exited86 in the same frame, but injected at
tick2 with field0 and an active startup movie, so the required guard acceptance
FAILED. The corrected source waits for20 live Pikmin and active gameplay before
negative injection; the real guard remains unconditional before early returns.

A west197 timing diagnostic was explicitly interrupted at28.922seconds after
review identified inherited captain relocation in its upcoming pluck path.
No pluck relocation marker occurred in that run. It is neither timeout evidence
nor accepted natural delivery. Preserved milestones: active gameplay12.083s,
input selection/native throw19.247/19.248s. Full timings remain unknown.

Candidate natural acquisition now approaches via controller input and requests
plucking with A; it no longer teleports the captain or forces a pluck state.
Scripted native throw/transport assignment remain disclosed fixture actions.
The unrelated adult-combat mode retains its separately labeled historical setup.
Read-only telemetry now reports the full selected route, dynamic Violet/cargo
bounding and collision-part spheres, plus terrain triangle/height samples.
Samples are diagnostic and cannot by themselves certify continuous clearance.
Corrected source passes MinGW syntax checking; runtime is UNTESTED.

Immutable follow-up: `output/purple1128-preparation02.json`. Next dependency is a
new Windows custom-fixture artifact, then seven field20 initialized guard cases
and original east197 natural acquisition/haul. Current private Linux validation
cannot produce that Windows artifact. Optional remote dispatch remains on hold
pending the coordinator's runner transition notice. No live build was cancelled.
