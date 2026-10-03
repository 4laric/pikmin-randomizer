# Toady lone-captain encounter (#1233)

Use a fresh isolated room containing source ID 101 (UmiMushiBlind), current production executable and current room overlay. Preserve legal assets and saves in ignored output. Confirm 20 starting Pikmin, active gameplay, and a centered 960x540 window before testing.

1. Dismiss the squad well outside the tongue and shove reach. Keep every Pikmin outside the forward attack cone, so it cannot initiate the attack being tested.
2. Approach the Toady from its front inside 170 units and 30 degrees of its facing. Observe a natural attack1 tongue animation initiated by the captain alone. The 170-unit query is the source attack-start range; actual damage remains tied to the moving tongue slots at key 5 and is not guaranteed by entering the acquisition cone.
3. Withdraw. Approach from behind and wait through its idle/move cycle: the rear captain must not initiate a tongue attack. It may eventually turn and then legitimately attack; record facing at attack initiation.
4. With two captains, leave captain one closer behind and captain two farther ahead inside the cone. The front captain must still initiate the attack. Dead, hidden or already mouth-held captains must not initiate this new query.
5. Repeat with source ID 71 (UmiMushi): its existing stored captain target and Pikmin attack behavior must remain unchanged. Repeat 101 with a Pikmin bait in the forward cone to verify its existing Pikmin path.
6. Continue ordinary combat through tail damage, death animation and actual corpse/drop/carry. Leave and re-enter the scene, then save/resume if the campaign supports it. These lifecycle steps are regression acceptance, not proved by the policy test or production build.

Record executable/source pin, private arena and logs, live squad/window observations, and PASS/FAIL/UNTESTED for acquisition, actual tongue damage, natural death/drop, transport/reward, cleanup/re-entry and save/resume. Do not enable PIKMIN_P2_UMIMUSHI_PROBE for player acceptance: it moves bait and throws Pikmin as instrumentation.
