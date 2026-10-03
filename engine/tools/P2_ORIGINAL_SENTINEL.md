# Original Sentinel plants (#1284)

Implementation owner: Codex through shared account `4laric`.

The source producer is `pc_p2_original_shijimi_group.{h,cpp}`. It has no
generator aliases or AP identities. Its adapter must use the independent
original parent identity and the child discriminator `(emission=0, member=0..4)`.
Member 0 is the hidden Red/Purple leader; members 1..4 are Yellow followers.
Every source emission consumes the plant sentinel before manager lookup.
An absent manager or a genuine null allocation is terminal, including partial
follower groups. Infrastructure errors invoke whole-emission cleanup and leave
an unpublishable pending record, rather than becoming fabricated null births.

Source ordering comes from retail GPVE01 revision 0 and research files:
`plants.cpp`, `shijimiChouMgr.cpp`, `shijimiChou.cpp`, `shijimiChouState.cpp`,
and `Entities/ShijimiChou.h` in the private read-only P2 research checkout.
The leader performs raw birth, onInit, leaderInit, unused rand(), then its
50% color roll. Each follower performs Y scatter, raw birth (including scale
RNG), color roll, appearance effect, forced Yellow color, and onInit. Failed
raw births omit color/init draws. The source group count is the last successful
follower loop index; it is not a general population counter.

Plant-origin genItem short-circuits the nectar-rate draw. Red/Purple require
their respective first-spray-made flag. Honey must be the real source factory
and execute init(nullptr), including its RNG, before assigning color. Source
velocity uses sin(face)*50 for both X and Z, with Y=200 and position Y+2.
The ledger records failed Honey births and retains ownership after the
Spectralid or its original plant retires. It never synthesizes an Egg journal.

The pure producer test checks the source call trace, RNG interleaving, every
single-child allocation failure, one-shot manager absence, spray suppression,
Honey null birth, cleanup after a half-init failure, and atomic saved-journal
validation. These controls do not qualify a native actor, real appearance
effects, ordinary Pikmin attachment, scene teardown, or campaign resume.

The foliage converter now accepts literal source50 Ooinu_l and source87
Magaret. Source50 is a 60-frame BCA with raw loop attribute2 and no registered
loop keys; source87 is a 74-frame BCA with attribute0 and no keys. Both use
normal-layer Plants behavior. Their fp27 child birth heights are 85 and 70.
Conversion alone does not admit either sentinel into gameplay.

The canonical Honey adapter is `pc_p2_original_shijimi_honey.{h,cpp}` and
`pc_p2_original_shijimi_honey_native.cpp`. It preserves the full plant root
identity and appends `(EmitterKind::PlantSpectralid, emission=0, member=0..4)`
with Honey slot0. It calls the real owner-pinned `honey::Manager::birth` with
the same source RNG. Successful init(nullptr) consumes its original draw;
capacity failure is true/null and consumes none. The actual scene owner's
Honey consumed callback must dispatch this ancestry to `PlantGroups::consume`.
No Egg contents record is created. Spectralid facing is not copied onto Honey:
retail genItem sets only position and velocity after initialization.

`pc_p2_original_shijimi_state.{h,cpp}` carries the plant-origin Wait/Fly/Fall/
Dead/Leave transitions and separate simulation, culling and leader-cluster
phases. Its source controls check attachment-only Fall, the authored END
boundary for drops, exact source counters and the absence of timed Leave
cleanup. It is an unbound mechanical component, not a native gameplay test.
Native services still must provide genuine attachment, floor triangles,
source animation keys, transforms, appearance and scene-owned retirement.

`tools/p2_shijimi_effect_resources.py` extracts verified genuine PID21/22/23
and `IP2_stardust1_i` from GPVE01 game.jpc into private output. This does not
reuse the Watage PID484 renderer. The native continuous chase emitter and
billboard rendering remain unqualified.

The source77 geometry importer `tools/p2_original_shijimi_resources.py`
authenticates all three original archives, literal three-joint rig, collider
and exact carry/dead/move BCA identities before writing the native bank.
The native `SourceBank` consumes 28 sampled render poses and all109 original
joint0 frames. Mechanical collision uses the integer BCA sample and actual
source key clock independently of visibility. Native bodies must own distinct
flattened geometry. SourceBank compilation does not prove body ownership or
Pikmin attachment; both remain native acceptance requirements.

