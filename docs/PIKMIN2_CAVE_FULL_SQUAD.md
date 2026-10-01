# Full-squad cave exit fixture (#1072)

The earlier #930 route saved 20 living Blue Pikmin but only one followed the
captain to the hole. A global survivor count cannot establish physical arrival.
This fixture recalls the idle Pikmin after real water-treasure delivery, waits
for followers at each return waypoint, and observes each original actor in the
water passage before allowing checkpoint/exit.

`native/tools/p2_cave_full_squad_fixture.cpp` is a separate replacement main.
It writes native controller main-stick, C-stick, whistle and disband inputs.
It never writes gameplay actor positions, velocities, species, AI modes or carry
attachments. The entry protocol deliberately stages 20 Blue Pikmin; this does
not prove natural Blue supply. Exit confirmation remains bypassed through the
existing native checkpoint API, followed by the actual native exit code 42.

Acceptance requires all 20 original actors observed in the 100-unit water passage
and then east of it, all 20 in formation within 120 three-dimensional units of
the captain at the hole for 30 observations, a durable real water receipt, and 20 checkpointed
survivors. Per-actor positions are logged before saving. A fresh process must
consume the actual transfer/receipt, restore the squad and suppress the delivered
treasure. The forced captain-down control must exit 86 with no success marker.
Positions must be finite and within 30 units of the floor height for passage and
arrival. The captain walks a small diamond inside the hole's interaction radius
to regroup through ordinary controls. Intermediate waits allow a 170-unit trailing
formation; the final 120-unit arrival criterion remains unchanged. Inherited
autoplay settings are cleared, with the master switch explicitly disabled.

Use `scripts/run_pikmin2_cave_full_squad.py` with explicit paths for the canonical
`--workspace`, frozen `--fixture`, private `--production` executable, local
`--generator`, legal `--assets`, converted `--pod`, and a fresh `--run` beneath
the canonical ignored output directory. Modes are `full_squad`, `negative`, and
`restore`; the latter requires `--previous` pointing to an accepted full-squad
run. The runner applies background-test policy and measured capacity admission,
preserves raw supervisor outcomes, and checks the scenario's actual exit contract
separately. It hashes producer outputs before allowing restart.

The minimum fixture baseline remains a fresh current overlay, a live supported
squad, centered 960×540 startup and the captain guard. Failed attempts must stay
immutable. Source-only changes belong on the new `codex/cave-full-squad-1072`
branches; #930's accepted handoff and merged branch heads remain untouched.

Runtime acceptance is pending. Natural Yellow/Blue progression, mixed colors,
electric delivery, hand-play F6 confirmation and complete campaign/AP/supervisor
acceptance remain separate gates. This fixture does not certify maintained
export or deployment.
