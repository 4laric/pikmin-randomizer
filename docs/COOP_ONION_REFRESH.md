# Live co-op Onion capacity

Issue #1108, owner Codex through shared account 4laric.

Unpaused co-op Onion menus refresh available stock, eligible owner squad and
field use including queued withdrawals each simulation tick. Their pending
selection shrinks toward zero when it becomes invalid. Confirmation checks
again after the closing animation, so a captain who reserves the final slots
can safely reduce the other captain's transfer to zero. Menus never turn a
withdrawal into a deposit. Singleplayer's paused menu path is unchanged; VS
retains its existing owner-specific actors, heads and pending-exit budget.

The manual smoke is a disposable injected UI scenario. It starts with 20 live
Reds and the retail scene's sprouts, grants spare Onion stock, and uses native
queued births to fill the authoritative 30-body limit. Both real menus open.
Staged deaths, stock changes and further queued exits change free space while
they remain open. These are test mutations, not natural campaign progression.

Connect a controller for P2, then run:

```powershell
py -3.12 scripts/play_coop_onion_smoke.py
```

P1 W/S selects transfers; Space confirms and Shift cancels. P2 uses
its stick and A/B (Cross/Circle). Watch the available counts and withdrawal
limit change while the world runs. Closing the game or the 60-second bound
ends the private attempt; rerun for a fresh reset. Saves and state stay under
ignored output. The manual smoke has no network sockets and remains unlaunched
until the user runs it. Human readability/input judgment is separate from the
automated proof and does not admit P2 gameplay or full campaign resume.

The scripted visible startup explicitly sets TEST_BACKGROUND=2: native auto-withdraw supplies20; only the exact value1 hides the window. This test staging does not alter normal campaign starts.
