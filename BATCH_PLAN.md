# Exploration and capacity batches

Approved direction: Flarlic capacity items, deployed-population milestones, first-defeat bestiary checks and exploration. Work stays in the isolated Pikmin workspace.

## Batch 1 — Flarlic and population

New opt-in schema-2 expanded-check profile; schema 1 remains unchanged. Start at 20 field capacity, eight Progressive Flarlic items each add 10, maximum 100. Respect the limit at spawn, sprout conversion and queued Onion withdrawal, including workers and carriers, without modifying saved user settings. Population checks occur once at 20, 30, ... 100 actual active Pikmin; stored Pikmin and unplucked sprouts do not count. Native counts—not receipts or capacity—award checks. Add native part-weight capacity requirements, sourced from loaded pellet configs. A Flarlic may never be placed behind its own required capacity with no alternative reachable check.

## Batch 2 — First-defeat bestiary

Eight initially supported native species: Dwarf Bulborb, Spotty Bulborb, Female Sheargrub, Male Sheargrub, Shearwig, Fiery Blowhog, Water Dumple and Wollywog. Award once per species across areas/days. Hook confirmed zero-health death, not damage, sighting, corpse delivery, stage teardown or despawn. Exclude bosses, spawners, props, unused creatures and time-limited species in this first catalog. The tracker displays defeated/unseen entries. Conservative availability requirements are separate from the runtime death trigger.

## Batch 3 — Exploration and integration

Eight initial checks: first active landing in each of the four supported areas, plus scouting at least 600 world units horizontally from that area's ship base. Require active, grounded, living captain gameplay; no awards in movies, menus or area unlock receipts. Scout checks are small exploration objectives, not claims that distant authored landmarks/routes have been audited. Later expand to named landmarks after route evidence is available.

Expanded total: 55 checks = 30 existing + 9 population + 8 species + 8 exploration. Item pool: five area/color unlocks, eight Flarlic, 25 required repair rewards and 17 surplus repair rewards. Goal stays 25; surplus repairs permit optional objectives without inventing unimplemented filler effects. Useful classification for surplus repair items in AP; distinguish pool size from victory threshold. No type unlock is a finite, irreplaceable individual Pikmin. Exact campaign resume and extinction recovery remain separate open work.

## Acceptance per batch

- Versioned catalogs/capabilities; existing IDs and schema-1 behavior preserved. Refuse unknown schemas, mismatched saves and cross-profile receipts.
- Deterministic solo/AP generation, capacity-aware part and milestone requirements, no self-locks, real fills over 100 seeds per profile.
- Compiled native probes check receipt limits, high-ID round-trip, exact thresholds, repeat deaths/checks, invalid stages, inactive gameplay and durable journal recovery.
- Hidden native smoke uses actual 20-red startup and tests capacity updates without inventing population/bestiary completion. Further gameplay acceptance must cover breeding, Onion UI withdrawal, kills and scouting; synthetic native event tests do not count as physical gameplay evidence.
- Emit a check-status report for population, bestiary and exploration. Preserve original BBFT functionality and files.

Physical part relocation, named remote landmarks, bosses, new Pikmin species, treasures and caves are outside these three bounded batches and retain their existing roadmap issues.

## Implementation status

All three batches are implemented locally. Tracking: [capacity #13](https://github.com/4laric/pikmin-randomizer/issues/13), [bestiary #14](https://github.com/4laric/pikmin-randomizer/issues/14), [exploration #15](https://github.com/4laric/pikmin-randomizer/issues/15).

17 Python tests and 201 AP fills pass. The compiled native probe passes all three categories, including check bit 54. Scripted native gameplay reached every actual population threshold from 20 to 100 after fixing allocation at the initial cap; it uses synthetic stored stock. The full scripted smoke did not pass: a culled dwarf with forced zero health did not produce a death event, and a repeat run encountered a transient state-file open failure. The adapter now pauses/retries failed opens while still rejecting malformed records. Player combat, breeding, all-area scouting and complete campaign acceptance remain open. Do not treat the event probe as proof of those gameplay paths.
