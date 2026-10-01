# Purple natural delivery follow-up

Issue [#1128](https://github.com/4laric/pikmin-randomizer/issues/1128), owner Codex
through shared account4laric. Parent1071 remains incomplete for natural delivery.
The primary review accepted only bounded staged/manual evidence, without source
merge/admission: `output/purple1071-primary-review01.json`, SHA256
`a42131c3097eb2b04de213ead8c9f904bbd8c85dca794179881700aa4aab914d`.
All1071 reports and the user-operated staged smoke remain unchanged.

## Latest status: round05 projection correction

Producer `5c5ca307f4660ad024471ae35ae57b33f59e120b` passed Windows36912221783:
212 tests, eight hashes and no-work. Compiled merge
`d830c2a30adc0045bbc28a87f5a22e091d1b3590`, tree
`93bca2dba054054e44ee4944cbc59b844471e4c5`; exact fixture match. Executable
SHA256 `69e43ff65c4ee30fe711000569840120ab4caabbf53b07cf5fac12afab58d810`.
All seven initialized guard05 cases PASS, live20/centered960x540/same-frame86.

East05 FAIL26.453s and West05 FAIL26.578s, exit1 without timeout. Both real
conversions precede a planner rejection; no pluck/cargo or observed contact.
The all-yaw offset radius and five-unit terrain allowance exclude all32 sampled
pluck endpoints. This is a fixture false negative, not native placement failure.
Live captain body/head radii are7.2/8.4 with separate world-space offsets.

Pushed `7172a2d9586ffae60629816d0accfde75bfe245e` projects the observed sphere
offsets directly, refreshes live geometry, and requires sampled terrain within
0.1unit of captain ground height. Syntax/diff checks pass; measured East05 geometry
has11 candidate endpoints with the corrected model versus0 before. This is only
read-only model evidence. Windows36914100082 and fresh06 runtime remain pending.
Immutable evidence: `output/purple1128-runtime-summary05.json`, both
`purple1128-live-route-...05.json` and `purple1128-projection-comparison06.json`.
No production physics/placement changes. Ordinary delivery/combat/save remain open.

## Round04 and initial live collision correction

Producer `d66bd52de5c04da4d8fde9ccd8aeb6acc5555a98` passed public Windows
run36908646606: 212 tests, eight artifact hashes and no-work dry-run. Actual
compiled merge `50fdb9383f43082e4614baefe0083c53fca79b4b`, tree
`0a17f4fcdac5ddf878e6f5d6f9bf55d4e339876d`; fixture matches producer. Executable
SHA256 `3b4579e127b05ad7e486ffcac51fda2911ac3d704cb3e117aa5e645fe922fa6a`.
All seven fresh initialized guard04 cases PASS with live20, centered960x540,
same-frame raw86 and no positive PASS, including pause/movie cases.

Natural East04 FAIL60.079s and West04 FAIL60.078s. Both convert through the live
Violet and produce a pullable native sprout, but stall before plucking, at final
distances56.159 and51.620. Final five captain observations are stationary despite
unfrozen nonzero input. Neither run creates cargo or establishes delivery.
Original Violet, sprout and cargo policy remain unchanged; no actor teleport or
speed override. Full immutable receipt: `output/purple1128-runtime-summary04.json`.

The route planner incorrectly inflated Violet parts with the captain's ground
radius8.5. Actual creature collision uses both actors' CollInfo parts. It also
retained an early Violet animation snapshot. Follow-up native
`5c5ca307f4660ad024471ae35ae57b33f59e120b` derives a conservative route from live
captain/Violet sphere parts, refreshes blocked segments, and logs read-only actual
collision pairs. Unsupported non-sphere geometry fails explicitly. MinGW syntax
passes; Windows36912221783 is pending. No runtime result is claimed for that fix.

Fresh05 scenes preserve legacy version2 placement bytes and the same baseline.
Next: exact-artifact guard05 and natural East05/West05, then ordinary combat and
native day-save/resume. Historical staged combat, direct stock helpers and forced
clock advancement do not satisfy those ordinary acceptance gates. Public Windows
CI supplies this custom fixture; no private runner dispatch or local heavy build.
The sections below preserve earlier evidence and are historical snapshots.

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

## Corrected artifact and initialized guard results

Pushed nativef067a3e88f818b75cd86e79eab4b2c187dd57251/rootdea06942 on verified
GitHub codex/purple-natural branches. Public Windows36895349196 passed212 tests,
eight file hashes and no-work. Actual compiled merge6a6b15512158edd2c8085dbafc07a731b264a843,
treedb37ec7b02c5a8d6c1ef8b06f832d70ca8839fb6, mainfdbd374146f9fc7ffeb2f19743654764f73a95fc.
The fixture file matches the producer. Windows fixture SHA256:
61ca586332d21eeb956312f80ebf130ddf52c77b5be04d711a93b056a33c5fa1.

All seven initialized guard02 cases PASS: health, manager death, global death,
native dead state, missing manager, health during pause and missing manager during
movie. Each first observes a healthy active captain/20 live Pikmin, then raw86 in
that same frame without a positive PASS, in8.64–8.80seconds. Failure01 remains
preserved. Full evidence: output/purple1128-guards02.json and each per-case report.

Original east197 natural02 FAIL at60.093seconds. Active gameplay8.416s, native
throw15.985s, repeated17.981s, actual Violet witness/conversion observed. No pluck
request/acquisition/cargo occurred. No captain relocation. Current blocker is
captain approach to the real sprout; the cargo route has not yet been exercised
by this corrected natural fixture. Do not infer route clearance from this run.

Read-only initial Violet telemetry:12 collision parts,45.024-unit maximum
horizontal collision extent and50-unit bounding sphere. Seventeen footprint
samples are flat grass at-37.722; this does not certify continuous terrain or
cargo clearance. Version2 marker and generator bytes match across old/fresh scenes.

Follow-up native8f617f7e515d6828dfe399927a84816e93cc2dd0 adds only observed
captain/sprout coordinates, controller port/stick/frozen state and sprout readiness,
plus checking collision info is initialized before traversing it. Syntax passes.
Intermediate be97bb689 failed syntax (missing concrete Kontroller header) and was
inadvertently pushed by a non-stopping PowerShell command; corrected forward with
no rewrite. Its failed/cancelled builds are not validation. Windows36896932976
is pending/running for the corrected follow-up; no new runtime claim yet.
Summary receipt: output/purple1128-runtime-summary02.json. Public CI is unaffected
by the latest optional private project=pikmin routing hold. No private dispatch.

## Current validated artifact and measured remaining blocker

Windows36896932976 passed212 tests, eight artifact hashes and no-work. Producer
8f617f7e515d6828dfe399927a84816e93cc2dd0; actual compiled merge
bbf0ecd0c60023030656187c2d538ed140357986, tree
f30b802e2e8c17775361033bdeb965461a1cfc5e, integration parent
208914127ae40ed34377d8b0da5205606020f83e. The fixture matches the producer.
Executable SHA256452d1a1054d3659d3c4372edc12ad76c48173689ab5c7c4dd598fb411dd9114a.
All seven fresh guard03 cases PASS again on this exact executable: healthy captain,
field20, same-frame raw86, no positive PASS, including pause/movie (8.56–8.83s).

Natural east03 FAIL60.094s. Active8.362s, native throw15.753s, actual conversion,
then a pullable Purple sprout at(-215.754,-37.722,2058.509). The captain moves to
(-257.256,-37.722,2054.807) and remains41.666units away, with zero displacement
across the last five samples despite unfrozen P1 input(-6,32). No pluck, acquired
Purple, cargo spawn, hauling or reward. Old and new failures remain immutable.

The exact private naviMgr.bin decodes ground radius8.5 and dead zone0.1. The p62
pluck-distance entry is absent, retaining native default15; the fixture's stop20
would also need correction once approach succeeds. Sparse body observations put
the captain near a Violet tip (about0.93 horizontal gap after the loaded ground
radius), supporting an obstruction hypothesis without claiming a collision callback
proof. Do not change physics or teleport actors to pass this case.

Next bounded work: controller-only detour around the measured Violet body and
approach within the actual native pluck distance, then repeat original east197
natural acquisition/hauling under60seconds. Cargo-body evidence is separately
available from the earlier artifact's Red control (22.734s PASS; bound35, ground
radius13.5, flatgrass samples). This is not Purple delivery acceptance.

No production placement changed and no version3 position was selected. Preserve
version2 bytes; require full route/cargo/body/terrain evidence before selecting a
stage1-only versioned placement. Root draftPR1139 is based on PR1090's branch to
isolate this evidence document; nativePR111 remains draft. Full immutable current
receipt: output/purple1128-runtime-summary03.json. This is progress evidence, not
an integrated source or full gameplay handoff.
