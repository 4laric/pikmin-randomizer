# Contributing

Read [AGENTS.md](AGENTS.md) first for repository layout, build isolation, push policy and issue-first tracking.

## Playtest seeds for the owner (binding)

The owner's playtest time is the scarcest resource on this project. A seed or build handed over for hand testing must make the thing under test impossible to miss. "I couldn't find it" is a failed handoff, not a failed feature (#945).

Minimise the owner's total effort: setup, travel, searching, combat, waiting, restarts and reporting. Prefer an immediate, unmistakable canary over a single distant target when both answer the same question. This is the same rule as the Bloodborne randomizer's "Saw Spear" example: don't change one pickup and ask the player to walk to it; change every applicable one so the next convenient one answers the question. Use one specific placement only when that exact slot or arena is the question, and say why a cheaper setup can't give the same answer.

0. **Define the question and the outcomes first.** Before handing over, write down what is being tested and what each result looks like. Cover pass, fail, partial, and "nothing visible", plus what each one means and what happens next. A valid session should answer the question whatever the outcome. An unexpected result goes back to engineering; it isn't permission for an endless series of "try this build" requests.
1. **Put it at the start.** Place every enemy, item or mechanic under test where the owner meets it within about 30 seconds of the day starting: at the landing site, or on the first path out of it. Choose the start area to match. Never rely on a slot that happens to be approved or convenient somewhere else on the map.
2. **Saturate.** Fill every ordinary slot in that starting zone with the species under test, and use several instances rather than one. If you test several species, group each one so it's obvious which is which. Leave out anything in the zone that would distract from or block the test.
3. **No gates.** Nothing under test may sit behind a bomb wall, a gate, a colour requirement, a later day (`first_day` above the start day) or a boss. If the test needs a gated place (a boss arena, for example), start the seed there or give the exact route.
4. **Ignore approvals for smoke seeds.** Placement approvals (root `accepted_slot_uids`, native compiled slot lists) are for real seeds. Owner smoke seeds bypass them (owner ruling 2026-09-29). Use the smoke-seed bypass switch and script once they land, rather than settling for an approved slot far away.
5. **Verify before handing over.** Launch the seed yourself (headless, one session at a time) or otherwise read its `native.log`. Confirm every species under test bound (`bound=1`, no `slot-rejected`, family bind/READY lines) at the coordinates you intended. Never hand over a seed where something silently failed to spawn.
6. **Say where and what.** The handoff states, per item: where it is (landmark or direction from the ship), how many there are, and what to check (for example: kill, carry to Onion, latch, sound). Keep it to a few lines.
7. **Don't make the owner wait.** Reuse prepared P2 content and extract only species that aren't cached. A swap of a few species should take minutes, not a full re-extraction.
8. **Owner commands are PowerShell.** Give one copy-pasteable PowerShell command that launches the seed, and put all of its files under ignored `output/`.

## Placement: don't hard-code where a species may go (binding)

Placement rules decide which seeds are *valid*. They must never decide what the game *can* spawn. We walked into this footgun on 2026-09-29:
- The Dirigibug could only spawn on one Distant Spring slot, because its first evidence run happened to use that slot and the slot was compiled into native as its only accepted target.
- The Crawbster and Titan Dweevil could only spawn in boss arenas, one of them locked until day 9.
- Owner smoke tests of three species needed a native rebuild just to put them next to the start.

1. **One source of truth, in root.** Seed generation (`randomizer/`, `docs/PIKMIN2_ADMITTED_PLACEMENT.json`) decides where a species may be placed. Native spawns what the seed binds. Native may refuse a binding only for a concrete runtime incompatibility, such as terrain, water, a missing host type or unstaged content. It then logs `reason=<specific cause>`. It never refuses because a slot id isn't on a compiled list.
2. **No compiled slot whitelists or per-species slot constants in native.** Evidence slot ids belong in evidence documents and tests, never in spawn gating. When you touch code that gates on one (`p2campaign::accepted`, `*_slot()` evidence constants, `slot-rejected`), move the decision to root data or remove it.
3. **Constraints describe the species, not a history.** Accepted placements come from the species' real needs: terrain, footprint radius, flight space, water, helpers, arena. "The slot where the evidence run happened" is evidence for that slot, not a restriction on others. A species must not end up with a single legal slot unless its needs genuinely allow only one; flag it in review if it does.
4. **Bosses are placed by constraint, not by cast list.** Arena placement is a data rule (footprint, clearance, protected drops). The same species must also be placeable on any slot that meets its footprint when a smoke seed or the dev console asks for it.
5. **Dev and smoke overrides are always available.** Every placement restriction must be bypassable by the smoke-seed switch or the dev console without a rebuild. A restriction that can only be lifted by recompiling is a defect.
6. **Review check.** A PR that adds or narrows a placement restriction must say which runtime constraint it encodes, and confirm the smoke bypass still reaches it.
