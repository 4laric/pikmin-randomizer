# Contributing

Read [AGENTS.md](AGENTS.md) first for repository layout, build isolation, push policy and issue-first tracking.

## Playtest seeds for the owner (binding)

The owner's playtest time is the scarcest resource on this project. A seed or build handed over for hand testing must make the thing under test impossible to miss. "I couldn't find it" is a failed handoff, not a failed feature (#945).

1. **Put it at the start.** Place every enemy, item or mechanic under test where the owner meets it within about 30 seconds of the day starting: at the landing site, or on the first path out of it. Choose the start area to match. Never rely on a slot that happens to be approved or convenient somewhere else on the map.
2. **Saturate.** Fill every ordinary slot in that starting zone with the species under test, and use several instances rather than one. If you test several species, group each one so it's obvious which is which. Leave out anything in the zone that would distract from or block the test.
3. **No gates.** Nothing under test may sit behind a bomb wall, a gate, a colour requirement, a later day (`first_day` above the start day) or a boss. If the test needs a gated place (a boss arena, for example), start the seed there or give the exact route.
4. **Ignore approvals for smoke seeds.** Placement approvals (root `accepted_slot_uids`, native compiled slot lists) are for real seeds. Owner smoke seeds bypass them (owner ruling 2026-09-29). Use the smoke-seed bypass switch and script once they land, rather than settling for an approved slot far away.
5. **Verify before handing over.** Launch the seed yourself (headless, one session at a time) or otherwise read its `native.log`. Confirm every species under test bound (`bound=1`, no `slot-rejected`, family bind/READY lines) at the coordinates you intended. Never hand over a seed where something silently failed to spawn.
6. **Say where and what.** The handoff states, per item: where it is (landmark or direction from the ship), how many there are, and what to check (for example: kill, carry to Onion, latch, sound). Keep it to a few lines.
7. **Don't make the owner wait.** Reuse prepared P2 content and extract only species that aren't cached. A swap of a few species should take minutes, not a full re-extraction.
8. **Owner commands are PowerShell.** Give one copy-pasteable PowerShell command that launches the seed, and put all of its files under ignored `output/`.
