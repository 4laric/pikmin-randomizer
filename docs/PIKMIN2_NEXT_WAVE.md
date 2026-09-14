> Current combined QA source: root `99ca118733b6919548565af538971ff284df7daf`, native `9b15d371cc63e7b0154bfc3dfc2cf5be9874c754`. See [combined QA pin](PIKMIN2_COMBINED_QA_PIN_437.md) for the executable hash and scope. This supersedes older source/build pins below. `output/p2-main-review` at `ef1cace` is an old dirty worktree, not the maintained remote head. `output/native-sweep437` remains assignment-5 WIP, not an export source.

# P2 next wave: Snow first, Dwarf Orange second

Latest integrated baseline and acceptance: [cohort preparation sweep](PIKMIN2_SWEEP_COHORT_437.md). Older queue entries below are historical and must be checked against this continuation.

Current integration baseline: [full integration pass #437](PIKMIN2_FULL_INTEGRATION_437.md). Its combined source and remaining-work ledger supersede historical pending-merge statements below.

Dispatch guide, 2026-09-14. Tracking #454; coordination #186. Implementation owner for this document: Codex through shared account 4laric. This is a work plan, not a gameplay acceptance report or a reassignment of active owners.

Start from the latest `origin/codex/p2-main-review` (draft #432). Current approved native baseline is `5b446a64156b338628c6d636cab3dc76f5a9d224`, clean. Read [the fixture-command sweep](PIKMIN2_FIXTURE_COMMAND_SWEEP_437.md), [the roster-readiness sweep](PIKMIN2_ROSTER_READINESS_SWEEP_437.md), [the receipt-provider sweep](PIKMIN2_RECEIPT_INTEGRATION_437.md), [the Hiba sweep](PIKMIN2_HIBA_INTEGRATION_437.md), [the placement/native queue sweep](PIKMIN2_PLACEMENT_SWEEP_437.md), [the shared-provider sweep](PIKMIN2_SHARED_PROVIDERS_437.md), [the Waterwraith dependency sweep](PIKMIN2_WATERWRAITH_INTEGRATION_437.md), [the wave-three handoff review](PIKMIN2_WAVE3_REVIEW_437.md), [the pre-wave review](PIKMIN2_PREWAVE_REVIEW_437.md) and [staging disposition](PIKMIN2_INTEGRATION_STAGING_437.md) for integrated tooling, blocked actors and the next queue; production evidence is pinned in [sweep #456](PIKMIN2_INTEGRATION_456.md). The current native integration worktree is `C:/Users/alari/pikmin-randomizer/output/native-sweep437` on `codex/p2-sweep437`; create your own native worktree from the pinned commit. The older `output/p2-main-review/native` is occupied by assignment 1 and must not be switched or used as an integration source. Record the exact root HEAD you use. Never overwrite the current engine with an older worker export.

This guide sets next-wave priorities. Keep the existing **01–33 lane numbers** and owners from [the fan-out guide](PIKMIN2_IMPLEMENTATION_FANOUT.md). Its build isolation, ownership and fixture rules still apply. Earlier lists telling agents to recover already-integrated hardlane/projectile/clock modules are historical; inspect the actual source first.

## Sweep reporting: remaining lanes

Every integration sweep must finish with the remaining **numbered-lane** count and change since the previous sweep. Maintain [the lane completion ledger](PIKMIN2_LANE_COMPLETION.md), separating full-lane completion from worker-finished/pushed slices. Current tracker baseline: **33 open (32 implementation/QA + integration), 0 full lanes recorded complete**. This is not a running-session count. Refresh tracking issues and acceptance evidence before decrementing it.

## Current dispatch: five focused assignments

User-approved focus, 2026-09-14: complete **opt-in Snow Bulborb first**, then **Dwarf Orange Bulborb**, through a real generated run. Documented P1-derived behavior is acceptable for this experimental milestone. Full P2 source fidelity remains a separate milestone; no identity is admitted by this document.

These five assignment numbers are dispatch slots, **not replacements for the existing 01–33 lane IDs**. The five currently active agents keep their current claims and finish their slices. Assign new or freed sessions to the work below; do not start duplicate owners. Codex remains lane 01 integration in addition to these five assignments. Record each session's assignment number, existing lane IDs, scoped issue and owned files before work begins.

| Assignment | Existing lanes / ownership | Concrete deliverable and acceptance |
|---|---|---|
| **1. Generated spawn connection** | 02/03/05; one accountable owner across the generator, roster and installation boundary | Carry Snow's exact roster identity from opt-in seed generation through validated fresh/cached content staging into an ordinary live native actor. Preserve legacy seeds and reject missing/wrong content. Deliver the live binding, not only parser/query markers or a receipt echo. Coordinate approved slots with assignment 3. |
| **2. Snow encounter completion** | 13, consuming 07/08/10; Snow-local modules | Pin the exact Snow source ID and asset bank; state which behavior is P1-derived. Prove autonomous interaction, real damage and lethal combat, corpse and physical carrying, plus clean actor teardown. Reproduce historical lifecycle evidence on the current pair and connect to assignment 1's ordinary spawn. Do not use forced health/death or fixture-only registration as final acceptance. |
| **3. Placement, rewards and persistence** | 04/06/07, coordinated with 03; one owner for this cohort's lifecycle | Approve a small explicit set of Snow-compatible slots using observed terrain, space and carry routes. Connect actual reward delivery to the supported campaign endpoint; prove revisit and process restart preserve identity and neither duplicate nor lose rewards. Include natural cleanup, address reuse and unaffected P1 controls. Keep Pod/Poko evidence separate from ordinary Onion/AP evidence. |
| **4. Independent acceptance** | 33; lane 01 supplies the integrated build | Prepare the reproducible generated-session test while implementation proceeds. On the pinned combined build, exercise generation, automatic staging, ordinary spawn, natural combat, delivery, revisit and restart. Test opt-in off/P1 controls and mixed P1/P2 scenes. After Dwarf Orange passes independently, test both P2 identities together with recorded frame-time, memory and actor budgets. Report failures without simultaneously changing production code. |
| **5. Dwarf Orange follow-on** | 13, consuming 07/08/10; variant-local work separate from assignment 2 | Prepare the second exact identity using the same spawn, staging and reward interfaces. Finish or explicitly document partial KochappyBase/P1-derived behavior; prove natural combat, death, carrying and cleanup. Existing bind/draw smoke is insufficient. Prepare in parallel, but admit only after its own full product-chain acceptance. |

Assignments 2 and 5 share family lane 13: reserve distinct files and have one named owner for shared KochappyBase edits. If an active owner already covers either species or a shared provider, extend that claim or take a non-overlapping slice; do not fork a competing implementation. Assignments 1 and 3 agree manifest identity, slot selection, actor lifetime and reward/save contracts before changing their shared interfaces. Routine family-local implementation and private builds remain autonomous.

### Outcome and acceptance scope

**Generate seed → automatic content staging → ordinary native spawn → natural interaction/combat → death/drop → actual transport/reward → revisit → process restart.**

First deliver this chain for Snow in a restricted, explicitly opt-in pool. Then repeat it for Dwarf Orange and test both together. Snow success does not admit other Bulborbs. Yellow Wollywog is a reserve candidate; Mamuta, Groink and other families continue under existing claims and are not dependencies of the first cohort.

Experimental admission may retain declared P1-derived AI, timing or animation approximations. It still requires working combat/receivers, legal placement, correct supported rewards, cleanup and persistence. Record the chosen behavior and known deviations beside the evidence and expose the experimental scope to the user. Do not label proxy acceptance as full P2 fidelity or whole-family completion. Any required roster/schema support for this distinction belongs to assignment 1; preserve existing validation and default-deny behavior until reviewed evidence supports explicit opt-in admission. A private candidate validation path must not enable unaccepted identities in normal generation.

Historical Snow evidence includes physical Pod delivery with a P1 host; it does not prove the current generated campaign path. Dwarf Orange has combined bind/draw evidence and partial behavior, not accepted natural delivery. At this dispatch revision the admitted enemy roster is still empty.

Dispatch progress (2026-09-14): assignment 5 (Dwarf Orange, source 44) wired the generated bind path in a private native worktree on the maintained baseline container where Snow (source 45) generated binds — `pc_p2_generated_bind` now dispatches 44 to `TEKI_Chappy` via `pc_p2_dwarf_orange_bind` gated by the dwarf-orange generated marker, with the Kochappy FSM auto-opting in for the bound spawn and an optional `assets/p2-dwarf-orange-fsm.txt` override. Private build `output/native-sweep437-build` links clean (ninja: no work to do). Root side: `experimental/pikmin2_dwarf_orange_content.py` emits the identity-44 content manifest (15 models + bank/profile config, hash-verified) and `experimental/pikmin2_candidate_session.py --source 44` provides the private pre-admission candidate scope; 11 new focused tests pass and the candidate/staging/install/enemy/placement suites stay green (118 tests + 17 subtests). Remaining for assignment 5: real-GL generated acceptance (spawn → combat → death → carry → reward → revisit → restart) and `cleanup_reentry` re-exercise on the pinned pair before admission; `transport_reward` stays lane 06. No identity is admitted by these changes.

## Assignment 4 does not wait for admission

Use [the private Snow candidate QA runbook](PIKMIN2_CANDIDATE_QA.md) to gather
pre-admission evidence on the published combined native build. Normal generation
remains gated. The native generated binding is already integrated; waiting for
lane 02 to admit Snow before testing it creates a circular dependency.

## Mandatory first actions for every session

1. Read AGENTS.md, this guide, the latest integration sweep, your parent issue and current #186 claims. Reuse your existing scoped issue; update its acceptance criteria and assign it to the authenticated account. Record the actual executing agent/session and implementation owner accurately.
2. Pin root/native base and head, list dirty state and candidate commits already present. Select one concrete source ID and one missing end-to-end slice. An existing owner keeps their lane; ask integration to resolve overlapping claims before editing the same modules.
3. Agree each required provider/consumer interface with its owner: caller, update phase, identity/lifetime token, inputs, result, failure behavior and one real acceptance case. Record this in the issue. Do not invent a competing shared framework.
4. Adopt the current fixture. Regenerate the arena in a new private output directory using the current overlay, which adds **20 red Pikmin when no Pikmin generator exists**. Existing squads are preserved, not topped up. Verify live valid spawns; document species-specific squad overrides.
5. Use **960×540, windowed and centred after persisted settings load**. Set `PIKMIN_P2_ROOM_WINDOW=960x540`. Replacement-main fixtures must implement and log equivalent startup themselves; an environment variable cannot fix an old binary. Observe gameplay without immediate extinction. Do not disable extinction globally.


## Local P1/P2 assets: verified paths for every lane

Verified on this Windows host during the asset-unblocking sweep (#437). Private worktrees do **not** inherit ignored assets from the main checkout. A missing `output/...` under your worktree is not evidence that assets are unavailable. Use these absolute inputs, read-only; write generated content into your own new private output directory.

| Input | Verified absolute location | Use |
|---|---|---|
| P1 extracted asset root | `C:/Users/alari/bbft/dist/cohesion/pikmin/assets` | Pass as `--assets` to room/family arena staging. Contains `dataDir/stages/practice/default.gen` and `dataDir/stages/chal0/default.gen`. This is an input asset tree; do not edit the original BBFT checkout. |
| P1 disc, if extraction is needed | `C:/Users/alari/pikmin-local/Pikmin.iso` | Header `GPIE01`, revision 1; 1,459,978,240 bytes. Usually use the extracted tree above. |
| P2 source disc | `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso` | Header `GPVE01`, revision 0; 995,557,376 bytes. Pass to family extractors using their documented `--iso` or `--source` option. |
| P2 local disc copy | `C:/Users/alari/pikmin-randomizer/assets/disc/PIKMIN2 for GAMECUBE.iso` | Present, same header and byte length as Downloads; byte identity not established by this sweep. |
| Historical P2 test image | `C:/Users/alari/pikmin-randomizer/output/pikmin2-runtime/pikmin2-source-test.iso` | Present, `GPVE01` revision 0, 1,000,762,688 bytes. Different length: do not silently substitute it for a pinned source. |
| Converted P2 room inputs | `C:/Users/alari/pikmin-randomizer/output/pikmin2-room105` | Contains `room.mod`, `room.ini`, `treasure.mod`; pass as `--converted` to the current room stager. Old executables in this folder are not the current fixture baseline. |
| Partial extracted P2 inputs | `C:/Users/alari/pikmin-randomizer/output/pikmin2-extract105` | Contains `arc`, `texts`, `treasure`; not a universal family import or P1 asset root. |
| BombSarai extracted inputs | `C:/Users/alari/pikmin-randomizer/output/pikmin2-extract-bombsarai` | Family-specific input for `experimental.pikmin2_bombsarai_assets --source`; not interchangeable with a converted install bank. |

From your current root worktree, stage a **fresh** generic room without launching it:

```powershell
$laneP1 = 'C:/Users/alari/bbft/dist/cohesion/pikmin/assets'
$laneP2 = 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso'
$laneRoom = 'C:/Users/alari/pikmin-randomizer/output/pikmin2-room105'
$env:PYTHONUTF8 = '1'
$env:PIKMIN_P2_ROOM_WINDOW = '960x540'
py -3.12 scripts/preview_pikmin2_room.py --assets "$laneP1" --converted "$laneRoom" --output output/your-lane-room-runs
```

The stager creates a new run subdirectory and applies the current starting-Pikmin overlay. Use the appropriate family stager to add that family's actors/configuration; the generic room alone does not install enemy assets. Check the family module's `--help` before running it: extractor flags differ. For example, BombSarai accepts `--source "$laneP2"`, whereas many other extractors accept `--iso "$laneP2"`. Choose a NEW lane-owned output directory; do not overwrite shared banks or old evidence.

Existing banks to inspect include absolute main-output subdirectories `bigtreasure-import-01`, `groink-weighted-assets-09`, `p2-jellyfloat-assets-01`, `p2-frog-import`, and `pikmin2-kogane-assets`. These are caches, not universally approved inputs: inspect their manifests, source hashes and required format before reuse. Regenerate when stale or incompatible. Pin the actual ISO/resource hashes in lane evidence; header verification alone does not prove source content identity.

Before reporting an asset block, test the absolute paths above and report the exact missing file, command and error. Distinguish a missing disc/tree from an unsupported conversion, missing family bank, bad manifest or stale fixture. Do not ask for another asset upload merely because your worktree's relative path is empty. Keep original assets read-only, do not relink Archipelago, and never commit assets. Runtime acceptance still requires the fresh arena, current privately built executable and observed live squad/centred-window evidence described above.

## Previous broad dispatch: superseded for new assignments

The five focused assignments above replace the earlier instruction to staff the full shared dependency spine and all family lanes. The tables below remain lane ownership and backlog references, not a request for another 33-session wave. Existing active owners continue their claimed work. Activate additional shared work only for a named blocker in the first cohort; preserve useful family handoffs without making every family a prerequisite.

Private builds remain parallel, bounded by host RAM/link capacity, with at most one heavy job per worker. Reserve one real-GL/input acceptance run at a time on this host in #186 and release it afterward. Integration alone writes the maintained build/export and draft branch. Keep shared-file ownership explicit.

## Shared lanes: each provider must ship a working consumer

| Lane | Next deliverable | Consumer / acceptance |
|---|---|---|
| **01 Integration** | Reconcile shared identity/receiver/lifetime candidates needed by the selected cohort, then species branches one family at a time. Publish accepted root/native pair and exact remaining queue. | Build/export parity and changed combined gates. Preserve upstream, save roots and current fixture fixes. No wholesale old snapshots. |
| **02 Roster/admission** | Per-ID gate ledger connected to an explicit deny-by-default admission set. Distinguish source enemies, variants, helpers and aliases. | 03 can select only reviewed IDs with legal encounters, content and evidence. Policy presence or taxonomy membership is not eligibility. |
| **03 Seed/native bridge** | Wire one admitted ID through the actual opt-in generator, versioned manifest/parser and ordinary native spawn path. | With 02/04/05: same seed, revisit and restart preserve identity; unknown versions/content fail clearly; legacy seeds retain behavior. Preview-only sidecars do not pass. |
| **04 Encounters** | Validate concrete placements for the selected IDs: terrain, space, routes, homes, helpers and protected checks. | Native XYZ/terrain and actual return-route evidence; reject incompatible slots. Boss adapters remain separate from universal replacement. |
| **05 Installation** | Consume existing family installers and stagers from the generated-session launcher/cache path. | Fresh and cached launch without manual copying; interrupted staging and wrong/missing content fail safely. No assets committed or shared AP relinking. |
| **06 Rewards/persistence** | Connect one real family drop/transport endpoint to durable ordinary Onion/AP receipt handling. | Family + 03 prove no duplicate or lost required reward across revisit/process restart. Host JSON dedupe and injected Pod delivery alone do not pass. Keep Pod/Poko separate. |
| **07 Lifetime/fixtures** | Reconcile centralized forget/rebind ownership with one live family, including late birth and address reuse. | Natural death, full teardown and new scene cannot retain stale actor/helper references; control actor unaffected. Manager reset alone is narrower evidence. |
| **08 Events** | Move one family gameplay effect onto authoritative simulation events. | Same attack/drop count across frame skips, loops, pause, interrupted motion and actor generation change. Draw-observed event logs are insufficient. |
| **09 Assets/rendering** | Close a named consumer bank/material failure, with reproducible staging and source comparison. | Missing clips/resources and approximation explicitly counted. Preserve strict defaults; no blanket converter rewrite or renewed claim that all families are blocked by #128. |
| **10 Receivers** | Reconcile electric/gas/attack adapter candidates and connect an actual emitter/attack volume to a live target. | Paired with 11 and a family: valid hit changes health/state; immunity rejects it; lethal path works. LTO retention or direct API injection is not an emitter test. |
| **11 Species/Bulbmin** | Reconcile identity storage, capability routing, recruitment and checkpoint schema as a coherent ordered series. | Paired with 10/12/03: selected species survives actual routing and restart; old checkpoint behavior explicit. No competing save-schema patch from a family lane. |
| **12 Captains/squad** | Review slot-0 adapter and provide the real captain/squad interface needed by one captor or Antenna Beetle. | Target identity, claim/release, interrupted capture and cleanup demonstrated. Unsupported second-captain semantics stay explicit. |
| **33 Independent QA** | Reproduce the first generated-session chain; add two-species mixed scene immediately after the second admission. | Immutable integrated build, natural evidence, replay/restart and agreed frame-time/memory/helper budgets. File precise failures; do not mutate production simultaneously. |

### Lane 04 blocker (2026-09-14)

Lane 04's concrete placement model is integrated ([sweep](PIKMIN2_PLACEMENT_SWEEP_437.md)),
but no candidate can be admitted yet:

- Native XYZ/terrain/return-route evidence is still false and needs a reserved
  real-GL run (lane 01/33), so every `(slot, identity)` pair remains `denied`.
- `Jigumo` (Hermit Crawmad) is `unplaceable`: the campaign table exposes no
  nest-anchor slot for its `PanHouse` child.
- Lanes 13/14/16/19 must confirm the per-identity space/water/home/helper facts,
  lane 02's evidence overlay contains candidates but no admitted identities.
  Assignment 1 must inspect the integrated manifest/schema support before adding
  cohort metadata; do not treat historical interface proposals as missing code.

## Family lanes: finish a concrete identity before expanding variants

These rows retain existing family ownership and backlog scope; new dispatch follows the five assignments above. Owners implement family-local FSM/events/receivers/assets and additive hooks in private worktrees. Shared changes remain with the provider above. Reuse current native modules and candidate series; first inspect what is already integrated.

| Lane | Next end-to-end slice | Providers / boundary |
|---|---|---|
| **13 Bulborbs/dwarfs/Sheargrubs** | One exact variant: natural fight, death, carry/reward and revisit. Preserve variant-specific source rules. | 06/07/08/10. Snow success does not admit all Bulborbs. |
| **14 Ground invertebrates** | Reconcile one species branch; complete its natural receiver/death/re-entry chain before merging the whole umbrella. | 01/07/08/10; 23 for plant interaction. Pair discharge and group births need their own evidence. |
| **15 Flying/ambient species** | One real wind or nectar lifecycle from ordinary spawn through reward/cleanup. | 06/07/08/10. Honeywisp contract or Mar harness alone is not execution. |
| **16 Frogs/aquatic** | One frog combat chain or source-correct harmless aquatic escape/death chain in a legal slot. | 04/06/07/10; 12 for captain-dependent behavior. Water and land variants separate. |
| **17 Reward beetles** | Natural hit-triggered drops with finite counts, real collection and restart dedupe. | 06/07/08/10. No unlimited farming or alias rewards. |
| **18 Breadbugs/nests** | Real contested cargo, nest ownership, interruption/death release and exactly-once ordinary reward. | 04/06/07. P1 proxy motion and new receipt helpers are foundations, not P2 contest parity. |
| **19 Mamuta** | Extend pinned natural evidence through actual transport/reward, territory/flick and revisit. | 06/07/10. Reuse 8/8 worker evidence without presenting it as a new integrated-build run. |
| **20 Cannon/projectiles** | Ordinary cannon actor + moving muzzle + Stone contact + actual receiver mutation; real requested child births. | 07/08/10. Shared Rock/Egg/Bomb primitives serve 21/25/26/27; do not fork them. |
| **21 Groink** | Natural targeting/burst and shell effects, followed by source revival/carcass recovery. | 06/07/08/10/20. Resolve current owner claim before resuming parked work. |
| **22 Elemental/Dweevils** | One actual elemental emitter and damageable enemy through death/reward. | 06/07/08/10/11; 20 for BombOtakara. Reference Python behavior does not fix FireOtakara health. |
| **23 Flora/Candypops** | Source pellet capture/release or real Pikmin conversion/refund with population conservation. | 06/07/09/11; 14 plant contract. Proxy Chappy corpse is not Pelplant completion. |
| **24 Bulblax/larvae** | Close missing natural combat, attachments and reward gates on existing King/Queen work. | 04/06/07/08/10; 09 materials. Avoid repeating already-passed injected gates unchanged. |
| **25 Snagrets/Crawbster** | Integrate source host, apply vulnerability window and realize Rock/Egg decisions as births. | 01/04/07/08/10/20. Hazard markers without births/damage do not pass. |
| **26 Long Legs/Man-at-Legs** | Connect policy to live leg/weak-point attacks, natural death and re-entry. | 04/07/08/10/20. Preserve shared collision/helper budgets. |
| **27 Dirigibug** | Ordinary carrier + animated capture joint + bomb release, interruption and ownership cleanup. | 07/08/10/20. Isolated bomb arena is not a natural carrier. |
| **28 Antenna Beetle** | Actual visual actor and follow locomotion connected to natural claim/reclaim/death release. | 07/08/09/11/12. Existing claim policy does not establish locomotion. |
| **29 Jellyfloats** | Lesser flight/suction/attachment, digestion and interrupted release through death; then Greater. | 07/08/10/12. Admit variants separately. |
| **30 Snitchbugs/Demon** | Ordinary captor target/admission, moving attachment, escape/drop and teardown. | 07/08/10/12. Captain drop hook alone is not a complete captor. |
| **31 Waterwraith/Tyre** | Consume staged two-species visuals, connect roller ownership/attacks and Purple vulnerability through cleanup. | 04/07/08/09/10/11. Staging profile currently precedes the native consumer. |
| **32 Titan Dweevil** | Connect existing FSM host to ordinary update and natural weapon hits, then real phase transition/drop. | 04/06/07/08/09/10/20. Existing four-weapon injected fixture and rebased identical series need no reimplementation. Audit actual clip availability. |

## Admission gates and evidence

Use PASS / FAIL / BLOCKED / UNTESTED / source-backed N/A per concrete ID. Every PASS includes root/native/executable pins, fixture/run path, inputs, observable result and interventions. Never promote injected acceptance to natural acceptance.

| Gate | Required observation |
|---|---|
| A Identity/content | Exact source ID/variant/helpers at ordinary spawn, validated assets, no silent P1 fallback. |
| B Declared behavior | For this opt-in experimental cohort: autonomous, playable behavior with P1-derived AI/timing/animation deviations explicitly recorded and tested. Full P2 fidelity separately requires source-correct states, events and interactions; experimental PASS does not satisfy that milestone. |
| C Combat/receivers | Natural attack/admission, vulnerability and immunity, interruption and lethal path where applicable. |
| D Death/drop/transport | Correct corpse/pellet/treasure/no-drop rule; real transport/collection where applicable; required checks preserved. |
| E Lifetime | Natural death cleanup, recycled address, late birth, scene exit/re-entry and helper ownership; no stale reference or control contamination. |
| F Persistence | Same seed identity/content after process restart; earned rewards neither repeated nor lost. Save timing follows the supported product contract. |
| G Product/mixed scene | Generate/install/launch without manual sidecars; legal placement; combined scene respects explicitly recorded performance and actor budgets. |

02 records admission only after 01 accepts the integrated pair and 33 reproduces applicable gates. Track separate columns for **policy implemented**, **native connected**, **natural arena accepted**, **generated-session accepted**, **randomizer admitted**, and **whole family complete**. Whole family completion requires every parent identity and applicable variant; one admitted identity is still useful progress.

Injected health, forced animation/event, fixed target, fixture-only spawn, fake persistence and direct Pod delivery remain valuable diagnostics. Label them on the same row as their result and retain the missing natural gate.

## Handoff and integration cadence

Send a coherent slice when it closes a dependency or a natural gate. Do not create a fresh integration task for every documentation tweak. Integration batches compatible handoffs and validates their combined effects; there is no fixed clock interval and no permission checkpoint after every routine family edit.

```text
Lane NN / owner-session / existing parent + scoped issue:
Concrete source ID and missing gate addressed:
Root base/head; native base/head; dirty state; ordered commits:
Owned files; shared hooks and provider/consumer agreement:
What is already in the integration branch; what is actually new:
Private build config/path; full native SHA; exe SHA-256; no-work dry run:
Fixture source/provenance; starting squad; observed centred 960x540 startup:
Natural vs injected actions; gates A-G with evidence paths:
Generated-session/revisit/restart result (or named remaining dependency):
Combined-scene impact; known limitations; next consumer:
```

Builds, fixtures, logs, saves, extracted assets and seeds stay under ignored output. Use lane-owned native worktrees/private Ninja builds with the maintained MinGW toolchain and JAudio ON; record actual flags. Follow [fixture build provenance](PIKMIN2_FIXTURE_BUILDS.md). Never push native origin. All GitHub issue/PR commands must explicitly target **4laric/pikmin-randomizer**; do not create coordination issues or comments upstream. Only the existing draft branch is the integration destination unless the user directs otherwise.

## Copy/paste session assignment

Choose assignment 1–5 above and fill in its existing lane IDs and concrete scope. Preserve any active owner claim.

> Take focused assignment N (existing lanes NN; exact identity and file scope: FILL IN). Target opt-in Snow first and Dwarf Orange second. Documented P1-derived behavior is acceptable for experimental acceptance; combat, placement, actual rewards, cleanup and persistence must work. Read AGENTS.md, docs/PIKMIN2_NEXT_WAVE.md and the latest integration sweep. Resume lane NN under its existing owner/issue; do not duplicate active work. Pin the latest approved root/native pair and identify one concrete source ID and missing natural/product gate. Reuse integrated code and agree shared interfaces with the named providers. Deliver the family-local implementation and additive hooks in a private worktree, using live starting Pikmin and the centred 960x540 fixture. Validate natural behavior, death/reward, cleanup and restart as applicable; clearly label injected evidence. Return ordered commits, exact build/run provenance, gates A-G and remaining dependencies. Do not stop at another standalone policy or staging document when the required provider is available. Do not modify main, push native origin or write to upstream GitHub.
