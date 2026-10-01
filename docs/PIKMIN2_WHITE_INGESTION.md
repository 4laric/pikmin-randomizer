# Ordinary White ingestion acceptance

Implementation owner: Codex through shared account `4laric`, [issue1120](https://github.com/4laric/pikmin-randomizer/issues/1120), child of #395/#131. This adds only a reproducible fixture and private runner. Production files are unchanged from native `2e6efbb1b841c1889d1bbd3b656e44ba6ae3629b`.

## Observed slice

Native `d562f7b369aec4d20117f395f13cee9a2e0b3b9b`, fixture08, fresh positive `output/white-ingestion/run-positive-2e484f74e5` exited0 in39.531 seconds. The scene began with20 Reds, one Ivory and one explicitly registered native P1 adult `TEKI_Swallow` mechanics adapter. Real SDL P1/native polling performed whistle, ordinary Red-to-White birth, Red dismissal (Release4 to Walk0), player pluck, movement, throw and retreat. The White was observed alive attached to the predator's mouth before ordinary native consumption.

The production callback logged exactly one `P2_WHITE_POISON_CONSUMED damage=750.000 queued_health=1016.843`. The fixture next observed HP267.026 and19 Reds/zero Whites/19 bodies. Starting HP was1100, from the ordinary loaded native adult parameters; White melee damage and native recovery preceded consumption. The queued750 is the P2 Chappy proper `fp02`; the remaining HP includes normal native regeneration. Neither the fixture nor runner writes HP, White identity, mouth attachment, swallowing events, callbacks, budgets, rewards or conversion timers. The predator survived (`death=0`); lethal poison and corpse creation are untested in this ordinary run.

Same executable fresh negative `run-negative-2149b020c6` exited86 with no success marker. The canonical three-signal captain guard runs immediately after engine idle and before startup/movie/pause/readiness returns; missing initialized captain/state and independent health/dead signals fail. Its negative-only helper input is disclosed and does not alter production health. Supplemental `naviMgr->isNaviDead(n)` observation/negative control is a future fixture enhancement; the accepted08 guard already checks the three mandatory fan-out signals.

## Source and staging

The poison profile is extracted from local legal `assets/disc/PIKMIN2 for GAMECUBE.iso`: archive SHA256 `3618455a8561f1e1b0aad0253a75a69fae1fe3a47160d1c1efa294b0ddeb2a84`, member `12abc387cf05d4bf2c53f453694a268bec4d00e4fee33b03626d0d071b0f80c4`, config `af9e979e3a7b48212c871797b45adbbaa8217b77ff43ad51116a30a4680fbd20`. Generator ID436207616 binds that profile to one existing native adult. This proves the opt-in P2 poison adapter with a native host, not imported P2 adult presentation or complete P2 adult AI/HP fidelity.

Fresh current20 Red generator overlay, ordinary native ENTRY2 starting-squad restoration, imported room collision, Ivory/White/Pod banks, staged enemy placement, movie skips, tutorial flags and dummy audio are setup interventions. The predator spawns through the normal generator and may move from its staged coordinates. Source assets are preserved through replacement files in the private overlay. The window is960x540 centered; canonical supervisor bound is60 seconds. No manual CUA or human feel approval is claimed; a manual ingestion scene should be offered only after its separate ready/setup path is validated.

Reproduce using private fixture08 executable and local banks:

```powershell
py -3.12 scripts/run_p2_white_ingestion.py --workspace C:/Users/alari/pikmin-randomizer --exe C:/Users/alari/pikmin-randomizer/output/white-ingestion/fixture-08/fixture.exe --assets C:/Users/alari/AppData/Roaming/PikminRandomizer/game-data/assets --white C:/Users/alari/pikmin-randomizer/output/white-ivory-budget/white-bank-01 --pod C:/Users/alari/pikmin-randomizer/output/cave-930-resume/pod --room C:/Users/alari/pikmin-randomizer/output/white-acquisition/room-converted --poison C:/Users/alari/pikmin-randomizer/output/white-ingestion/poison-bank-01
# Add --negative for the fresh guard refusal.
```

## Preserved failures and limits

Fixture01-03 dependency scans refused a redundant nonexistent header before any runtime; fixture04 corrected it. Positive c65925b3f5 reached a White sprout but timed out on held-X dismissal; a251987770 showed Idle17 (not Release4) after a Walk-only pulse predicate;03993dd5bd dismissed successfully but stopped too far from the head;6a72c0ad24 plucked successfully but exposed a fixture phase7 movement omission. These are failed history, not acceptance. The final fixture uses the previously accepted immediate-birth dismissal and15-unit pluck approach, with the phase mapping corrected.

Existing #1103/#1111 acquisition/refund/checkpoint artifacts are immutable. This bounded ordinary nonlethal ingestion slice leaves unsupported predator families, failed-kill/invulnerability/replay/reuse natural scenarios, lethal poison/corpse/reward conservation, gas immunity, buried treasure, ship/day-save storage and full campaign support open. Earlier injected poison contract tests remain separate evidence.
