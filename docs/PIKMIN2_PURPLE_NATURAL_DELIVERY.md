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
