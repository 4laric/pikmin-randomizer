# KingChappy Flick/trample runtime gate (#172 / #289)

Bounded lane-24 slice. Moves the Emperor Bulblax `Flick` / key-35 trample from
the runtime harness's optional/`untested` column to a required, deterministically
observed gate. Family parent [#172]; actor issue [#289].

## What changed

- Native `pc_port/pc_p2_king.cpp`: adds an opt-in fixture injection
  (`injectFlickTick`, 7th token of the existing `p2-king-inject.txt` sidecar).
  At the configured behavior tick it repositions the Emperor on the nearest
  live Pikmin (captain fallback when the squad has been eaten), enters `Flick`
  and sets the frame one before `FlickTrampleKey` (35) so the key-35
  `trampleScan` fires on the next 30 Hz behavior tick. Absent the sidecar the
  injection is inert; reset clears it. No production behavior or shared
  semantics change.
- Root `experimental/pikmin2_king_runtime.py`: adds required scenario 5
  (`P2_KING_SCENARIO_FLICK`) and moves `flick_trample` from `optional` to
  `required`, asserting both the `P2_KING_INJECT_FLICK` marker and a live
  press (`pressed_pikmin` or `pressed_captains` >= 1).
- Native custom fixture entrypoint `tools/preview_p2_room.cpp`: adopts the
  #404 window policy (`pc_fixture_window_size`, 960x540 default,
  `PIKMIN_P2_ROOM_WINDOW` override, `pc_window_center()` + standard log) so the
  replacement-main fixture has equivalent window behavior to `pc_main.cpp`.

## Ordered commits

Root branch `opencode/p2-lane24-king-flick` (based on `opencode/p2-batch5-bulblax`):

