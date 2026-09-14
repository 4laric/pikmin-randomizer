# P2 enemies: full implementation and randomizer blockers

Current integration disposition: [integration sweep #450](PIKMIN2_INTEGRATION_450.md).
Read this before interpreting historical integrated/candidate claims below.

Audit #434, 2026-09-13. Implementation owner: Codex via shared account `4laric`.
Reviewed draft #432 at `92c926e` (native `9735870c`, upstream `511f22fe`),
maintained P2 `ffe6316`, fetched worker branches and current issue comments.
This is an evidence audit, not a new gameplay acceptance run.

**We have substantial conversion, display and bounded mechanics work. We do not
have an all-P2 production randomizer pool.** Completing enemy mechanics and
making those enemies valid seeded encounters are two separate remaining jobs.
There is no defensible percentage complete without a reconciled per-ID roster.

## What changed since the previous blocker list

- Pelplant conversion is integrated: 10/10 clips. Sokkuri/Armor mechanics,
  Mamuta death/corpse and Pelplant proxy lifecycle passed combined integration.
  King tongue/swallow, bombs, WarCry/cross-Emperor, death and reload gates passed
  #422. These are no longer unstarted tasks or pending #422 export work.
- Shared BTK, multi-material binding, skeletal blending, sampled-pose rendering
  and BRK color support have landed. Upstream specular enum/attenuation and
  object-normal texgen fixes are in draft #432. **#128 is no longer a blanket
  converter blocker**, but bank coverage, event adoption, billboard support and
  family-specific fidelity remain open. P2 before/after specular visual review
  is still required; build/startup does not close #239.
- Newer worker evidence exists for all six ground-invertebrate identities,
  Mar/Tadpole, cannon policies, and proxy reward/re-entry. It is not all present
  in the audited draft. Do not confuse a pushed harness with integrated native AI.
- Jellyfloat has install/fixture/capture work in its lane. The old “no arena yet”
  statement was stale; ordinary flight/suction and draft integration remain open.

## First blocker: reconcile what is actually integrated

The previous family status overstates the draft's hard-lane integration. Direct
inspection finds no `pc_p2_hardlanes.cpp`, BombSarai runtime modules, Fuefuki FSM
or BigTreasure host/attack/visual modules in this draft. `pc_p2_bigtreasure.cpp`
is an ownership policy and is not listed in its CMake target. Demon drop-state
hooks exist, but are not evidence of a complete integrated captor.

The hard-lane export `87204df` exists on worker branches and is **not an ancestor**
of the draft. Inspecting its tree confirms the missing modules exist there.
This is an integration gap, not a request to reimplement those modules. A whole
old engine export must not overwrite newer renderer, lifecycle or upstream work.

| Candidate evidence | Audited draft disposition | Next action |
|---|---|---|
| Hard-lane export `87204df`, #244/#245/#246 | Absent runtime seam despite historical “integrated” docs | Reconcile native modules/CMake/setup/tick/cleanup against current engine; repeat affected combined gates. BombSarai's cited prebuilt runtime did not validate the new seam |
| Ground six-species + Mar/Tadpole, #407; root `86aa159`, native `737af8c6` | Sokkuri/Armor present; ElecBug/TamagoMushi/Imomushi/Hana/Mar/Tadpole source modules absent | Integrate native candidate plus harnesses and batch3 parser fix; retain exact bounded claims |
| Cannon integration root `656c556`, native `104d6dfa`; #406/#410–#413/#424/#425/#427 | New cannon/projectile modules absent | Integrate policies/seam, then connect actual actor, moving muzzle, health mutation and item births |
| Lifecycle/reward #397: `6b71b14`, `9280a2f`, native `fb6389ce`; Flora report `2dd19ad` | Earlier lifecycle present; later reuse/reward handoff not accepted by #422 | Reconcile corpse/reward ownership and test address reuse plus exactly-once delivery |
| HikariKinoko #429, root `33c5cac` | Static billboard fallback absent | Review bounded fallback; it converts 1/1 clips but is not camera-facing billboard support |
| Sampled clock/events #431, root `cb253f5` | Candidate contract absent; live consumer migration not done in lane either | Review shared contract, adopt by family, verify exactly-once events independently of displayed pose |
| Jellyfloat #243 / Demon #215–#242 / Groink #198 | Private/policy/partial hooks; no complete ordinary-gameplay chain verified | Inventory exact candidate commits, integrate complete owned paths, then run natural capture/projectile/lifecycle gates |

Candidate evidence above is reported by lane issues, not independently rerun by
this docs pass. Branch tips can move; integration must pin exact commits.

## Second blocker: the production randomizer bridge

Source evidence: `randomizer/campaign_enemies.py::resolve_campaign` still chooses
P1 compatibility cohorts over the existing 72 campaign records and emits
`ENEMY_CAMPAIGN 1`. `apworld/pikmin_randomizer/options.py` exposes the existing
P1 campaign option. `engine/pc_port/pc_p2_preview.cpp::pc_p2_preview_setup` returns
unless experimental room mode is active. Family sidecars and fixture placements
are not generated by the ordinary seed/launcher path.

For actual P2 pool eligibility we still need:

1. **Canonical roster and capability records.** One row per concrete source ID,
   variant, required helper and resource alias, mapped to native implementation,
   assets, placement requirements and accepted gates. Separate enemy choices from
   plants, hazards, projectiles, manager bases and non-spawnable aliases. Include
   Bulbmin and special Bulborbs rather than treating Snow as the entire family.
2. **Versioned seed identity and native binding.** Persist P2 choice, variant,
   parameters, dependent actors and content hashes. Deterministically install
   placements/sidecars, preload resources, register late/scheduled births and
   preserve the choice across revisits. Reject unsupported identities and missing
   content; do not silently produce a P1 substitute or change legacy seeds.
3. **Encounter compatibility.** Audit footprint, water depth, flight space,
   burrow ground, home/nest location, projectile corridors, helper limits and
   corpse return routes. Bosses need encounter adapters. “All enemies available”
   means each has legal placements, not that every enemy fits every spawn slot.
4. **Rewards and logic.** Preserve required P1 checks/drops/farming and explicitly
   define P2 corpse, pellet, treasure and no-drop behavior. Keep ordinary Onion
   and AP behavior distinct from the experimental Pod/Poko ledger. Add new
   checks only intentionally. Verify source coverage, reachability and AP fills.
5. **Player installation and persistence.** Build/cache required P2 assets from
   local source data, verify region/content identity, stage them with generated
   sessions and report missing prerequisites. Reopening a seed must restore the
   same roster, rewards and actor dependencies without duplicate grants.

This bridge can be proven with a small admitted cohort before all families finish.
A complete P2 story campaign, every cave, or perfect Piklopedia UI is not required
just to add enemies to the P1 randomizer. Required species/captain/terrain mechanics
are required where a particular encounter depends on them.

## Family audit: mechanics still required

“Present” below refers to the audited draft; “candidate” refers to worker evidence.
No row is a blanket Family-complete acceptance.

| Family / identities | Delivered evidence | Still between it and pool eligibility |
|---|---|---|
| Bulborbs/dwarfs/Sheargrubs; special Bulborbs and Bulbmin (#120/#197/#131) | Snow and dwarf/grub visual/mechanics foundations present | Per-variant behavior/receiver/event mapping, natural death/carry/revisit; Spotty Bulbear revival, Fiery Bulblax fire/water rules, Bulbmin leader death/recruitment and cave-only ownership. Audit exact roster; these were underrepresented in the old table |
| Ground six (#165/#407) | Sokkuri/Armor present; ElecBug, TamagoMushi, Imomushi, Hana have source slices in candidate | Sokkuri water/press/death/re-entry; Armor weak-point and captain interaction (source-inapplicable bridge states need explicit N/A); paired ElecBug discharge/Denki; Mitite group birth/true Astonish; Whiskerpillar plant/tube eating; Hana underground protection/captain attack/poison. All need natural lifecycle/mixed-scene evidence |
| Flying, frogs, Honeywisp (#166/#167/#194–#196) | P1-counterpart display paths; candidate Mar wind event and Tadpole escape/leap | Mar full wind/stuck-Pikmin/fall behavior; Hanachirashi and Spectralids; frog source landing/crush/receivers; Honeywisp drop/nectar accounting; death/re-entry and family-specific transport or N/A |
| Aquatic (#167) | Batch3 display; Tadpole candidate | Catfish source behavior; Jigumo nest/PanHouse ownership; UmiMushi variants' parameters, targeting and weak points; water/collision/eat/flick/death/return routes. Ranging Bloyster captain-dependent targeting needs a defined captain capability |
| Cannons/Groink/projectiles (#169/#198/#406/#425/#427) | Candidate cannon/buried FSM and Stone/Rock/Egg seam; Groink isolated source policies | Real actor and animated muzzle integration, dynamic targets, collision-to-health mutation, explosions/drop births, simultaneous projectile ownership. Groink burst/target/revival/carcass recovery and pedestal variant; Man-at-Legs projectile dependency |
| Blowhogs/Dweevils/hazards (#170/#408) | Tank display; proxy damage application and Red-fire/Blue-water routing proven | Source Dweevil FSM and enemy-side receivers; gas/electricity and White/Yellow fidelity; carried objects, elemental emissions, BombOtakara payload; fixed hazard activation. Accepted InteractAttack is not itself applied source damage |
| Beetles/Breadbugs/Mamuta (#168/#219–#221) | Native slices; Mamuta bury/cap99/captain damage/death/corpse passes | Beetle drop limits and re-entry; Breadbug cargo contests/nest ownership/Giant scoring; Mamuta adversarial flick/territory. All need ordinary placement, reward and revisit acceptance |
| Bulblax/Baby (#172/#239/#256/#289) | Integrated Queen/Baby attack and King tongue/bomb/WarCry/death/reload fixture gates | Natural targeting/combat, untested King flick/trample, dynamic attachment/hitbox checks, ordinary rewards and boss placement; material/alpha/source-lighting visual comparison after upstream fixes; multi-actor budgets |
| Snagrets/Crawbster (#174) | Display/corpse-render foundations | Burrow/emerge, multi-bite/jump joints, White Flower Garden parameter variant; Crawbster roll/turn/flick and falling Rock/Egg; vulnerable windows, real damage, death/rewards/re-entry |
| Long Legs/Man-at-Legs (#173) | Display; reusable lifecycle foundation | Source leg movement/stomp/knock-off, hitboxes/vulnerabilities, Man-at-Legs gun/projectiles, natural death/cleanup/reload and CPU/actor budgets |
| Dirigibug/Antenna Beetle (#244/#245) | Hard-lane fixture/policy evidence; runtime seam missing from draft | Integrate first. Dirigibug visual/capture-joint and multi-carrier ownership; Antenna Beetle visual/audio actor, follow movement, source events and panic/claim lifecycle. Lane fixture passes do not mean a normal spawned actor is complete |
| Jellyfloats/Snitchbugs (#243/#215–#242) | Lane capture/receiver/drop work; Demon drop-state hooks present | Lesser Jellyfloat natural suction admission + flight FSM + moving suction joint, animation/death/release/late births. Greater: captain capture/two mouths/Drop. Snitchbug natural target/capture/escape/interruption/drop/teardown and animated mouth. Integrate owned candidates |
| Waterwraith/Titan (#175/#246) | Display; Titan candidate host/attack/trace/visual gates with 2/29 motions | Waterwraith/roller dependent lifetime, vulnerability and phase FSM; Titan remaining bank/Louie asset, source attack/receiver/weapon detach/phase behavior, real actor host and encounter performance. Candidate trace success is not complete enemy damage |
| Flora/Candypops (#171/#397/#429) | Pelplant 10/10 conversion + integrated proxy lifecycle; newer candidate proxy corpse gives 2 Pokos | Source Pelplant pellet capture/release and Onion seed behavior; Candypop conversion/refund/count conservation; plant lifecycle. Hikari static fallback needs integration and real billboard rendering. A Chappy corpse with a plant model is not source Pelplant completion |

## Shared runtime gates

- **Animation events:** batch2 currently parses the bank's event token without
  executing it. #431 offers a candidate contract, not migrated live actors.
  Each attack/death/drop must fire once under loops, pauses, frame skips and
  state changes; attachments need the same authoritative source frame.
- **Receivers/species/captains:** complete the specific poison/electricity,
  Purple/White, capture/held and captain ownership interactions an enemy uses
  (#113/#131/#130). Do not block harmless counterparts on unrelated mechanics,
  but do not fake missing mechanics with identity changes or invincibility.
- **Lifecycle/rewards:** natural kill, interrupted capture, dependent cleanup,
  late births, recycled addresses, stage/day/cave changes and save/reload; exactly
  one valid reward, no stale pointers, no borrowed control-actor state.
- **Performance:** capped per-species bank memory, collision/event work, helpers
  and projectiles; mixed roster at target density. Individual 30 FPS fixtures do
  not establish combined budgets. Existing renderer improvements help but are
  not full-roster evidence.
- **Current fixtures:** rebuild exact-head and regenerate arenas, default live
  Pikmin and centred 960x540 window. Record explicit interventions and distinguish
  source-backed N/A, untested and passed. See the mandatory fixture guide.

## Numbered parallel dispatch

Use [the 33 numbered lanes and copy/paste worker prompt](PIKMIN2_IMPLEMENTATION_FANOUT.md#numbered-parallel-lanes--deepseek-dispatch-435).
Lanes 01–12 own integration and shared/product systems, 13–32 own independent
family groups, and 33 owns independent seeded-run/mixed-scene QA. The guide defines
ownership, candidate reuse, dependencies, acceptance and capacity limits; this
blocker list remains the evidence baseline. Existing owners retain their lanes.

## Recommended next delivery sequence

1. **Reconcile candidates and roster first.** Integrate missing hard-lane wiring,
   newer species, lifecycle, cannon and converter/event candidates in reviewed
   slices. Produce a per-ID ledger from family contracts with draft commit,
   build registration, assets and accepted gates. Do not start duplicate work.
2. **Prove one end-to-end seeded cohort now.** Prefer self-contained P1-counterpart
   enemies with existing natural combat/carry evidence. Generate a real seed,
   stage assets automatically, exercise normal play/death/reward, revisit and
   restart, and verify AP checks. This exposes the bridge before more
   one-off fixtures accumulate. Admission is evidence-based, not “all tier 1.”
3. **Finish ordinary family behavior in parallel lanes.** Family owners close
   natural combat and lifecycle for the admitted cohort and then expand it.
   Shared owners deliver receiver/event/cargo primitives against actual consumers.
4. **Add dependent encounters.** Captors, paired beetles, nests, revival and
   projectile enemies follow their ownership and placement contracts; bosses
   become legal encounter types with explicit helper and terrain budgets.
5. **Close full-roster acceptance.** Every concrete enemy has at least one valid
   seeded encounter, required source mechanics, content/install support and
   natural lifecycle/reward evidence; representative mixed scenes and seed/logic
   sweeps pass. Keep scenery/helpers separately covered without counting them as
   independently randomizable enemies.

Suggested work ownership: integration/roster; seed-placement-install bridge;
family behavior lanes; shared receivers/events/ownership; independent mixed-scene
QA. This is a proposal for next implementation issues, not newly dispatched work.

## Evidence references

- [Pipeline levels](PIKMIN2_ENEMY_IMPORT_PIPELINE.md),
  [mandatory fixture baseline](PIKMIN2_IMPLEMENTATION_FANOUT.md),
  [#422 integration](PIKMIN2_INTEGRATION_422.md),
  [upstream #433](../UPSTREAM_SYNC.md),
  [existing randomizer pool constraints](../ENEMY_RANDOMIZER_ROADMAP.md).
- GitHub source/evidence: [family coordination #186](https://github.com/4laric/pikmin-randomizer/issues/186),
  [roster/difficulty map #197](https://github.com/4laric/pikmin-randomizer/issues/197),
  [species candidates #407](https://github.com/4laric/pikmin-randomizer/issues/407),
  [cannon #425](https://github.com/4laric/pikmin-randomizer/issues/425),
  [lifecycle/rewards #397](https://github.com/4laric/pikmin-randomizer/issues/397),
  [Jellyfloat #243](https://github.com/4laric/pikmin-randomizer/issues/243),
  [billboard #429](https://github.com/4laric/pikmin-randomizer/issues/429),
  [clock/events #431](https://github.com/4laric/pikmin-randomizer/issues/431).

No code changes, native builds or runtime tests were performed for this audit.
Earlier test totals certify their pinned snapshots, not every candidate above.
