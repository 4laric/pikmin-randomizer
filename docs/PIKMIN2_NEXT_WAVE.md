# P2 next wave: complete playable encounters and admit the first cohort

Dispatch guide, 2026-09-14. Tracking #454; coordination #186. Implementation owner for this document: Codex through shared account 4laric. This is a work plan, not a gameplay acceptance report or a reassignment of active owners.

Start from the latest `origin/codex/p2-main-review` (draft #432). Current approved native baseline is `c223f4424e27ab33beba408dd644362018789708`, clean. Read [the Hiba sweep](PIKMIN2_HIBA_INTEGRATION_437.md), [the placement/native queue sweep](PIKMIN2_PLACEMENT_SWEEP_437.md), [the shared-provider sweep](PIKMIN2_SHARED_PROVIDERS_437.md), [the Waterwraith dependency sweep](PIKMIN2_WATERWRAITH_INTEGRATION_437.md), [the wave-three handoff review](PIKMIN2_WAVE3_REVIEW_437.md), [the pre-wave review](PIKMIN2_PREWAVE_REVIEW_437.md) and [staging disposition](PIKMIN2_INTEGRATION_STAGING_437.md) for integrated tooling, blocked actors and the next queue; production evidence is pinned in [sweep #456](PIKMIN2_INTEGRATION_456.md). Record the exact root HEAD you use. Never overwrite the current engine with an older worker export.

This guide sets next-wave priorities. Keep the existing **01–33 lane numbers** and owners from [the fan-out guide](PIKMIN2_IMPLEMENTATION_FANOUT.md). Its build isolation, ownership and fixture rules still apply. Earlier lists telling agents to recover already-integrated hardlane/projectile/clock modules are historical; inspect the actual source first.

## Outcome for this wave

Deliver a small evidence-selected P2 cohort through:

**generate seed → automatic content staging → ordinary native spawn → natural interaction/combat → death/drop → actual transport/reward → revisit → process restart.**

Start with one concrete source identity, then add a second independently implemented identity and test them together. Choose from the strongest existing family evidence, not perceived simplicity or a promised species count. Initial candidates to assess are lanes 13, 14, 16 and 19; none is pre-approved. A harmless species has source-backed interaction gates instead of invented attacks. Boss, captor and elemental owners continue in parallel.

The exit condition is at least one admitted identity completing the generated-session chain, followed by a two-identity mixed scene with agreed budgets. Do not wait for every family to finish before proving the product path. Do not silently enable unfinished identities to fill the cohort.

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

## Dispatch priorities and parallel width

First occupy the dependency spine: 01, 02, 03, 05, 06, 07, 10 and 33. Pair 10 with 11 when species routing is required. Assign 04 to the actual candidate slots. Then staff independent family owners, with 08/09/12 activated against named consumer gaps. Existing active lanes continue; this is sequencing for spare sessions, not a stop instruction.

All 33 lanes can perform useful source review, private implementation and tests concurrently. Heavy builds are limited by measured host capacity, not session count: each worker has a private build and at most one heavy job; reduce job counts when RAM/link pressure rises. One real-GL/input acceptance run at a time on this host, reserved and released in #186. Integration alone writes the maintained build/export and draft branch.

Do not split one shared file across multiple new sessions. A family owner may divide disjoint species modules after identifying file ownership and interfaces. Each session holds one active slice and at most one ready handoff; while waiting, resolve its named dependencies or improve its natural acceptance evidence.

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

## Family lanes: finish a concrete identity before expanding variants

Each row is an independently assignable lane. Owners implement family-local FSM/events/receivers/assets and additive hooks in private worktrees. Shared changes remain with the provider above. Reuse current native modules and candidate series; first inspect what is already integrated.

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
| B Source behavior | Autonomous states, animation/event ordering and source-correct interactions; resource approximations stated. |
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

> Read AGENTS.md, docs/PIKMIN2_NEXT_WAVE.md and the latest integration sweep. Resume lane NN under its existing owner/issue; do not duplicate active work. Pin the latest approved root/native pair and identify one concrete source ID and missing natural/product gate. Reuse integrated code and agree shared interfaces with the named providers. Deliver the family-local implementation and additive hooks in a private worktree, using live starting Pikmin and the centred 960x540 fixture. Validate natural behavior, death/reward, cleanup and restart as applicable; clearly label injected evidence. Return ordered commits, exact build/run provenance, gates A-G and remaining dependencies. Do not stop at another standalone policy or staging document when the required provider is available. Do not modify main, push native origin or write to upstream GitHub.