| Commit | Subject |
|---|---|
| `52c3340` | pikmin2: deterministic KingChappy Flick/trample runtime gate (#172/#289) |
| `2636961` | preview: inject a starting Pikmin squad into every private fixture stage (cherry-pick of `a51b301`, #404) |

Native branch `opencode/p2-lane24-flick-native` (based on `opencode/p2-batch5-actor-hooks` `e0ab01be`; never pushed):

| Commit | Subject |
|---|---|
| `a34276e7` | pc_port: opt-in King Flick/trample injection for deterministic receiver gate (#172/#289) |
| `f6f43fb8` | pc_port: open experimental-room windows small and centered by default (cherry-pick of `1d5a242b`, #404) |
| `57bb1a4e` | tools: adopt 960x540 centred window policy in custom room fixture entrypoint (#404) |

## Six arena gates (this slice)

| Gate | Status | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS | `P2_KING_READY id=230020 enemy=53 variant=default xyz=34,30,1896` |
| 2. Autonomous movement and animation | PASS | `P2_KING_APPEAR_TRIGGER`, `P2_KING_STATE 10->11`, `11->0`, sampled clip draw |
| 3. Attacks and receivers | PASS | `P2_KING_INJECT_FLICK ... state=Flick`, `P2_KING_TRAMPLE id=230020 pressed_pikmin=1 pressed_captains=0 flick_captains=1 range=45.0 band=30` |
| 4. Death and corpse | PASS | `P2_KING_INJECT_KILL`, `P2_KING_STATE ... to=2 health=0`, `P2_KING_DEAD_KEY frame=185` |
| 5. Actual transport and reward | source-backed N/A | Emperor Bulblax has no corpse/carry reward in this fixture; `P2_KING_SWALLOW` poison is the family-local outcome |
| 6. Cleanup and re-entry | PASS | `P2_KING_RESET_REQUEST`, `P2_KING_RELOAD_REQUEST`, reload `P2_KING_READY` (`reload_ready>=5`) |

Tongue/bomb/WarCry/cross-Emperor remain as previously accepted required checks;
no already-passed gate was re-run with unchanged inputs except as part of the
single bounded run below.

## Fixture baseline adoption (#404)

```text
Fixture baseline adoption
Child issue / lane / implementation owner: #172 / lane 24 (King flick/trample) / Codex via shared account 4laric
Root commit + dirty state / overlay source: opencode/p2-lane24-king-flick @ 2636961 (clean worktree output/p2-lane24-root). scripts/preview_pikmin2_room.py sha256 4abe0e950a1c7f137572d976ed62fd5a794c079683253a13bde8bfee47762a5a; ensure_pikmin_squad present (cherry-pick of a51b301).
Native commit + dirty state / worktree / private build directory: opencode/p2-lane24-flick-native @ 57bb1a4e18d75396e2cfef6652447f36f44c0464 (clean), worktree output/p2-kimi-bulblax-native, build output/p2-kimi-bulblax-native/build-king.
Squad change present / window change present (ancestry or source evidence): overlay ensure_pikmin_squad present in root 2636961; window 1d5a242b cherry-picked as f6f43fb8 and the custom fixture entrypoint adopts the same policy as 57bb1a4e. Both marker sources verified; the fixture had an explicit 5-red/5-blue squad so the overlay did not top up.
Fresh arena command / run directory / asset and config hashes: py -3.12 -m experimental.pikmin2_king_runtime run --assets C:\Users\alari\bbft\dist\cohesion\pikmin\assets --bank output/bulblax-bank2-run1 --output output/p2-lane24-flick-runtime-02 --exe output/p2-lane24-flick-fixture-03/build/fixture.exe -> output/p2-lane24-flick-runtime-02/king/f0dc0ff1017a45a9a631ad73a86afff6. king-stage.json sha256 c35419cc55f01b834afdedb061efa49c5d13be13d672f862519400016afa353a; config_sha256 c7d8b0bca9aa0212f7a403e47dd812341425d9f587e213154d70d9d8af767aac; course practice.mod 873abade86d4fb7f40633993c206a5a97ebcccf3b756a5f783fb031908f2ee0a.
Executable SHA-256 / fixture provenance status if applicable: fixture.exe 47c3a82560084942a9865b2ac68335ee2f43a8a2a1f66e5860989043caa54de1; provenance.json status=built; expected_native_head=57bb1a4e...; freshness checks ninja no-work x2. pikmin_pc nectar.exe built in output/p2-kimi-bulblax-native/build-king.
Window setting / observed size and centring evidence: PIKMIN_P2_ROOM_WINDOW=960x540; native.log "[PC Port] Experimental preview window set to 960x540 windowed and centered (override with PIKMIN_P2_ROOM_WINDOW=WxH or =off)." via pc_window_center() in the fixture entrypoint.
Live starting Pikmin / active gameplay / no immediate extinction evidence: P2_KING_BASELINE red=5 blue=5 at start; guard against zero census active; PASS P2_KING_ACTOR_RUNTIME bounded_behavior_tick; no extinction screen. (gameover.blo appears only as a DVDOpen asset load.)
PASS, FAIL, or BLOCKED; remaining work: PASS for the bounded flick/trample gate. Natural (un-injected) Flick accumulation from live Pikmin blows, full material/BTK fidelity, mixed-scene performance and campaign re-entry remain open (#239/#128).
```

## Natural (un-injected) Flick/trample gate

The bounded gate above used the opt-in Flick injection. The remaining natural
path is now demonstrated by `experimental/pikmin2_king_natural_flick_runtime.py`:
the intact 5-red/5-blue squad is staged around the buried Emperor and **no**
`p2-king-inject.txt` is present (the harness removes it and aborts if it
reappears). The actor's own `receiveScan` accumulates stuck Pikmin, its natural
`checkFlick` selects `Flick` at full health, and the key-35 `trampleScan` presses
live Pikmin. The only staging is the labeled per-tick re-pin of the live squad
into a ring around the spawn; there are no bombs (the harness rewrites the
profile bomb-free) and no Flick/kill injection.

Run `output/p2-lane24-natural-runtime-03/king/1e370da8c1fd4cfeadee7e1f0d194c34`
(fixture SHA-256 `8dea2537fc22a0f85ef7ecd9675fdf0234f669043ed47a519b7f9f06a942ab7e`,
provenance status `built`, expected native head `57bb1a4e`), validator all-true
(`completion`, `baseline`, `ready`, `no_injection`, `natural_check_flick`,
`natural_trample`, `natural_flick_state`, `no_rewards`):

```text
P2_KING_NATURAL_ARMED no_injection=1
P2_KING_APPEAR_TRIGGER id=230020 nearest=30.000 range=60.0 waited=1
P2_KING_CHECK_FLICK id=230020 health=1290.0 max=1300.0 roll=0.778 shout_rate=0.5 next=3
P2_KING_TRAMPLE id=230020 pressed_pikmin=7 pressed_captains=0 flick_captains=1 range=45.0 band=30
P2_KING_STATE id=230020 from=3 to=0 health=1280.0
PASS P2_KING_NATURAL_RUNTIME natural_flick_trample
```

`next=3` is the natural Flick selection; the trample then presses 7 live Pikmin.
This closes the "natural un-injected Flick accumulation from live Pikmin blows"
item for the bounded fixture; material/TEV/BTK fidelity (#239/#128) and campaign
lifecycle remain open.

## Scope boundary

The injection is a fixture channel, labeled in every log line, and does not run
without `p2-king-inject.txt`. This does not complete the family: natural combat,
material/TEV/BTK fidelity, and campaign lifecycle remain with #172/#239/#128.
