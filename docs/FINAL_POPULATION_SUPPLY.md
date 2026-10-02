# Final saved food suppliers (#1186)

Parent #1153; implementation owner Codex through shared account 4laric.

This is a source/config model candidate for the experimental mixed P1 plus all42
release. It does not enable new population rules, alter the admitted pool, or
change legacy manifests. Physical route, combat, Onion birth and renewal
acceptance remain open.

`scripts.audit_population_supply` reads the legal local generator/config inputs
and emits metadata only. The committed Python data snapshot contains975 generator
records (690 Teki/boss plus285 GenObjectPellet records),116 generator-file hashes
and62 loaded pellet configurations. Ship parts remain identifiable by config
kind3 and contribute no food. `GenObjectPlant` is decorative vegetation; Pellet
Posies are Teki species7 and were already present in the original raw audit.

`population_supply.resolve` applies the saved resolved enemy catalog and exact
arena suppression to these facts. It saves guaranteed minimum counts, activation
and expiry, cache flags, replenishment interval, final P1/P2 identity, carrier
minimum/slots, per-Onion guaranteed yields and explicit logical review branches.
Probabilistic extra pellets, zero counts, suppressed actors, unquantified P2
module overrides and kill-only P2 sources contribute no guaranteed food. A P2
occupant never inherits its P1 vehicle's corpse yield. Unknown P1 corpse sources
outside the persistent resolved catalog remain unquantified.

The calendar distinction matters. `Generator::informDeath` updates the latest
spawn day when a group is depleted. Cached positive-interval respawn requires
`currentDay >= latestSpawnDay + interval`, while the ordinary campaign's
`pc_randomizer_next_day` holds day29. Those sources cannot replenish indefinitely
after late depletion. The seven protected Hope dwarf records still supply nine
bodies at four gross births each in an initial complete wave; UID40410547 has
count0. Default reloads and active cached interval0 sources can replenish at the
day cap according to the source condition, subject to actual gameplay acceptance.
Finite waves are counted once; no theoretical earlier respawn cycles are credited.

The five Hope default Posies offer a separate candidate renewable witness. Their
reload flags0, interval0, chance1 and positive minimum count give a guaranteed
number pellet when fully grown. Premature cutting sets its drop count0 in
`TaiPalmSettingPelletAction`. Yield uses the worst nonmatching Onion outcome,
preserving random/cycling pellet colors. Matching color is never assumed.

Logical branches require a review evidence reference, the usable carrier colors,
permanent Onion/combat/route prerequisites and a fully-grown-Posy allowance where
needed. Optional delivery filler cannot be a prerequisite or create supply.
Coordinates and parser success cannot supply these reviews. The production
resolver therefore emits unreviewed branches by default; model test branches
are clearly identified as synthetic logic fixtures, not physical acceptance.

`growth_bound` checks area access, target Onion, the actual saved color carry
profile and field capacity, finite consumed counts, activation and expiration.
It also requires explicit `usable_carriers` counts for the destination color;
missing counts mean zero. Neither an unlocked Onion, delivery items, stored stock
nor the capacity limit establishes a living, available squad. At native a489,
`GameCoreSection.cpp` 4196–4226 grants five stored Leaf Pikmin once for each newly
unlocked nonstarting Onion. Withdrawal and route usability still need a witness.
It keeps unavailable/delayed/expired food out. Consumption and activation state
are explicit caller inputs; reconstructing the JSON snapshot cannot reset food.
`can_reach_population` keeps starting20 and needs actual food above that. Total
population uses one destination-color witness rather than double-counting finite
food across different Onions.
These are individual gross-growth bounds, not a global allocation of finite
food among progression milestones. Production activation must either provide
reviewed renewable witnesses or allocate finite food once across the entire
progression proof; separate successful count queries cannot reuse a consumed body.

## Exact-owner integration proposal

The static proposal saves `bootstrap_proofs` alongside supplier routes. Both
reconstruct from the code-owned registries during validation, so a changed Onion
retrieval prerequisite invalidates the old snapshot rather than silently changing
reachability under its saved fingerprint. Retrieval proofs accept exact version,
nonempty textual evidence and unique permanent progression requirements only;
delivery filler, unknown fields and malformed values are rejected. Empty reviewed
registries still refuse activation. These are source controls, not route proofs.

The current seed owner should review the source snapshot and bounded logical
branches before enabling it. Required hooks belong to the genuine seed/catalog,
AP/session and native owners:

1. Generate the versioned snapshot only after P1/P2 assignment and arena
   suppression, before progression fill. Freeze reviewed branches from immutable
   source/config/route evidence. Do not activate a snapshot with no reviewed
   suppliers as a release default.
2. Include the optional snapshot in strict manifest validation and fingerprint
   reconstruction. Legacy seeds without the field retain their existing rules.
   The field is passive logic metadata and needs no new native capability solely
   to be serialized; any actual native renewal change needs its own version.
3. Dispatch population checks to `can_reach_population` only for the new field.
   Preserve the saved field through AP slot data, client restoration, tracker and
   reconnect. Native save/caller consumption integration must not manufacture
   finite food. Define the usable initial carrier supply of newly unlocked
   Onions as part of the reviewed branch; unlocking alone is not physical proof.
4. Run genuine Generate/Main starting-color/area, cap10, minimum stats and
   progressive carry/maturity fills, plus remote-Onion cases. They remain pending
   until the owner hooks and reviewed branches are adopted. Existing successful
   abstract fills are not farming evidence.
5. Independently verify ordinary combat, body/pellet return, actual Onion sprouts,
   repeated-day replenishment and native save/resume/reconnect on selected UIDs.

The regressions cover full42 preservation, final kill-only identities, protected
counts, last-source suppression, expired/delayed/missed activation, locked Onion,
missing combat requirement, one-fewer carriers, excluded filler, finite
consumption through JSON reload and an alternate fully-grown-Posy witness.
No shared seed/catalog/runner/native source is changed by this candidate.