The private composition entry is `tools/original_sentinel_build/`. It consumes
the real resource owner's build harness and adds Sentinel Honey/state sources
and strict controls. Only the coordinated GitHub runner may qualify the heavy
native composition. Syntax-only compilation is not a linked executable proof.

## Direct gameplay smoke script

Use a fresh private original Forest arena/card with 20 starting Pikmin and a
960x540 centered window. Stop on captain down or startup extinction.

1. Walk the captain into the actual source50 forest/plantsgen.txt#12. Observe
   its touch animation and four visible Yellow followers. Verify the fifth
   object is the hidden leader using the typed source journal, not a visible
   replacement actor. Walk through it again after animation END: no new group.
2. Throw a Pikmin onto a follower. Observe real attachment, Fall, Dead END,
   the actual Honey drop, and normal nectar drinking/maturity change. Ordinary
   damage and a synthetic health write are not substitutes for attachment.
3. Repeat at actual source87 forest/plantsgen.txt#28. Its child origin uses
   source fp27=70. Confirm independent parent/emission ownership.
4. Leave the scene with a surviving follower and a loose Honey. Re-enter and
   inspect the actual scene lifetime behavior. Save/resume through the ordinary
   source card UI when that path is admitted. No duplicate child/drop event or
   stale leader reference may survive; saved child state must use no-init
   allocation and must not replay birth/init RNG.

Required native gates remain unqualified until the real dynamic source77
adapter, native receiver/animation clocks, shared typed Honey ancestry, genuine
TChouDown effects, and source checkpoint provider execute together. Preserve
failed runs and label source controls separately from direct gameplay.

## Draft actual native factory contract

`pc_p2_original_shijimi_native` owns real native pool bodies and distinct private
geometry, with source77 sphere seating and motion bank. `foliage::Native` borrows
this manager before preflight. Only the private Sentinel composition enables
these hooks; ordinary production rejects source50/87 without that composition.

The scene owner supplies actual parent/emission authority, dynamic child ledger,
surface/cave identity, same source RNG raw discard, genuine appearance/fade/latch
effects, and actual AILOD culling. Source77 raw capacity is 10 on the surface and
25 in caves; capacity exhaustion remains a successful null birth with no scale
or init RNG. Culling uses source visibility/Pikmin-cell state and suppresses FSM,
animation and physics updates. The source Cullable flag starts disabled, is
reenabled by follower flight, disabled on Fly entry and enabled on Leave entry.

State retirement is deferred until the source state callback completes, then
retires the actual event/journal, detaches real Pikmin and releases geometry.
Unexpected native kill removes ownership without recursively killing the body.

This factory is not qualified gameplay. The actual scene composition, genuine
continuous 21/22/23 renderer and Hit24, original color material application,
source physical checkpoint provider, native map/receiver behavior and direct
20-Pikmin gameplay remain open. The source-manager and native pool limits are
separate; root reservation does not promise all later children will be born.

The separate `DownEffects` source control consumes only SHA-verified genuine
GPVE01 21/22/23 and stardust bytes. It preserves the JPA first/fractional rate,
point-volume RNG, particle lifetime/moment, accumulating gravity, scale/alpha
flick and rotation, source2048-entry trig frontier, and fade/drain. Positions
follow the body for later births; existing particles remain independent.
Actual scene clipping is injected at the source30 radius after emission, so
previous clipping suppresses births and current clipping suppresses drawing.
A restart after fade requires a fresh emitter handle while old particles drain.
The private composition additionally links `NativeDownEffects`, a distinct GX
rotating-billboard renderer with the genuine64x64 I8 texture, source additive
SRCALPHA/ONE, alpha>10, LEQUAL/no depth writes, source color/global color mixing
and source30 clipping. The ordinary Teki manager advances it once per step,
including detached drain. Native syntax passes; actual linked rendering and
scene ownership remain unqualified. Hit24 and the physical provider remain
open. The genuine-resource controls are source evidence only.

