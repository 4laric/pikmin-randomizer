# BigFoot natural Mitite death drop (#1231)

Implementation source: native 51e25ed622ecda443805c81e8730e58b69381496. Source/compiled tests are bounded evidence; this manual encounter has not yet passed natural gameplay acceptance.

Use the prepared NEW private package `output/bigfoot-mitite-natural-1231-v2`, generated with `output/bigfoot-mitite-prepare-baseline20.py` through the ordinary smoke generator with starting_flarlic2. The older cap10 package and its sessions are preserved. Manifest inspection verifies red starting color, cap20 and exactly one source69 placement; resources68/69 are staged with no extra child placement.

```powershell
& C:/Users/alari/pikmin-randomizer/output/bigfoot-mitite-natural-1231-v2/play.ps1 -Exe <exact-reviewed-private-nectar.exe>
```

Before approaching the boss, use the ordinary Onion menu to withdraw all20 starting reds and observe field20 alive on terrain. Real campaign startup keeps the20 stock in the Onion for manual play (`gameSetup.cpp319`, `gameCoreSection.cpp4235-4259`); package preparation is not evidence of20 live field actors. No test-background/autoplay/health edits or boosted damage. The source boss health remains10000.

The new launcher explicitly requests `PIKMIN_P2_ROOM_WINDOW=960x540`. In accepted pc_main.cpp the explicit size is parsed before the room check, then applied after saved settings and centered; nevertheless observed window dimensions/centering and terrain/squad remainPENDING. Record them before accepting the run. Keep stdout/session logs under this private package. No runtime was launched while host memory was about0.8GB.

1. Approach the closest replacement bulborb slot (about720units from Forest of Hope captain start). Observe the normal drop-in and press attacks; throw Pikmin onto the body and defeat it through ordinary combat.
2. During the actual death clip at source key2, observe one cluster of30 Mitites falling from the body. Natural terrain collision should trigger bounce/scatter/panic. Keep the boss on camera through the death clip.
3. Observe the boss vanish with no carcass. Any Mitites still within their natural lifetime must remain independent of boss removal; survivors may naturally dive before the boss clip ends, so distinguish Hide cleanup from a parent-triggered purge. Whistle the scattered squad, attack a Mitite, and observe its real death and nectar drop. Survivors should eventually dive and leave rather than follow a dead boss.
4. Check logs: one `P2_LONG_LEGS_BIRTH species=BigFoot ... count=30 requested=30`, one `P2_BIGFOOT_MITITE_GROUP ... count=30`,30 distinct member births, actual LAND events, later boss ESCAPE. No child campaign binding/extraAP checks. The boss's existing no-carcass kill check remains once.
5. Leave the scene and reenter after a fresh ordinary boss encounter; verify no stale child visuals, dangling leader pointers or inherited source bindings. A new boss actor may produce one new group, while completed actors never produce a second group.
6. Repeat with an actual held ship-part slot using the established #901 held-part transfer mechanism: the ship part drops through the generic death funnel and no Mitite group spawns. AP reward receipt alone should still allow the Mitite group.

Record executable SHA256, exact native/root commits, package/session paths, window/squad observation, encounter video/log and result. Fewer births under a full80-Teki pool are tolerated source allocation failures and logged honestly; they do not qualify the full30-member encounter.

Known port limits retained: the Mitite behavior remains the existing P1-backed family host; full source tumbling rotation while falling is not rendered. Natural combat/drop, held-part encounter and full campaign save/resume remain open until observed.


