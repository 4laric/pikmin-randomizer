# Compact co-op radar menus

Issue #1102; implementation owner Codex through shared account 4laric.

On the co-op/netplay playtest branch, each player's map/count/control menu now
fits a 4:3 corner panel. Real split menus are 30% smaller linearly and remain in
the owning half, including horizontal splits and swapped sides. Online peers
render their own world fullscreen; their two panels use outer upper corners
with 40% width/44% height bounds, leaving the common center clear. Unified local
cameras use the same fullscreen layout. Normal singleplayer drawing is unchanged.

The change preserves menu input, update, draw count/order, player radar identity,
simulation, zoom/pan and saves. It restores the radar index, UI4:3 flag and
projection offset, then returns to the existing full viewport/scissor contract.

For a fresh local smoke, connect a controller for P2 and run:

```powershell
py -3.12 scripts/play_coop_radar_smoke.py
# Repeat in the other split orientation:
py -3.12 scripts/play_coop_radar_smoke.py --orientation horizontal
```

This directly boots a disposable Impact Site day 2 co-op session with 20 Reds. It grants only the Whimsical
Radar checked slot 4 (mask 16) for this visual check; progression is synthetic
and stays in the disposable session. P1 keyboard
Y and P2 controller Y/triangle open the menus; Shift/B/circle closes them. Try
each menu and both together, move captains apart, and check the OTHER player's
center stays clear. Judge label readability and radar zoom/pan. Closing the game
or the 90-second bound ends the attempt; rerunning creates a fresh private session.
The local smoke opens no network sockets. Startup movie/ordinary UI behavior is
unchanged; dismiss those with normal controls if they appear.

For online testing, both peers must use the identical separately packaged radar
build and existing host.bat/join.bat scripts. Test the same menu combinations in
each fullscreen peer. Existing 58c0fed packages stay unchanged. This presentation
slice does not admit any P2 gameplay or infer human readability approval.
