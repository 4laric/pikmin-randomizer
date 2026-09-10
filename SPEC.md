# Pikmin Randomizer implementation specification

Status: proposed implementation baseline, 2026-09-10. Existing native and BBFT code is a preserved prototype; features below are not implemented unless explicitly identified as inherited.

## Product and milestones

Build a Pikmin 1 native-PC randomizer that changes physical part placement, supports a standalone Archipelago world, and can later add selected mechanics inspired by later Pikmin games. Preserve Pikmin 1 movement and squad play. Complete a playable base randomizer before enabling expansion content.

M0: isolated build and standalone seed/session contract.
M1: curated part-placement shuffle with a complete, saveable solo seed and AP seed.
M2: extensible Pikmin types, then Purple/White abilities and matching optional obstacles.
M3: treasure checks and a small handcrafted cave using validated expansion mechanics.

Rock, Winged, Ice, Glow, procedural caves, multiple captains and Oatchi are deferred research candidates. Do not silently expand the first release to include them. Exact later-game model/animation import is an unproven pipeline; use clearly identified prototype assets until conversion is validated.

## Inherited implementation

The independent native/ snapshot has BBFT transport hooks, full-progression mode with 28 non-Impact-Site ship-part checks, Yellow/Blue Onion discovery checks, area gating, and color grants. bbft/ preserves AP logic and conductor dependencies. Current full progression begins day two in Forest of Hope with twenty reds. This is not yet standalone; the inherited adapter starts fresh native sessions and needs durable resume work.

TheLynk's Pikmin AP release v0.5.1 (commit 592f74a1f0fd6fdf331ce6874ec3f19f353801ae) defines 30 vanilla ship-part locations and optional per-color population thresholds. Our first release focuses on physical placement; population checks are deferred. Reference: https://github.com/TheLynk/Archipelago/tree/Pikmin_apworld_V0.5.1/worlds/pikmin .

## Default seed and progression contract

- First supported profile: tutorial skipped, day-two Forest of Hope start, twenty red Pikmin; Impact Site absent. There are 28 movable ship-part objects and two fixed Onion-discovery checks. A later full-campaign profile can restore Main Engine and Positron Generator after opening/tutorial behavior is audited.
- Red is the starting type. Yellow and Blue are independently received unlocks. Later-area access is independently received. Do not require BBFT's Mario/Zelda regions, Zora Tunic or Bomb Bag. Yellow retains Pikmin 1 bomb-rock behavior.
- Distinguish native part identity, placement slot/check identity, and AP reward identity. A slot's permanent check ID does not change when its displayed physical part changes. A part may move once into any compatible slot; AP reward assignment is a separate shuffle.
- Use a new standalone game identity and versioned location-ID namespace, with an explicit manifest mapping. Do not reinterpret old BBFT saves, IDs or slot data as standalone seeds. Compatibility remains available in the preserved BBFT adapter.
- At delivery, mark the physical slot collected exactly once. In AP mode its reward may belong to another player. Received Ship Repair items drive the standalone repair goal; collecting a physical part must not also grant its shuffled reward locally. Supply 25 Ship Repair items plus five color/area unlocks, with default goal 25. This corrects the draft's impossible 33-item pool for 30 checks; all 28 physical parts remain present. Native ship-part flags can track physical identity, but must not accidentally drive area gates or trigger vanilla victory independently.
- Solo mode uses the same placement, capabilities, item pool and persistence contract with a local reward provider. AP connection is not required for solo. In AP mode journal offline collections for replay but do not guess unreceived rewards.
- Default day policy: retain daylight/sunset play and time costs, disable the campaign failure deadline. Vanilla 30-day challenge is deferred until resource/time feasibility is validated. Victory must have a tested native presentation and durable AP completion signal.
- Losing the squad must have a recoverable path. Exact type recovery and one-time starter-grant rules must be specified and tested; a finite AP grant alone cannot be assumed sufficient for logic.

## Placement and route model

Start with a vetted finite catalog of locations, not arbitrary XYZ placement. Begin with existing part spawn sites, excluding or pinning unsupported scripted drops. Each slot records stable ID, area, spawn transform, acquisition kind (ground or enemy drop), allowed size/weight class, ground clearance, carry-route attachment, obstacle prerequisites, day/respawn behavior, and a validation evidence reference.

Each object records native part ID, model/collision dimensions, carry minimum/maximum, enemy/script dependencies and collection behavior. Preserve individual weights initially. A slot can accept only compatible objects; reject unsupported assignments instead of silently moving them or treating all parts as identical.