## Released GenPiki attachment reference preparation

The attachment successor uses the unchanged owner397599b3 SDK (four imported
files, separately identified predecessor). GenPiki references serialize complete
catalog/sourceKey/recordUID/successful attempt/activation and local position;
native pointer/lifetime never enter saved bytes. The successful attempt already
identifies the member, including failure gaps: do not invent another ordinal.
Current process incarnations reject pending, expired or reused body pointers.
Saved ancestry resolves to fresh handles supplied by the actual party owner,
with independent source membership checks and unchanged output on refusal.

The native reader traverses actual sticker links/part/local positions and
rechecks topology and incarnation after authority queries. Only GenPiki is
prepared here; unknown, BudConversion or Onyon provenance must refuse instead
of losing relationships. The reader is not yet linked to a live source77 scene.
This reference preparation does not allocate bodies, apply stick/FSM state,
implement the full physical provider, or publish a graph. SAVE admission stays
closed until actual cross-family party/whole-context restoration is complete.

The next native consumer exposes `Native::captureGenPikiAttachments`. It selects
the actual owned source77 body and its own `st__` part, captures the producer's
full child identity, and guards membership callbacks with the source77 body's
current process incarnation. The helper still requires the caller's independent
selected whole-graph `AttachmentAuthority`; a live Piki handle alone is not that
authority. A callback that retires/reuses the source77 owner refuses before the
reader continues. All outputs stay unchanged on refusal.

This consumer is syntax-qualified with actual native headers. Its implementation
requires `PIKMIN_ORIGINAL_SENTINEL_ATTACHMENTS` and the actual released Piki SDK
owner plus attachment TUs in the native link; without that composition the API
explicitly refuses. The old private component graph does not link test observers
as a substitute. Whole-party membership/mapping has no released contract yet,
so scene wiring, linked qualification and physical capture acceptance are open.

## Root production intake recipe

The successor to qualified private composition353 uses the root entry point:

```powershell
cmake -S output/native-original-sentinel -B output/source77-root-build -G Ninja `
  -DPIKMIN_ORIGINAL_SENTINEL=ON -DCMAKE_BUILD_TYPE=Release `
  -DPIKMIN_NETPLAY_BUILD=OFF -DPIKMIN_NATIVE_JAUDIO=OFF `
  -DPIKMIN_NATIVE_OPTIMIZE=OFF -DPIKMIN_ENABLE_IPO=ON
cmake --build output/source77-root-build --target pikmin_pc
cmake --build output/source77-root-build --target pc_p2_original_shijimi_group_test
ctest --test-dir output/source77-root-build -R "^pc_p2_original_shijimi_group_test$" --output-on-failure
```

Use a private build directory and the supported platform toolchain. The root
option defaults OFF. ON adds the ten source77 TUs once to `PC_PORT_SOURCES` and
sets consistent actor/attachment guards for the game and linked legacy/runtime
fixtures. The source77 harness now selects this root option; it no longer
injects production sources or definitions. `original_resource_build` likewise
obtains the production dependencies from root CMake, without duplicate TUs.

Required source intake is the complete PR208 source77 leaf set plus its eight
owner-pinned1c4 Honey/typed-ancestry dependency files and the released actual397
Piki SDK/Body hooks. Keep maintained successors, Watage and foliage93/brown-large
cases; do not overwrite those owners from the older component branch. This
option is a code/link intake, not actual Scene or whole-party admission. Genuine
private banks and concrete parent/emission/birth/retirement/AILOD/FX services,
independent selected whole-party membership, and the complete cold graph remain
required. Missing services refuse; no Scene or party stubs are supplied. Gameplay
and SAVE remain unqualified. Prior353/union06/07 receipts describe the earlier
private harness composition and must not be relabelled as root-entry evidence.
The root source77 option also declares the pure group control target once. Its
two sources are the actual producer/journal implementation and the controlled
RNG/lifecycle/drop/codec test; the test main is never a production game source.
The private wrapper only relocates that target's output for receipt hashing.
These controls do not provide native gameplay or SAVE acceptance.
