# P2 enemies in Pikmin 1 Archipelago seeds

Specification, 2026-10-01. Tracking: [#1046](https://github.com/4laric/pikmin-randomizer/issues/1046).
Specification and resolved-check implementation owner: Codex, using the shared
`4laric` account. Existing import and gameplay owners retain their scopes below.

## Outcome and baseline

The resolved source/check catalog slice is implemented on `codex/p2-ap-integration`
with paired native branch `codex/p2-ap-catalog`. This is a review candidate;
the end-to-end campaign milestone below remains open. See the implementation
record at the end for exact validation and release dependencies.

Generate a normal `Pikmin Randomizer` AP slot with P2 enemies, launch its exported
manifest with the matching native/content package, and complete it through real
combat, deliveries and ordinary campaign saves. Imports arriving later should
need an admission record and content adapter, not another AP integration.

This extends the existing P1 world. A separate P2 world, cave campaign, item/part
relocation, and completion of every P2 import are outside this milestone.

The inspected remote root `main` is `0ae48903ad81374e3eed452b9e7dc3ca187dfddb`.
The local checkout is the older `kimi/p2-bulblax-import` lane at `fdd55812` with
unrelated work in progress. Current remote source and issue evidence take
precedence over its older README and family-status snapshots. No executable was
built or run for this specification.

Already present on the inspected main:

- `p2_enemy_randomizer`, `p2_enemy_pool` and placement options in the AP world;
  CLI/seed generation, `p2_layout`, manifest fingerprint and
  `p2-enemy-bridge-v1` capability support.
- An evidence-backed playable pool, content installers, native campaign actors,
  per-seed sampling, boss-arena placement and held-part integration work.
- AP exports the authoritative manifest in both slot data and `.pikmin.json`.
  Universal Tracker restores that manifest rather than regenerating choices.

Gaps verified in the inspected source:

- `catalog.active_names()` still selects fixed modern catalogs. Its reachability
  paths do not consume the final P2 bindings; P2 receipt identities are not yet a
  complete AP location catalog.
- AP pool descriptions still describe the early six-species cohort. Density,
  explicit species selection, proxy tier and Purple campaign do not have complete
  parity with the seed API. Placement help incorrectly says a document is required
  even though generation supplies the committed default.
- P1 randomization and P2 bindings are rejected in combination. Population farming
  logic still largely assumes vanilla Hope/Navel sources.

Do not use a species count in this document as admission authority. Imports and
admissions are moving; use the pinned playable/roster records when implementation
starts. An open issue can already contain landed work: reconcile its latest
commits and evidence before assigning a slice.

## End-to-end contract

The generation order is:

`options -> eligible species -> P1 layout -> P2 overrides/arenas/holders -> final
source inventory -> checks and requirements -> reward pool -> AP fill -> export`.

Resolve this once before fill. Save the actual choices, schedules, requirements,
check mapping and content requirements in the manifest. Runtime, tracker and
client consume that result; none samples the pool again. `unplaced` is diagnostic
information, not an encounter or an AP check.

### Identity and events

Keep four identities separate: P1 species, P2 source ID, proxy identity and native
host vehicle. A P2 actor riding a P1 Frog never awards the P1 Frog check. A
cosmetic proxy never masquerades as a source-behavior P2 identity.

Use one global bestiary check per eligible P2 species, named
`Bestiary: Deliver <species>` for a corpse delivery. Multiple area sources are
alternate ways to reach that same check. Assign its AP ID once in a dedicated,
audited namespace; never derive the ID from sample order, generator UID or the
current pool length. Reserve names/IDs for later imports without creating their
locations until they are present. Explicitly qualify names that collide with P1.

For a killable species without a deliverable corpse, use a separately declared
`Defeat` check only when its source-backed death event is supported. No synthetic
corpse or host-death shortcut. The #888 no-check identities 9/10/11/16 receive no
kill/carry check. Check policy and permission to spawn are separate decisions.

Maintain existing P1 bestiary IDs and event meanings. Keep their locations only
when the final layout retains a valid source. Pearl and defeat checks remain their
actual event types. A replacement does not inherit the displaced species' check.

Ship parts retain their existing UFO-based location IDs. A held part dropping is
not its check: ship absorption is. Killing or delivering the same holder may
independently satisfy its bestiary event. Preserve the current `emperor_bulblax`
25-repair appearance/death goal and Final Trial access unless the separate finale
replacement contract is explicitly implemented and accepted.

### Compatibility

Add a versioned resolved-enemy/check-catalog extension and a required capability
for its native mapping. Final field/token names are decided with #439/#905 after
reviewing their current adapters. Do not silently change the meaning of the
existing `p2-enemy-bridge-v1` protocol.

Old manifests, IDs, native journal order and sessions retain their old behavior.
New manifests carry an immutable ordered native-event-to-AP-location table,
covered by fingerprinting. Native and Python validate the same table. Do not
filter a compiled check array on one side and shift old indices on the other.
Unknown IDs, conflicting mappings, foreign content and unsupported capabilities
fail before gameplay with a specific error. No automatic old-seed conversion.

## Work packages

| Package | Scope and likely files | Coordination / dependency | Done when |
|---|---|---|---|
| A. Baseline and admissions | Reconcile playable table, roster, installers, constraints, receipts and native pin; record one release input inventory | #888, current import owners; #998 identity repair; upcoming #1042 larva and #1012 Man-at-Legs | Every selected identity has a runnable content/actor path and declared check policy; arrivals are added atomically without stale allowlists |
| B. Options and final layout | `apworld/pikmin_randomizer/options.py`, world `manifest()`, `randomizer/seed.py`, CLI, `experimental/pikmin2_seed_bridge.py`, `p2_placement*`, `p2_boss_arenas.py`, `p2_held_parts.py` | #439, #893, #899, #948/#951; coordinate shared seed files | AP/CLI agree, a bare opt-in seed works, P1 choices and P2 overrides yield one deterministic final source inventory |
| C. Bestiary and event bridge | `randomizer/catalog.py`, manifest validation, native randomizer/GoalItem/death/receipt seams, runner/session; reserve stable IDs | #905 primary; #901/#924 held parts; #441 receipt work | Only present species get checks, P1 credits work alongside P2, correct event credits exactly once, legacy indices remain intact |
| D. Reachability and pool balance | Catalog rules, per-source requirement data, AP region/rule construction and item pool | C; placement/route and species owners | Every active check and goal is reachable under the declared logic; no combat/carry/farming circular dependency or pool deficit |
| E. Launchable AP package | `scripts/build_apworld.py` and current packaging entry points, content staging, launcher/preflight, tracker/spoiler | #442/#643; A-C; native pin | Clean separate AP installation generates and launches the exact exported seed with required assets/capabilities, with useful failure messages |
| F. Integrated acceptance | Existing seed/AP/native suites plus fresh campaign and multiworld sessions | #444; B-E; applicable native fixes | The release matrix below passes on frozen pins; remaining gameplay limitations are reported by species, not hidden by exclusions |

### B: option and placement behavior

Keep P2 opt-in during this milestone. Refresh descriptions from the actual pool.
Expose species selection and existing density policies with shared validators;
avoid a second AP-only implementation. A normal user need not provide an evidence
document. Keep custom placement as an advanced override. Distinguish admitted
source behavior from proxy tiers in names, validation and spoilers. Expose Purple
campaign requirements when that foundation is available; do not infer Purple-only
combat from a species name (Giant Breadbug has an accepted non-Purple route).

For combined P1/P2 options, resolve P1 assignments first and apply P2 bindings by
stable UID. Define one replacement/suppression operation for groups and arena
mates, avoiding double birth or two owners for one generator. Rejection of a
combination needs a concrete collision reproduction, not a blanket design rule.
Introduce a layout version where this changes existing generation semantics.

Keep schedules, alias generators, survivor-count cache behavior and held-part
identity explicit. A group with reduced survivors must not change identity on
reload. Ordinary density and arena occupancy are separately resolved, then merged
into the source inventory. Incompatible explicit density requests explain the
actual shortage/constraint; default sampling records what could not be placed.

Placement constraints live in root data: footprint, clearance, water, flight,
helpers and actual routes. Boss arenas follow the owner-directed real-seed policy
in #899. Evidence slots are examples, never native whitelists. Native still checks
runtime compatibility and reports a specific `reason=`. Smoke/dev overrides stay
available, but a smoke rebind is not proof of the generated AP layout.

### C-D: source inventory, logic and rewards

Record surviving P1 sources and placed P2 sources after arena suppression and
holder replacement. Each source carries identity/event kind, UID/aliases, area,
earliest day/expiration/respawn, terrain/route requirements, loaded carry minimum,
and dependencies for combat/helpers. Preserve valid sources outside the P2 slot
catalog. Retain the catalog snapshot with the seed so later pool changes do not
invalidate an existing session.

For each source, reachability requires area access, spawn schedule assumptions,
an executable combat method, and a usable delivery route for delivery checks.
Accept any valid source for a species. Combat alternatives are OR branches
(including cargo/Onion damage, bombs or color-specific attacks); prerequisites
within a branch are AND conditions. Do not invent universal color requirements.
Document any retained conservative rule and its route evidence/open audit.

Carry logic uses the actual spawned corpse's loaded minimum, legal carrier slots,
field capacity and the applicable color carrying upgrades. The P2 retail value
and a P1 host pellet value may differ: describe the production value currently
used, then version it when native fixes it. A capacity-times-strength inequality
alone cannot prove a navigable return path. Defeat checks do not need corpse carry.

Recompute renewable population farming from the final sources, including scheduled
and protected sources, rather than assuming Hope/Navel remain farmable. Cover
starting colors, Flarlic, maturity/stat progression and food/cargo interactions.
Do not depend on optional filler deliveries to repair an unreachable progression
graph. Breadbug theft must not permanently consume a required bestiary/part reward.

AP regions need manifest-aware location areas: a global species check with several
sources can live in a dedicated bestiary region and use an OR of source access
rules. Tracker source/day displays must use the same data. Never reveal reward
placements in the ordinary tracker.

Build rewards after choosing the active checks. Preserve the current 30-repair
pool/25-required behavior and required unlock/upgrades, filling remaining slots
with the existing benefits. Check that the reduced catalog can hold progression;
if not, report the deficit and fix the configuration/pool design through its owner.
Do not quietly omit progression, resurrect absent-species checks or change the goal.

### E: assets and persistence

Stage every required content dependency, including helper/projectile/arena/holder
resources, from legal local inputs into private `output/`. The AP package includes
the bundled bridge/core code and catalogs, not source disc assets. Preflight the
native pin, capabilities, content version/hashes and generator hashes before
releasing gameplay. A generic installed-P2-assets boolean is insufficient.

Map current `onion:p2:<id>:<stage>` receipts through the manifest catalog, retaining
source provenance and the existing authenticated session envelope. Resolve a
global species check idempotently across areas, respawns, reconnects and AP receipt
replay. Avoid aliasing a P2 corpse into a P1 host check. Verify the suspected P1
delivery suppression in #905, rather than assuming it has already been repaired.

Exercise day-end save/reload, dropped-but-undelivered corpses/parts, living holders,
already-collected parts, rollback and repeat visits. Preserve the existing campaign
checkpoint semantics; full mid-day suspend is a separate feature. A P2 death must
not also emit an unintended goal, part, host bestiary credit or duplicate reward.

## Acceptance and release sequence

Start B/C/D now against small resolved layouts and the existing admitted imports.
Develop E in parallel through its existing owner. Native fixes/imports supply
versioned inputs; they do not block designing AP location identity or logic.
F begins when the selected cohort and matching native/content pin are ready.

1. **Contract milestone:** pure seed/catalog tests prove mixed sources, sampled-out
   species, groups, arenas, held parts, event provenance and compatibility. Packed
   AP code uses these same validators, not stale copied modules.
2. **Playable slice:** a real AP generation with an ordinary P2 enemy, surviving P1
   enemy and accepted P2 boss exercises natural combat, actual delivery, unchanged
   held-part checks, reconnect and saved-day resume. Use the real generated bindings.
3. **Cohort release:** run the full admitted selected cohort across compatible
   sources and AP configurations; accept later imports with focused species runs
   plus the affected matrix. Do not wait for the entire P2 roster.

Required automated matrix:

- P2 disabled and historical manifests retain identity/check/goal behavior.
- Fixed and randomized starts across supported areas/colors; low and high Flarlic;
  stat, permanent-check and collection options; both goal modes.
- Pools smaller/equal/larger than available slots; default sampling; each exposed
  density; ordinary/group/arena/holder placements; mixed P1/P2 options.
- Stable AP IDs and native ordered mapping across sampling orders, future imports,
  malformed input and catalog tampering. Unplaced species get no locations.
- AP solo fills and multiworld cases with remote area, Onion, capacity, carry and
  supported combat dependencies. Sphere analysis reaches every active check and
  preserves the 25-repair finale dependency. One remote item must genuinely unlock
  a placed P2 check; generation success alone is insufficient.
- Separate generated AP export, slot data, client and Universal Tracker use the
  same fingerprint/catalog. Unknown receipts fail safely; duplicate/replayed
  receipts do not grant twice. Mismatched executable/content fails before play.

Required runtime evidence:

- Correct identity and spawn, movement/animation, attacks/receivers, death/corpse,
  actual transport/reward, cleanup/re-entry for the selected species; use
  source-backed N/A where appropriate. Test P1 and P2 receipts in the same seed.
- A real boss-arena replacement and a part-holder drop-to-ship-check path where
  those mechanisms are included. No displaced P1 actor or missing part/goal.
- Day-end/restart and AP disconnect/reconnect retain earned checks and living
  identities. Include mixed-scene frame-time/memory measurements against the
  integration-approved budget; do not scale density from isolated birth tests.
- Record natural versus injected/power-mode observations explicitly. Existing
  owner-approved power-mode admission does not prove normal low-capacity AP logic.
- Adopt current 20-Pikmin overlay and 960x540 centered fixture startup, captain
  guard and bounded runtime runners under the fan-out guide. Those fixture defaults
  do not override ordinary AP starting population/capacity rules.

Solo AP acceptance need not wait for netplay. If the release includes co-op, add
two-peer placement/content/check mapping, targeting, death/drop and replay tests;
the large Titan sidecar transport fix [#997](https://github.com/4laric/pikmin-randomizer/issues/997)
is then a dependency. Do not narrow the solo pool to satisfy a netplay packet limit.

Each handoff records issue/owner, exact root/native commits and dirty state,
content hashes, private worktree/build directory, executable SHA-256, no-work
Ninja dry run, generated manifest fingerprint, AP package version/hash, commands,
logs and PASS/FAIL/BLOCKED/UNTESTED gates. Build leases and the aggregate budget use
the shared `output/workflow/` registry; the integration lead alone performs the
maintained native build/export. Keep existing player sessions and parallel
checkouts intact.

## Immediate next work

Have #439 and #905 agree the resolved catalog/event table and stable ID reservation
first; implement source discovery, P1 suppression repair and dynamic AP locations
as the first bounded slice. Its acceptance seed must include a surviving P1 check,
a placed P2 delivery and a sampled-out P2 species, with no dangling location.
Then add kill/carry/farming rules, option parity, combined layout resolution and
packaged multiworld validation. Existing import owners continue native behavior
fixes and admissions; their next handoffs include the check/logic/content metadata
needed by this pipeline.

## Resolved-check implementation record, 2026-10-01

The first slice resolves persistent P1 generator sources after P2 replacement,
held-part seating, arena aliases and arena suppression. Only actually placed
P2 identities and surviving P1 suppliers create bestiary locations. Sampled-out
identities and model proxies create no P2 behavior check. P1 part/finale IDs stay
fixed. P2 AP IDs reserve `LOCATION_BASE + 0x600 + retail_source_id` independently
of placement order. The example `ap1046` has 89 locations: 40 P2 delivery checks,
six surviving P1 bestiary checks and the other 43 modern checks.

`enemy_catalog` stores final source UIDs, species, stages, first days, check IDs,
events, production corpse carrying minima and legacy native indices. It requires
`resolved-enemy-checks-v1`; `ENEMY_CHECKS 1` transmits the exact journal mapping
and authorized P2 source/stage pairs. The native adapter persists AP events before
the secondary corpse receipt ledger, rejects foreign source pairs and permits
surviving P1 deliveries. Legacy manifests omit the extension and retain their
existing indices. Existing internal `generate()` callers retain that behavior;
new AP/CLI P2 seeds request the extension explicitly. Session recovery checks the
recorded mapping, including Purple and proxy suffixes.

AP package candidate 0.33.0 includes the module and static reserved ID map. AP
density and numeric source-selection options use the existing seed validators.
The tracker and CLI status consume the saved source/check catalog. Imports with
no production corpse metadata fail generation with a specific error; fixture
carrying overrides do not count as production metadata.

Validation: 81 targeted tests and eight subtests pass, including native IPC
deliveries, duplicate/restart handling, crash-before-runner recovery, source/stage
rejection, capability refusal and legacy regression. The packaged archive loads
outside the repository, fills default/full, sampled, bounded, explicit-species,
low-capacity and progressive/permanent variants, and fills a two-player world
with remote items. Exported manifests roundtrip without regeneration. CLI
generation and status display all 40 placed P2 delivery checks.

Native source pin `e0da46e795969a9690fc01dc8f77cc585d718294`, clean, builds in
`output/native-p2-ap-integration-build` with Ninja/MinGW Release/IPO/JAudio.
`nectar.exe` SHA-256:
`7407493b3399222fae28e85dcb213c6b5246bad8c3519ca5ffa811318129cf2d`.
The `pikmin_pc` Ninja dry run reports `ninja: no work to do.` The engine-free
protocol probe also builds and reports no work on its dry run. Build/probe/test
records remain local under `output/p2-ap-spec/` in the canonical workspace.

Release gates remain open:

- Shared semantics/ID and delivery review under #186, #439 and #905; integration
  lead merges the paired native change, builds and exports the maintained line.
  This lane does not export `engine/` or update the shared AP installation.
- Per-source combat/color/carry-route acceptance and renewable population farming
  from final sources (#951). This slice retains conservative all-three-color and
  weakest-color carrying rules, and does not claim low-capacity combat proof.
  Population and ship-part logic retain the existing rules; a successful fill
  does not certify physical routes or farming after replacement.
- Catalog validation currently rederives against the pinned accepted placement
  and production metadata. Noncanonical custom targets are rejected. Historical
  snapshot migration and a version change are required if route/corpse policy
  changes; later imports must not silently rewrite an existing seed's checks.
- Combined P1/P2 enemy layouts, remaining proxy/Purple option parity, unsupported
  death-only P2 events and complete content/native version preflight are later
  slices. Existing incompatible combinations remain explicit generation errors.
- Fresh guarded native campaign delivery, day-end save/relaunch and full Emperor
  completion acceptance after incoming imports/fixes. No graphical runtime was
  launched for this slice; all six gameplay gates remain UNTESTED. The protocol
  probe uses no engine/window/Pikmin, so fixture adoption is N/A for this evidence.
  Any later gameplay acceptance must adopt the current 20-Pikmin overlay,
  centered 960×540 startup and captain guard in a fresh private arena.