A check is logically reachable only if the captain and required Pikmin can reach the object, enough eligible carriers can be supplied, required hazards/obstacles can be handled, and the object can reach the ship along a valid carry path. Account for geometry, object size, water, bomb walls, bridges, slopes, height and carrier throughput. An accessible pickup is not proof of a usable carry route. Do not assume glitches or Winged shortcuts.

Phase A supports within-area assignments over validated ground slots; scripted drops can remain fixed. Phase B permits cross-area assignments only for validated compatible pairs. Report the actual randomized versus pinned slot count in the seed summary. Persist a seed's placement; daily generators and reloads must neither duplicate nor respawn collected parts.

## Generation and runtime boundary

A versioned seed manifest contains seed ID, RNG algorithm/version, profile, area/slot catalog versions, physical assignments, AP check mapping, goal/day policy, enabled content, and required adapter capabilities. Keep reward spoilers separate from normal runtime manifests where possible. Runtime validates the manifest before changing game state and rejects unsupported versions/features.

Apply relocation at generator/spawn boundaries and collection attribution at ship-delivery boundaries. Suppress each original spawn only when its replacement assignment has been accepted. Preserve native model/carry behavior. Enemy drops need explicit ownership and duplicate protection.

Both solo fill and AP fill must use the same location requirements derived from placements. Generate progression spheres, validate initial reachable checks and all required unlocks, and reject color/area self-locks. Failure should name the unsatisfied slot or requirement. AP inventory is authoritative for received rewards; local physical completion is authoritative for object persistence, with reconciliation rules for reconnects.

## Save and isolation requirements

Use per-seed, per-slot state separate from original BBFT saves and user campaign saves. Persist physical collections, submitted/pending checks, received-item cursor/idempotency state, goal state, native day/area/squad/Onion state, content versions and manifest fingerprint. Use crash-safe writes. A mismatched save must fail clearly rather than reset or merge automatically. Repeated reconnect, restart and area transitions must not refill starter grants, duplicate parts or lose checks.

Build in new local directories. Do not reuse original CMake caches, relink the shared Archipelago installation, or change BBFT playtest packages. Audit inherited launch scripts for absolute paths before use. Source publication/provenance and asset packaging are separate from the planning repository; no original game assets belong in it.

## Additional Pikmin types

First replace hardcoded three-color assumptions with a type registry/capability model. Audit population counts, selection UI, models, particles, combat, throwing, carrying, hazards, Onion storage, Candypops, reproduction, extinction recovery and save serialization. Preserve the three original types' behavior. Every new type has an explicit save ID and feature/version requirement.

Purple MVP: weighted carrying (target ten carrier units), a heavier/slower throw profile and landing impact/stun. Distinguish carry units from occupied attachment slots. White MVP: faster travel, poison immunity, and poisoning an enemy that consumes one; poison obstacles supply a reason to use the capability. Buried-treasure detection is a later increment. These are adaptations with documented tuning, not claims of exact sequel parity.

Initial acquisition uses AP/solo type unlocks and a documented native population source with extinction recovery. Do not require importing the later games' cave-only lifecycle or Onion rules. Expand logic only when mechanics and renewable availability have been physically validated. Purple strength must not automatically substitute for Yellow height or bomb capability; White speed does not imply water immunity.

## Treasures and cave slice

Implement arbitrary collectible records beyond the fixed native ship-part table: stable IDs, model/weight/value, collected flags and AP checks. Optional treasure rewards use a separately balanced pool and do not increase the base 25-repair goal implicitly.

First cave is one authored floor with an entrance from an audited existing-area location, a return point, a small enemy encounter and a handful of treasures. Entry preserves selected squad; exit preserves survivors and collected state. Define death/reset, day clock and save/resume explicitly. Proposed default: pause surface day clock underground; returning resumes the same surface day; no free population reset. A cave cannot strand the player behind its own randomly placed unlock. No procedural room assembly in this milestone.

## Verification and release gates

M0: fresh native build, vanilla opt-out smoke, standalone handshake and incompatible-manifest rejection.
M1: catalog/route evidence; deterministic generation and invalid-seed rejection; at least 100 generated seeds across supported profiles; native pickup/carry/delivery coverage for each supported slot family and heaviest compatible object; complete solo run and AP run; restart, offline collection/reconnect, day transition and extinction recovery exercised. Tests must check real contracts rather than repeat implementation tables.
M2: original-color regression plus native fourth/fifth type creation, selection, storage, save/load and ability playtests; logic never assumes unimplemented abilities.
M3: enter/collect/exit, save inside cave, resume, wiped squad recovery and AP dedup verified. Gameplay sign-off remains separate from build/unit success.

Risk order: carrying/navigation and script identity; save/goal authority; color generalization; asset/animation conversion; new environments. Finish the base seed gate before enabling expansion mechanics by default.
