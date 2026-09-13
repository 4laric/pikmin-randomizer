# Purple impact attack specification

Status: target specification, 2026-09-13. The [landing earthquake and Red dwarf receiver](PIKMIN2_PURPLE_IMPACT_GATE_AB.md) are implemented; [direct-hit progress and evidence](PIKMIN2_PURPLE_DIRECT_HIT.md) are tracked separately. Full HipDrop flight and feedback remain future work. Tracking: [#393](https://github.com/4laric/pikmin-randomizer/issues/393), parent [#113](https://github.com/4laric/pikmin-randomizer/issues/113). Implementation owner: Codex through shared account `4laric`.

## Goal and scope

A thrown Purple should land with a heavy impact: a direct enemy collision follows that enemy's press/hipdrop behavior, while nearby eligible enemies receive a separate earthquake that can produce a bounce and stun. Damage, shaking, crushing and stun are distinct outcomes. A shockwave must not subtract health from everything nearby.

Target the experimental Pikmin 2 mode. Existing Purple identity, carrying, conversion and sampled rendering are prerequisites. This spec does not change the P1/AP proposal in #9, ship storage, population rules or White Pikmin. Ground-impact support alone must be advertised as a partial implementation until flight, direct hits, feedback and supported enemy families pass their gates below.

## Evidence and parameter contract

Source revision: `632af93787b9c95b63f0c13be32b161375ce3a96` (verified locally). Use the existing [emitter contract](pikmin2-purple-emitter-contract.md) and [dwarf stun audit](pikmin2-kochappy-purple-stun.md), with reproducible extractors in `experimental/pikmin2_purple_emitter_reference.py` and `experimental/pikmin2_kochappy_stun_reference.py`. Direct inspection for this spec includes `native/pikmin2-research/src/plugProjectKandoU/pikiState.cpp:1733–1952`, `enemyInteractBattle.cpp:11`, and `enemyBase.cpp:2858` in `src/plugProjectYamashitaU`.

| Property | Contract |
| --- | --- |
| Earthquake radius | Retail P017 = 60 world units, expanded by target bounding radius |
| Direct hipdrop payload | Retail P022 = 20; header default 100 is not the retail value |
| Ground/platform recovery | 0.3 seconds after impact |
| HipDrop entry pause | 0.25 seconds before descending/homing phase |
| Dwarf generic hipdrop fallback | Audited family parameter 50; not additional guaranteed damage and not necessarily reached |
| Dwarf Fit chance | Random value strictly below 0.3 after earthquake landing, unless retained positive stun timer selects Fit |
| Dwarf Fit duration | Red 10 seconds; Snow/Orange 5 seconds, separately enabled and validated |

Values above describe the audited source/retail reference. Do not extrapolate dwarf duration or damage to other enemy families. Store parameter provenance with implementation evidence. This task does not rerun ISO extraction.

## Attack lifecycle

1. Arm an attack only for an enabled, living Purple entering an eligible thrown attack. Give it a source lifetime ID and monotonically increasing attack token. Ordinary falls, sprout launches, carrying drops, walking and other colors must not arm this feature.
2. Full fidelity requires the P2 HipDrop entry/transition audit. Inside HipDrop, source clears velocity and waits 0.25 seconds, then sets downward velocity from gravity. Its custom-radius 50 candidate search selects the closest living enemy by 3D separation and sets horizontal velocity toward it at 120 units/second where horizontal distance is nonzero. Falling rotates facing and uses FALL animation. These are source rules, not permission to add homing to every native fall; audit the upstream transition into HipDrop before implementing this phase.
3. Ground or platform contact outside the recovery substate emits impact feedback and an earthquake, enters recovery and waits 0.3 seconds before returning to ordinary AI. Duplicate collision/bounce notifications for this same impact must not create another wave.
4. A collision with another Pikmin returns without impact processing. On enemy collision, descending velocity first permits Hipdrop dispatch. The receiver tries press before generic hipdrop fallback; earthquake follows that dispatch. Re-read vertical velocity, then dispatch the source's additional Press payload of 10 only if still descending. This is intentional callback ordering, not permission to add every payload to health.
5. Preserve source attachment fallback when the final interaction was not accepted and the collision part is stickable on a living target. Exit HipDrop only if it is still the active state; do not override a state transition caused by a callback.
6. Clear transient arming on consumption, death, state cancellation, stage teardown and actor reuse. A new throw obtains a new token. Impact tokens are runtime state and must not replay on checkpoint reload.

## Earthquake and receiver behavior

The source candidate predicate is `dx*dx + dz*dz <= (60 + targetRadius)^2`, including equality. It uses target position, ignores Y in the narrow-phase test, and deduplicates targets within the iterator pass. Source cell membership still bounds enumeration. A registered-actor scan with this predicate is an explicitly documented port approximation; adding an arbitrary vertical cutoff would be a behavior change.

Map radius from the native actor's collision bounds after an adapter audit. Do not use a visual or shadow radius. Only registered supported actors receive the new interaction; unsupported families retain existing behavior and do not count toward coverage.

Dispatch the special DropEarthquake birth response before normal eligibility when that family supports it: source can transition a waiting actor to Appear. Normal eligibility requires floor contact, alive/nondead/nonflying state, and absence of hard constraint, bitter, no-interrupt and bitter-immune conditions. Unsupported flag mappings must be explicit gaps, not guesses from similarly named P1 fields. The source callback returns false even when it changes state; use an explicit adapter outcome for instrumentation rather than treating that boolean as rejection.

For the audited dwarf lifecycle, Earthquake stops motion and supplies vertical velocity `200*bounceFactor + 100*random`; Purple supplies bounceFactor 1. After more than three updates and ground contact, select Fit using retained timer or the family chance, respecting interruption flags. Fit advances elapsed time and exits strictly after its family duration. Repeated earthquake must preserve an already positive timer rather than reset a full stun duration. Death and bitter interruption remain active. Freeze locomotion/attack through the lifecycle action, never by skipping the whole BTeki strategy or setting a debug freeze flag.

## Native design and rollout

Use separate emitter and family receiver modules. An event contains source lifetime ID, attack token, cause, position and direct-target/collision-part identity where relevant. The emitter deduplicates the wave; it must not accidentally suppress the intentional direct callback sequence. Receiver state is keyed by target lifetime, with lifecycle phase, bounce update count and retained Fit elapsed time. Log accepted/rejected reasons, pre/post health and state, and event IDs in test builds. Consume gameplay RNG at the source decision points; inject deterministic rolls in policy fixtures.

| Gate | Deliverable and completion evidence |
| --- | --- |
| A: adapters | Audit native thrown hooks, target collision radius, supported flags, RNG and Chappy action ordering. Identify a damage/death-preserving stun insertion point and a disposable Purple-enabled Pod arena. No player launchers or shared assets changed. |
| B: first playable slice | Opt-in thrown-Purple landing emitter plus registered Red Dwarf Bulborb earthquake/bounce/Fit receiver. Preserve native direct collision behavior and label direct-hit fidelity pending. Prove damage and death during stun before enabling this slice. |
| C: direct attack | Port audited Hipdrop/Press dispatch, collision-part handling and attachment fallback without stacking duplicate native damage. Validate dwarf crush separately from generic fallback. |
| D: complete Purple flight and feedback | Audit entry to HipDrop, then implement pause, descent/homing, spin/FALL, landing recovery, impact sound/effect and bounded camera/rumble feedback. Clear effects on interruption and teardown. |
| E: family coverage | Enable Snow/Orange independently with their five-second durations. Add every further family only with a source receiver contract, immunity/exception coverage and native acceptance. |

Likely touchpoints are new `native/pc_port/pc_p2_purple_earthquake.*` and per-family stun modules; `pc_p2_purple.*` for identity/arming; native `pikiState.cpp` for audited throw/contact hooks; family registration/reset code; and the specific Chappy reaction/action ordering. Final hook locations must be recorded at Gate A. Do not replace shared strategy logic or globally change enemy parameters. The existing Purple preview requires a Pod; use an isolated compatible fixture rather than silently changing the no-Pod enemy arena.

## Acceptance matrix

These are requirements, not claims of executed native tests.

| Case | Required result |
| --- | --- |
| Source and mode | Enabled thrown Purple triggers; ordinary colors, disabled mode, walking, sprouts and unarmed falls do not |
| Geometry | Just inside, exactly on and just outside 60 + collision radius behave correctly; nonzero radius and large Y separation covered; broadphase approximation recorded |
| Duplicates | Collision plus bounce generates one wave per impact, one target visit per wave; a later throw and a different Purple remain independent |
| Direct collision | Ascending hit skips descending interactions; descending trace follows Hipdrop, earthquake, velocity re-read, conditional Press; no unconditional 20 + 50 + 10 health subtraction |
| Crush/fallback | Accepted dwarf press bypasses generic fallback; a separately audited fallback receiver gets its correct behavior; stickable rejection preserves attachment |
| Eligibility | Corpse, airborne, constrained and interrupted actors reject as specified; birth-drop exception has its own result; unsupported family unchanged |
| Bounce/stun | Ground contact alone before the update threshold cannot select Fit; roll 0.299 succeeds and 0.3 fails when no retained timer; Red exits only after 10 seconds |
| Repeated impact | Retained positive elapsed timer is not refreshed to full duration; two distinct impacts remain distinguishable |
| Damage/death | Normal attacks reduce health during bounce/Fit; lethal damage interrupts and yields exactly one normal death/corpse path |
| Lifetime | Removal, reset and reused actor addresses clear state; reload does not replay an impact or preserve a stale stun |
| Regression | Ordinary P1/AP combat, health, throwing, carrying and corpse delivery remain unchanged; Purple conversion/ten-unit carrying still work |
| Natural play | Controller throw demonstrates direct hit, nearby bounce, both chance outcomes across attempts, recovery, repeated throws and kill during stun; logs and capture identify exact build and family |

Policy tests establish boundaries and ordering. Compiled integration tests must exercise actual native callbacks and death processing. A Windows production build plus isolated natural-play evidence is required for gameplay sign-off; forcing an FSM or injecting a throw in a fixture is not equivalent to controller acceptance.

## Remaining uncertainties

The [flight implementation and evidence](PIKMIN2_PURPLE_FLIGHT.md) now cover the upstream Purple apex transition, entry pause, descent/homing, spin, source ROLLJUMP/FALL poses, recovery and native feedback. Scripted full throws cover ground recovery and an adult direct hit. Native spatial/organic target enumeration and ordinary-AI re-entry are explicit adaptations. Original P2 particle/audio rendering, full controller acceptance, dwarf-crush acceptance and further family-specific direct-hit fidelity remain open. There is no universal enemy stun duration, guaranteed 30% stun for every species, or area-damage promise. Completing these bounded gates does not close #113 or constitute campaign acceptance.
