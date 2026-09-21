# P2 implementation fan-out and mandatory fixture baseline

Next-wave dispatch: [playable encounters and first cohort](PIKMIN2_NEXT_WAVE.md). Keep existing lane numbers; use this guide for current priorities and acceptance.

Asset lookup: [verified local P1/P2 inputs and staging commands](PIKMIN2_NEXT_WAVE.md#local-p1p2-assets-verified-paths-for-every-lane). Private worktrees do not inherit the main checkout's ignored asset directories.

Agent entrypoint, 2026-09-13. Documentation tracking: #404. Coordination and
shared-semantics review: #186. Implementation owner: Codex through shared GitHub
account `4laric`; assignment alone does not identify a lane or activate work.

Execution update, 2026-09-15: use [the workflow operating contract](PIKMIN2_WORKFLOW.md)
for durable lane records, watchdog actions, resource leases, handoff validation
and integration metrics. Its current policy supersedes historical reservations.

Read this before claiming or resuming a P2 implementation slice. Follow
[AGENTS.md](../AGENTS.md), [the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md),
[blockers](PIKMIN2_FULL_IMPL_BLOCKERS.md), and
[family status](PIKMIN2_FAMILY_STATUS.md), plus [family issue coordination](https://github.com/4laric/pikmin-randomizer/issues/186). This guide defines dispatch and fixture
requirements; it does not reassign existing owners or authorize duplicate work.

## Mandatory first action: adopt the current test fixture

### Verify local source availability before declaring assets missing

On this host, consult the canonical workspace's
`output/workflow/asset-inputs.json` before reporting missing legal/source assets.
The inventory records the local P2 disc, all 2,768 disc members with offsets and
sizes, hash-verified Forest/Yakushima cave data and Demon model/animation bytes,
and the existing P1 runtime asset directory. Recheck the actual paths and relevant
bytes using `experimental.pikmin2_assets.disc_files`; stale inventory metadata is
not proof of absence or availability. The disc is currently at
`C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`; runtime assets are at
`C:/Users/alari/AppData/Roaming/PikminRandomizer/game-data/assets`.

Distinguish missing raw source bytes from unfinished extraction, decompression,
conversion, geometry decoding, staging, source integration and runtime support.
Those engineering gaps need concrete owned work, not a request for the user to
provide assets already present. Record exact missing members, searched roots and
failed reads before claiming an external asset dependency. Use private output for
derived data and preserve the source disc and shared asset installation. Raw
asset presence never establishes runtime readiness or clears gameplay gates.

Every new AND already-running lane must refresh its fixture baseline before its
next runtime acceptance run. Old generated arenas and old executables do not
acquire these changes automatically. Report adoption in the lane's child issue.

| Component | Required behavior | Known introducing revision |
|---|---|---|
| Root `scripts/preview_pikmin2_room.py` | `overlay()` calls `ensure_pikmin_squad()` for the supported `dataDir/stages/chal0/default.gen` override, adding 20 red Pikmin when no Pikmin record exists | Root `a51b301` |
| Native `pc_port/pc_main.cpp` | Experimental-room startup defaults to a 960×540 window and calls `pc_window_center()` after loading persisted settings | Native `1d5a242b`; root source export `541bfba` |

These are minimum capability markers, not a request to reset to old commits.
Both markers must be verified: #419 imports the overlay and #422 integrates
the native window default into production and the replacement-main room fixture.
Older executables still require a rebuild.
Use the newest integration-approved source containing both changes and all
current lane dependencies. Record exact root/native commits and dirty state.
Check your own worktree, not just the maintained checkout. Preserve ongoing work
when merging/rebasing; equivalent cherry-picked changes require source evidence
because ancestry alone will not identify them.

1. Refresh the root overlay script and the lane's native source. Inspect inherited
   scripts for original absolute paths before executing them.
2. Regenerate the arena into a NEW private `output/` directory with the current
   family arena runner using the current `preview_pikmin2_room.overlay()`.
   Existing Pikmin generators are preserved; the helper does not top up an
   existing squad. Unsupported/custom stage formats or runners bypassing this
   overlay need an explicit equivalent starting squad and their own evidence.
3. Confirm the generated stage has live starting Pikmin in valid positions.
   The default added squad is 20 reds. This prevents immediate zero-Pikmin
   extinction at startup; it does not disable extinction during gameplay.
   Check terrain/placement for the lane's arena and document any override.
4. Build the lane's current native source in its private build directory. Set
   `$env:PIKMIN_P2_ROOM_WINDOW='960x540'` for the standard acceptance launch and
   use the experimental-room entrypoint. Do not inherit `off` or `0`, fullscreen
   settings, or a stale executable. Other dimensions are for explicitly recorded
   observation needs, not the standard default.
5. Observe a 960×540 centred window, a live squad, and entry into active gameplay
   without the immediate extinction screen. Standard startup logs should include
   `Experimental preview window set to 960x540 windowed and centered`.
   Capture the log and window/squad evidence in the private run directory.

**Custom C++ fixtures need special attention:** the fixture builder replaces the
production main object. A fixture with its own startup is not guaranteed to run
`pc_main.cpp` window setup. Its owner must verify equivalent window sizing and
centring in that entrypoint and record observed evidence. An environment variable
alone cannot add the behavior to an old or custom executable.

**Guarded cave boots must use wall-clock supervision (#671).** Run the canonical
`scripts/run_pikmin2_cave_fixture.py --exe <private-exe> --source-run <old-run>
--run-dir <new-private-run> --timeout 60` instead of launching an unbounded raw
fixture or relying on its frame counter. The runner preserves input files,
creates a separate overlay with readable files and valid directory junctions,
streams `native.log`, kills its own child on timeout, and writes `run-result.json`.
Keep `run-inputs.json` with the executable and input hashes. Never construct a
directory junction to an ordinary file: this made `consFont.bti` unreadable and
crashed real startup in `Font::setTexture` despite green guard self-tests.

The historical Yakushima arena also disagreed with its 20-survivor checkpoint.
Regenerate the lane arena using the current squad baseline before acceptance;
do not weaken the checkpoint count check. `--baseline-assets <legal-P1-assets>`
explicitly regenerates the standard 20-Pikmin arena for a **boot smoke test only**.
It replaces lane placement and cannot establish cave geometry, collision or
gameplay acceptance. The same bounded runner with
`P2_CAVE_GUARDED_BOOT_FORCE_CAPTAIN_DOWN=1` must produce raw exit 86 and
`P2_FIXTURE_CAPTAIN_DOWN` with no boot PASS. Window creation and engine-independent
guard tests alone do not establish a working boot.

**Other native fixtures also require a bounded runtime launch (#701/#702).**
Use `py -3.12 scripts/run_pikmin2_fixture.py --exe <private-exe> --run-dir
<fresh-staged-private-arena> --arg=--experimental-pikmin2-room --pass-marker
"<fixture-specific PASS marker>" --timeout 60` from the canonical checkout.
Use the fixture's actual arguments (for example `--arg=--experimental-challenge-level
--arg=1`). The runner validates readable boot assets/runtime DLLs, preserves cwd,
records hashes and kills only its own fixture child on timeout. Stage the correct
arena before launching; an empty directory is not a runtime input package.
Do not use a build supervisor for runtime: `leased_run.py` sets cwd to the source
worktree, discarding the selected arena. Runtime needs no build lease. A window
stuck in `System::Initialise`/`pumpAudio` is not gameplay progress; preserve its
failure logs and correct inputs before a fresh attempt.

If a window is already stuck at extinction, retire that run, regenerate its arena
and relaunch the updated executable. Do not use an extinction-screen screenshot
as gameplay evidence or alter production extinction semantics to bypass it.
Keep independent QA bundles immutable; create a new version and hand it off.

Required adoption comment (fill every field; do not claim PASS from source alone):

```text
Fixture baseline adoption
Child issue / lane / implementation owner:
Root commit + dirty state / overlay source:
Native commit + dirty state / worktree / private build directory:
Squad change present / window change present (ancestry or source evidence):
Fresh arena command / run directory / asset and config hashes:
Executable SHA-256 / fixture provenance status if applicable:
Window setting / observed size and centring evidence:
Live starting Pikmin / active gameplay / no immediate extinction evidence:
PASS, FAIL, or BLOCKED; remaining work:
```

The coordinator maintains an adoption checklist for ALL active lanes in #186.
An existing lane's next handoff is incomplete without this record. A document
link or commit acknowledgement is not runtime adoption evidence.

## Numbered parallel lanes — DeepSeek dispatch (#435)

This section supersedes the old six-lane dispatch table. **33 useful ownership
lanes** are available, not 33 mandatory new sessions. Assign one session per lane;
retain an existing owner who is already delivering that scope. The ledger in #186
must identify the actual session/worker, child issue, files and status. Assignment
to the shared GitHub account does not identify the worker. Follow AGENTS.md
for the repository implementation-owner field (Codex through shared `4laric`);
record the actual executing agent and DeepSeek session separately so that this
shared ownership field never implies which model did the work. Do not invent a
separate GitHub identity.

Baseline: use the latest approved root/native pair from lane 01. Initial known
review snapshot is root `06cae25` on `codex/p2-main-review`, native `9735870c`;
draft #432 includes upstream `511f22fe`. Do not reset existing worker branches to
this baseline or discard newer work. Missing candidates are enumerated in
[the blocker audit](PIKMIN2_FULL_IMPL_BLOCKERS.md). Lane 01 publishes subsequent
approved pairs; other lanes pin them and merge updates at acceptance boundaries.

**All GitHub mutations must explicitly target `4laric/pikmin-randomizer`.**
Never infer the target from the current directory: native's upstream is a different
repository. Use `gh ... --repo 4laric/pikmin-randomizer` for issues/PRs/comments;
use explicit repository paths for API mutations. Read/fetch upstream when needed,
but do not create upstream issues, comments or PRs without a separate user request.
For Git pushes, verify the remote URL and explicit root branch first. Never push
native origin or upstream. Workers do not merge main or draft #432 themselves.

### Shared and product lanes

Dependencies below gate integrated acceptance, not the start of useful work.
A consumer can audit, implement against an agreed interface and test privately
while its provider finishes. A fake adapter is not end-to-end acceptance.
File prefixes are ownership suggestions; inspect actual existing modules first.

| Lane | Scope / first concrete deliverable | Owns and excludes | Dependencies / completion gate |
|---|---|---|---|
| **01 — Integration and candidate reconciliation** | Reconcile missing hard-lane export `87204df`, species `86aa159`, cannon `656c556`, later lifecycle and converter/event candidates in small reviewed batches | Maintained root/native pair, shared build/export, merge queue and cross-lane hook reconciliation; does not reimplement family AI | Start now. Review current source, not old whole-engine snapshots; preserve upstream/specular/session fixes; each batch builds, exports with parity and repeats affected gates. Publish exact integrated commits and notify consumers |
| **02 — Canonical enemy roster and eligibility** | Per-source-ID ledger covering variants, aliases, helpers, assets, runtime module, owner, legal encounters and six-gate evidence | New roster/schema module and audit tooling; family owners supply source facts; does not claim gameplay PASS | Start now, consult #197 and every parent checklist. Every concrete identity accounted for; helpers/nonspawnable aliases explicit; eligibility defaults denied until evidence. Agree schema with 03/04/05 before coding consumers |
| **03 — Seed selection and native manifest bridge** | Opt-in versioned P2 seed choices and deterministic native actor bindings for a small admitted cohort | New seed/native protocol adapter and focused seed/CLI/AP glue; 02 owns roster, 04 owns constraints, 05 owns asset staging | Design now; acceptance needs 02/04/05 and one eligible family. Same seed/revisit/restart gives same identity; malformed/unknown content rejected; old seeds unchanged. This lane is the primary owner of shared seed/options/protocol edits |
| **04 — Placement and encounter compatibility** | Machine-readable legal slots/encounters: terrain, space, water, routes, homes, helper counts, schedule and protected drops | Placement constraints/audit tools and encounter descriptors; no seed serialization or family FSM edits | Start with existing P1 slots and candidate cohort. Inputs to 02/03; accepted placements have native XYZ/terrain/route evidence. Bosses use encounter descriptors rather than universal replacement permission |
| **05 — P2 content installation and packaging** | Local-source extraction/cache/content identity -> automatically staged family assets and sidecars for one generated seed | Installer/cache orchestration and launcher/package glue; family extractors remain family-owned, generic converter belongs to 09 | Contract with 02/03 now. Acceptance: fresh install, cached replay, missing/wrong source and interrupted staging; no retail assets committed/distributed; generated session launches without manual sidecar copying |
| **06 — Rewards, cargo and save receipts** | Define and prove per-enemy death/corpse/pellet/treasure semantics and exactly-once receipts across restart | Shared reward/cargo/receipt interfaces, persistence patches and tests; family-specific drops stay with families; 03 owns bootstrap protocol | Start by reconciling later #397 reward candidates with 01/07. Ordinary Onion/AP vs experimental Pod behavior explicit; no duplicated rewards, lost required checks or invented new checks. Coordinate native save mutations with 01 |
| **07 — Lifecycle, registrations and fixture infrastructure** | Reusable natural-death/forget/recycled-address/re-entry/late-birth harness and ownership hooks | Shared registration/lifetime utilities, fixture builder/overlay and lifecycle harness; families implement their cleanup, 06 owns reward meaning | Reuse #397 candidates. Demonstrate stale reference rejection, control actor unaffected and repeatable teardown; distinguish manager reset from full scene/day/restart. Own shared fixture changes, not all family runtime runs |
| **08 — Animation clocks and gameplay events** | Review/adopt #431 contract in one real consumer, then publish tested migration pattern | Shared sampled clock/event reader/player and contract tests; families map states/events; no generic material or species FSM ownership | Start from `cb253f5`, not a rewrite. Exactly-once events through loops, pauses, skipped frames, interruptions and generation change; displayed pose cannot substitute for event execution. Coordinate each consumer migration |
| **09 — Conversion, material and renderer fidelity** | Integrate #429 bounded fallback and validate upstream specular changes on actual P2 materials; identify remaining real-bank failures | Shared converter, billboard/render/material infrastructure; per-family resource selection stays with families; clock belongs to 08 | Reuse landed Pelplant/BTK/BRK/skinning work. Strict defaults preserved, repeat hashes, source-backed visual comparisons. Static billboard is labeled approximation; camera-facing support is separate acceptance. One renderer owner avoids competing shader edits |
| **10 — Damage, elemental and attack receivers** | Shared damage/immunity/attack-volume contract with actual health changes and lethal paths | Generic receiver routing/attack adapters; species capability definitions from 11; families own vulnerability/state rules | Start from #408. Cover fire/water/gas/electricity, valid/immune targets and queued damage; pair with an actual family. Do not bypass updates or make actors invincible to hold fixtures still |
| **11 — Pikmin species and Bulbmin capability** | Complete enemy-facing Purple/White/Red/Yellow/Blue behavior plus Bulbmin recruitment/lifetime contract | `pc_p2_species`, Purple/White/Bulbmin modules and species storage/abilities; no generic receiver or captain-controller ownership | Preserve active #113/#131/#393/#395 work. Coordinate 06/10/12. First prove needed poison/electric/Purple interactions; Bulbmin includes leader/dependent ownership and cave-only recruitment. Ordinary harmless enemies need not wait for all five-species fidelity |
| **12 — Captains and squad ownership** | Stable captain/captive/squad interface needed by Snitchbugs, Greater Jellyfloat and Ranging Bloyster | Captain switching/health/held/capture bridge and squad ownership; captor FSMs remain in families | #130; coordinate 07/11/29/30. Two-captain requirements explicit; switching, capture interruption, death and reload do not lose/duplicate held actors or squads |

### Family lanes

Each family lane owns source audit, family assets/configs, FSM, family event and
receiver adapters, natural arena run and per-ID ledger evidence. Own its existing
family-prefixed modules, tests and docs; do not edit another family's module.
Routine additive hooks are implemented privately and submitted as focused commits
for 01. Shared receiver/event/lifetime/renderer semantics go to lanes 06–12.

| Lane | Family / existing issues | First bounded slice and candidate reuse | Acceptance and dependencies |
|---|---|---|---|
| **13 — Bulborbs, dwarfs and Sheargrubs** | #120/#197; existing Snow/Kochappy/Uji paths | Audit source IDs/variant differences and close one natural combat/death/carry/revisit chain; then special Bulbear/Fiery Bulblax rules | 08/10/06/07. Report revival and elemental variants separately; Bulbmin is 11. Do not declare the whole family complete from Snow |
| **14 — Ground invertebrates** | #165/#407; Sokkuri, Armor, ElecBug, TamagoMushi, Imomushi, Hana | Reuse six-species candidate native `737af8c6` and root `86aa159`; finish missing natural receiver/death/re-entry gates | Own the shared ground family resources. Pair discharge, Mitite group births, plant eating and Hana protection remain explicit. 10/07/08; plant interface with 23 |
| **15 — Flying counterparts and ambient fliers** | #166/#194–#196 as applicable; Mar/Hanachirashi/ShijimiChou/Qurione | Reuse Mar candidate and Honeywisp path; complete real wind/nectar lifecycle before expanding variants | 08/10/06/07. Own flying resource/FSM group; excludes Snitchbugs, Dirigibug, Antenna Beetle and Jellyfloat (27–30) |
| **16 — Frogs and aquatic enemies** | #167/#194/#201; Frog/MaroFrog/Tadpole/Catfish/Jigumo/UmiMushi | Reuse Tadpole candidate; finish harmless escape/death/re-entry or a counterpart combat chain; then nest and Bloyster variants | 04 water/ground contracts, 06–08/10; captain-dependent Ranging Bloyster needs 12. Explicitly owns Frog/MaroFrog despite historical cross-family issue grouping |
| **17 — Reward beetles** | #168/#219; Kogane/Wealthy/Fart | Reuse native Kogane work; natural hit/drop limits, variant rewards and reload | 06/07/08/10. Own beetle modules, not Breadbug/Mamuta. Preserve aliases and finite reward counts |
| **18 — Breadbugs and nests** | #168/#220; PanModoki/OoPanModoki | Reuse actor/cargo work; close contested cargo, nest ownership and Giant scoring | 04/06/07. Prove interruption/death/revisit releases cargo and rewards once; reserve shared cargo modifications with 06 |
| **19 — Mamuta** | #168/#221 | Reuse integrated bury/cap99/death/corpse evidence; close natural territory/flick/transport and revisit | 06/07/10. Do not repeat only forced death; retain source-backed harmless/attack distinctions |
| **20 — Cannon larvae and shared projectile primitives** | #169/#406/#410–#413/#424/#425/#427 | Reuse `656c556` / native `104d6dfa`; connect actual cannon actor + moving muzzle -> Stone -> real receiver | Own Kabuto variants and reusable Stone/Rock/Egg/Bomb primitives/contracts. 08/10/07; 21/25/26/27 consume rather than fork these primitives. Egg drop commands must become real births |
| **21 — Gatling Groink** | #198/#204–#210 | Resume existing owner/candidate; complete targeting/burst/animated muzzle and shell health effects, then revival | 20 primitives, 08/10/06/07. Own Groink-specific shell/host/controller, preserve parked work until owner claim resolved; pedestal variant and carcass recovery explicit |
| **22 — Blowhogs, Dweevils and fixed hazards** | #170/#408; Tank/Wtank/Otakara family/Hiba variants | Reuse Tank and receiver diagnosis; one complete elemental enemy, then shared variants | 10/11 for immunities, 06/07/08; BombOtakara consumes 20 blast contract. Titan is 32, flying blowhogs are 15. Keep object theft/drop ownership source-correct |
| **23 — Flora and Candypops** | #171/#397/#429 | Reuse Pelplant conversion/proxy lifecycle, then implement source pellet capture/release and actual seed/reward path | 06/07/09/11; coordinate Whiskerpillar plant interface with 14. Candypop refund/count conservation; Hikari camera-facing fidelity; never count proxy Chappy corpse as source Pelplant |
| **24 — Bulblax and larvae** | #172/#239/#256/#289 | Reuse integrated Queen/Baby/King gates; natural combat/attachments/rewards and remaining King flick/trample | 06–10 and 04 boss placement. Renderer edits owned by 09; family owns material bindings/reference captures. No repeat work on already-passed injected WarCry/death gates without changed inputs |
| **25 — Snagrets and Crawbster** | #174 | Source burrow/emerge/bite/jump and vulnerable/death lifecycle; then Crawbster roll/fall hazards | 08/10/07; 20 owns Rock/Egg primitives, 04 owns encounter geometry. Family owns spawner decisions and animated joints |
| **26 — Long Legs and Man-at-Legs** | #173/#312 | Source legs/stomp/weak points and natural death/re-entry on existing display path | 07/08/10/04; Man-at-Legs consumes 20 projectile contracts. Own leg rig/attack scheduling; bound collision and helper budgets |
| **27 — Careening Dirigibug** | #244 | Recover hard-lane modules through 01; connect ordinary carrier actor, capture joint, bomb lifecycle and interruption | 08/10/07/20. New seam must be runtime-tested; older fixture without it is insufficient. Multi-carrier ownership and dead-carrier attribution |
| **28 — Antenna Beetle** | #245 | Recover hard-lane binding/FSM through 01; add real visual/audio actor and follow movement to proven claim/reclaim policies | 08/09/11/12/07 as applicable. Natural claim, panic/death release, whistle reclaim and scene lifecycle; no policy-only locomotion claim |
| **29 — Jellyfloats** | #243 | Resume lane fixture; Lesser natural flight + Attack suction admission + moving joint before Greater | 07/08/10, 12 for Greater captain capture. Digestion, interruption, release/death, late births; separate each variant's eligibility |
| **30 — Snitchbugs and Demon** | #215–#242 | Consolidate existing capture/drop/attachment candidates into an ordinary spawned captor | 07/08/10/12. Correct target, admitted attachment, escape, interruption, grounded release and teardown; captain drop-state hook alone is not completion |
| **31 — Waterwraith and rollers** | #175 | One source-correct BlackMan/Tyre owned encounter: phases/vulnerability/roller attacks and cleanup | 04/07/08/10/11. Roller ownership and Purple vulnerability are required; do not work in Titan modules |
| **32 — Titan Dweevil** | #246 | Recover host/weapon/trace/visual candidate through 01; complete real weapon damage and one natural phase transition | 07–11/20 as applicable, 04 boss budgets. 2/29 motion staging and missing Louie resource remain explicit; no full-boss claim from isolated trace tests |

### Independent acceptance lane

| Lane | Deliverable | Boundary and dependency |
|---|---|---|
| **33 — Mixed-scene and seeded-run QA** | Reproduce the first admitted cohort through generate -> install -> natural fight -> reward -> revisit -> restart; then adversarial density/ownership scenes | Start now by defining matrix and reproducing approved baseline; consume immutable builds from 01 and family evidence. Own QA tools/reports, not simultaneous production fixes. Test weak/strong stats, minimum cap, paused events, scheduled births, interrupted capture, address reuse, missing assets and frame/memory budgets. File concrete failures with exact IDs/commits; do not report a mocked scene as a real seed |

### How wide to launch

All lanes can begin discovery/contracts/private unit work now, after checking
existing claims. Do not force every session to wait for lane 01 to finish every
candidate. Lane 01 first pins the contracts and reconciles the candidates needed
by immediate consumers. Family owners can continue on their newer branch and
supply an ordered native series without wholesale exported-tree replacement.

If you have fewer sessions, staff **01–10, 13, 14 and 33** first, filling already
active owners rather than replacing them. Then staff the remaining family lanes
and species/captain providers according to their consumers. An existing active
boss/captor owner should continue; this priority is not a stop instruction.
With enough sessions, all 33 ownership lanes are useful. Do not subdivide a shared
family FSM/resource group further unless the owner can name disjoint modules and
an agreed interface; more sessions editing the same hooks is not more throughput.

Code review, source audits, conversion and unit tests can proceed concurrently.
Each worker uses its own root/native worktrees and private output. CPU/RAM capacity
limits simultaneous heavy builds: `-j 6` is a per-build example, not permission
for 33 simultaneous six-job builds. Reserve build capacity before launching and
reduce concurrency when memory/link pressure requires it. One real-GL/input
acceptance run at a time on this host; reserve a short named slot in #186 and
release it immediately. Do useful independent work while waiting for a slot.
Only 01 owns maintained build/export and merge into the integration branch.

### Shared-file collision rules

- 02 owns roster schema; 03 owns seed/options/native protocol; 04 owns placement
  schema; 05 owns installer/package integration. Agree a minimal contract before
  consumers fork incompatible representations. Coordinate overlaps, not whole lanes.
- 06 owns reward/save semantics; 07 owns lifecycle/fixture infrastructure; 08 owns
  clock/event semantics; 09 owns converter/GL; 10 owns generic receivers; 11 owns
  Pikmin capabilities; 12 owns captain/squad semantics.
- Family-specific adapters and bindings stay with family owners. Shared files
  such as `teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`, `tekimgr.cpp`,
  `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp` and CMake receive small
  separately identified hook commits, reconciled by 01. No shared dirty checkout.
- Workers update their lane doc and child issue. 01/02 maintain the aggregate
  roster/status/blocker tables; avoid 33 conflicting edits to the same board.
- If an interface is missing, post the exact inputs/output/lifetime/invariants,
  proposed header and one consumer test. Provider and consumer agree ownership;
  do not create a second generic subsystem. Temporary adapters stay private and
  are labeled until real integration passes.

### Copy/paste dispatch prompt

Replace `<NN>` with exactly one lane above. This is suitable for a fresh DeepSeek
session; do not copy the entire roster as one worker's assignment.

```text
You own lane <NN> from docs/PIKMIN2_IMPLEMENTATION_FANOUT.md.
Read AGENTS.md, that guide, and docs/PIKMIN2_FULL_IMPL_BLOCKERS.md first.
Check #186 and the existing family/child issue for active owners and pushed work.
If this lane is already owned, take an explicitly disjoint agreed slice or report
that collision; do not duplicate the implementation. Otherwise claim the lane in
4laric/pikmin-randomizer, assign the child issue to the authenticated account and
record the implementation-owner field required by AGENTS.md, plus your actual
executing agent/session separately.
Always specify --repo 4laric/pikmin-randomizer for GitHub writes. Never post upstream.
Implement the first bounded deliverable, then advance the lane's remaining gates
within its scope; do not stop at a plan, source audit or pure policy if ordinary
runtime is the requested gate. Reuse existing candidates and source contracts.
Use private root/native worktrees and ignored output; Native work branches may be pushed to native origin under the AGENTS.md Git push policy (never default/p2-integration branches, tags or force-pushes).
Coordinate shared interfaces and narrow hook commits with the named provider and
lane 01. Preserve other workers' changes. Obtain current baseline from lane 01.
Before runtime, rebuild exact-head, regenerate arena, verify live starting Pikmin
(default 20 reds when no squad exists), centred 960x540 window and active gameplay.
Reserve heavy-build capacity and the real-GL slot; keep working independently
while waiting. Record natural vs injected evidence and source-backed N/A honestly.
Deliver ordered commits, root/native bases and dirty state, source IDs, changed
files, contracts, build/executable/config hashes, fixture adoption, six-gate table,
remaining blockers and one exact reproduction command in your child issue.
Keep one active slice and one ready handoff; handoff to lane 01, not upstream/main.
```

### Required lane ledger and handoff

Lane 01/02 track each lane in #186 using:

```text
Lane NN / session name / worker / parent + child issue:
Status: unclaimed | active | waiting on named interface | handoff-ready | integrated
Owned source IDs and files; provider/consumer agreements:
Root branch/base/head; native branch/base/head; dirty state:
First deliverable and acceptance; candidate commits reused:
Blocking lane + exact contract needed (if any):
Build capacity / GL slot reservation (release time when done):
Handoff commits + evidence; integrated revision (only after lane 01 acceptance):
```

A lane is not finished when its branch is pushed. Integration must identify the
accepted commit and repeat changed combined gates. “Family complete” and “eligible
for the production randomizer” remain separate columns in lane 02's ledger.

## Sequence and acceptance

First product milestone: a small admitted P2 cohort in real generated seeds,
with automatic content staging, natural combat, rewards, revisit and restart.
Select species by demonstrated gates, not a fixed count or presumed difficulty.
In parallel, family owners finish source behavior and shared providers close
concrete consumer gaps; a universal AI framework is not a prerequisite.

Then expand by independent FSM/resource groups. Each implementation maps source
states, motion timing and events, including loop boundaries and interruptions.
Record event ownership, immunities, helper/attachment lifetimes and exactly-once
drops/rewards. Event metadata or sampled poses alone do not execute source behavior.

Each handoff reports the six arena gates as PASS / FAIL / BLOCKED / UNTESTED /
source-backed N/A, with evidence paths:

1. Exact identity and spawn.
2. Autonomous movement and animation.
3. Attacks and receivers.
4. Death and corpse.
5. Actual transport and reward.
6. Cleanup and re-entry.

Label injected state/health separately from natural combat. Manager recreation
does not prove full scene teardown or campaign resume. A starting squad does not
fix invincible proxies. Begin mixed-scene correctness, frame-time and memory
measurements with the first two implemented species; establish explicit budgets
with integration before scaling density. Family complete still requires every
parent identity and all applicable gates, including mixed-scene performance.

Before dispatch, reconcile status against the #434 audit and pinned source.
Historical “integrated” labels do not establish presence in draft #432. Source
inspection and the per-ID ledger decide which work is missing; do not repeat
completed King/Pelplant gates or silently omit hard-lane integration.

Before dispatch, reconcile status against pinned evidence and register the actual
lane in the local workflow registry. The old blocker document is historical;
King WarCry is passed. Scope only remaining unproven behavior and do not dispatch
duplicate cleanup/FSM work from stale blanket summaries.

## Private builds and reviewable handoffs

Use a lane-owned native worktree and build directory under ignored `output/`.
Do not edit/build the shared native checkout for exploratory lane work. Example
from the repository root, after creating the lane worktree:

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
cmake -S output/native-<lane> -B output/native-<lane>-build -G Ninja -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON
cmake --build output/native-<lane>-build --target pikmin_pc -j 6
cmake --build output/native-<lane>-build --target pikmin_pc -- -n
```

Replace placeholders. Ensure the Python-bundled `ninja.exe` is on PATH, or pass
its full path with `-DCMAKE_MAKE_PROGRAM=...`. The maintained Windows build uses
`PIKMIN_NATIVE_JAUDIO=ON`; the default OFF configuration can fail to link on
`Jac_NoteDemoSkipped`. Record pinned commit, private build directory, executable
SHA-256 and the no-work dry-run result for each attempt. Never run two heavy jobs
against one build directory. Use resource leases for private builds and the
aggregate heavy-build budget. Shared runtime fixtures require the shared-runtime
lease; private runtime launches are exempt from that reservation.

For replacement-main fixtures, use [the provenance builder](PIKMIN2_FIXTURE_BUILDS.md)
against that completed PRIVATE build:

```powershell
py -3.12 scripts/build_pikmin2_fixture.py --source output/native-<lane> --build output/native-<lane>-build --fixture <fixture.cpp> --expected-native-head <full-native-commit> --output output/<lane>-fixture-<attempt>
```

Run only an attempt whose `provenance.json` status is `built`. Freshness rejection
requires resolving inputs and rebuilding; a produced executable alone is insufficient.
The builder does not launch, stage assets, or supply the starting squad/window policy.

Cap each worker at one active implementation slice and one ready handoff. Each
handoff includes parent/child issue, owner, exact base and ordered commits, owned
files, requested shared hooks, source mapping, tests, build provenance, fixture
adoption record, gate evidence and remaining work. Isolate shared-semantics edits
into focused commits. Update the issue with progress and integrated commits.

Family owners can implement narrow additive registration hooks. Saves/rewards,
captain state, generic damage/physics, actor lifetime, converter defaults and ID
conflicts require #186 review. Only integration builds `native/build-randomizer`
after integration and runs `scripts/export_native_source.py`. Native origin pushes
follow [AGENTS.md](../AGENTS.md#git-push-policy); main/default and p2-integration
branches remain protected. Keep assets, builds, logs, saves and runtime state local under `output/`;
do not modify the parallel original BBFT or decomp/research checkouts or relink AP.

## Integration sweep inventory (lane 01)

A root push is not the complete handoff inventory. Read each current lane issue's
latest delivery comments and resolve the native branch/commit and any local root
branch they name. Native work branches may be pushed (AGENTS.md push policy), but a completed
native handoff may exist only in the shared local Git object database. Record the
accepted root/native pair separately, including standalone native dependencies
of root fixtures. Compare source or patch equivalence where cherry-picking makes
ancestry differ; do not reapply superseded exports. Review shared hooks, build,
export and run the supplied consumer fixture rather than treating a merged root
document as native integration. Record explicitly any held dependency and why.
See [the continuation audit](PIKMIN2_NATIVE_HANDOFF_INTEGRATION_437.md).

## Mandatory captain safety (#632; active lanes included)

Before the next runtime run, add the fixture-only canonical helper
`scripts/p2_fixture_captain_guard.h` (absolute include or hash-recorded local copy),
or an equivalent tested guard. It never changes health or production behavior.
Once the captain has initialized, call the guard immediately after the engine
idle step and BEFORE movie/pause/UI early returns, readiness gates, observation
counters, or PASS markers. Check all three independent signals:

```cpp
Navi* n = naviMgr ? naviMgr->getNavi() : nullptr;
if (n) {
    p2_fixture_require_captain(GameStat::orimaDead,
        n->getCurrState() && n->getCurrState()->getID() == NAVISTATE_Dead,
        n->mHealth, observed);
}
// Only now process pause/movie/UI and increment observed ticks.
```

Include the pinned engine's GameStat/Navi/NaviState declarations. This helper
prints P2_FIXTURE_CAPTAIN_DOWN and exits 86 (BLOCKED), including nonfinite HP.
Do not skip death checks just because a movie or pause is active. An initialized
captain disappearing unexpectedly likewise blocks observation, rather than
counting ticks. A timeout alone does not explain whether gameplay advanced.

Park the captain outside the tested enemy's actual attack reach for enemy death,
transport and re-entry tests where captain hits are irrelevant. Do not move him
away when captain targeting/damage is the test. Do not introduce blanket health
refills, revive/clear death flags, disable extinction, or change production rules.
Protection is permitted only as explicitly labelled fixture instrumentation for
isolated observations; record its mechanism and exclude it from captain-damage,
survival and unmodified-combat acceptance. Separate unprotected runs prove those.

Record child issue, fixture/guard hashes, placement/protection policy, rebuilt
executable hash, a negative captain-down guard test, and fresh runtime log. Existing
runs are not retroactively protected. Interrupted logs are diagnostic evidence;
mark unfinished gates BLOCKED/UNTESTED. Preserve earlier PASS evidence using its
separate original successful run. Handoff validation rejects captain-down log
references supporting PASS gates or PASS slice criteria. It does not infer safety
from absence of a marker in an old, uninstrumented fixture. Reviewers must verify
adoption before accepting fresh runtime claims. Death-specific tests may cite the
interruption as a labelled negative test, not as general gameplay completion.

For affected active lanes, the controller sets a captain-safety adoption requirement
and writes `captain-safety-required.md` in their runtime output plus an integrator
review notice. A runtime handoff must add:

```json
"captain_safety": {"policy": "unprotected", "evidence": ["guard_source", "guard_negative_test", "fresh_runtime_log"]}
```

inside `fixture_adoption`, with keys resolving to hashed handoff evidence. The
reviewer checks the source call order and each evidence role; merely supplying
keys does not prove adoption. Use `protected_observation` only for the isolated,
labelled case described above. Its attack/receiver PASS is rejected. Existing
already-submitted handoffs are not rewritten; apply the requirement before the
next run. Subsequent controller dispatches repeat the instructions explicitly.

## Preparation packets are not source implementation

A missing native hook, build registration or engine entry point needs a job that reserves the actual native files in a private native worktree, implements them, compiles/tests them and submits native commits for the existing integrator to review and merge. A job owning only documentation and a Python patch generator is preparation, even if its title says "landing" or "integration candidate". Integrating that packet does not integrate its proposed native patch and must not clear the consumer's source dependency.

The single-writer restriction protects the maintained checkout and final merge/export. It does not prohibit issue-backed, exclusively owned private native implementation. Serialize overlapping file claims; do not evade them by producing repeated packets. Record the actual executable producer lane with `workflow.blocked_followup` so verified source integration can wake its consumer. The #668 Mar registration job is an example: it owns native CMake/preview/Mar/receipt code and compiled tests, while #665 is only a preparation input.
