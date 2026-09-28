# Snow health policy (#120)

This optional experimental policy gives registered Snow Bulborbs their source
Pikmin 2 maximum and initial health of 150. Their combat state machine, attack
timing and movement remain the native Pikmin 1 Chappy implementation.

## Source and contract

The local retail archive `enemy/parm/enemyParms.szs`, member
`yellowkochappy/enemyparm.txt`, has general parameter `fp00 = 150`.
`native/pikmin2-research/include/Game/EnemyParmsBase.h` identifies this as health;
`YellowKochappyMgr.cpp` allocates the KochappyBase parameters. The extractor keeps
parameter groups separate because IDs repeat across groups. It records source
hashes and animation events in a local JSON report, without distributing assets.

Extract to a new private directory:

```powershell
py -3.12 -m experimental.pikmin2_snow_policy --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --output output/my-snow-policy
```

After installing a Snow bank into a private run directory, call
`experimental.pikmin2_snow_policy.install(imported, run)` with Path objects.
The run must contain `p2-snow.txt` and `p2-snow-actors.txt`. The optional
`p2-snow-policy.txt` is exactly:

```text
P2_SNOW_POLICY_1
health 150
```

No file preserves existing behavior. Invalid policies fail closed. This is not
an arbitrary health tuning interface and is not enabled by existing launchers.
The native actor registration changes initial health and its TPF_Life query,
which also supplies health gauge and regeneration limits. Family parameters are
never changed; unregistered P1 actors return their original parameter value.
Do not assume that fallback is 100: installed P1 assets can override defaults.

## Animation mapping evidence

The retail `kochappy/enemyanimmgr.txt` and KochappyBase source specify:

| Source clip | Source events | Current proxy rendering |
|---|---|---|
| attack | frame 8 attack/eat; frame 88 swallow | P1 attack motion 8 |
| dead | animation end drives death transition | P1 death motion 0; corpse holds last pose |
| flick | frame 31 flick | P1 flick motion 9 |
| move1 | loop frames 10–39 | horizontal velocity selects movement |
| wait1 | loop frames 10–60; frame 61 notice | stationary fallback |
| type1 | press | unmapped |
| type5 | carry; loop frames 10–29 | unmapped |
| waitact1 | turn; loop frames 6–19 | unmapped |
| waitact2 | eat | unmapped |

`src/plugProjectYamashitaU/kochappyState.cpp` consumes those attack/flick events;
`SysShape/KeyEvent.h` defines loop markers 0 and 1. The current renderer selects
sampled source poses using normalized P1 animation phase. This policy does not
apply source event timing or implement P2 eating, pressing, turning or carrying
states. The extraction report retains all nine clips, including unmapped ones.

## Registry lifetime

Actor identity is process-local. Snow setup and actual manager reset clear the
registry. The manager constructor resets only when the global manager pointer is
null; an unrelated live manager is not cleared. The instance reset is likewise
restricted to the global manager. Static initTekiMgr clears alongside its global
pointer reset. A successful newTeki birth forgets a reused actor address before
initialization, preventing inherited Snow health and visuals. Death does not
forget the actor: corpse identity remains available until slot reuse.

Source gameCoreSection explicitly clears tekiMgr before constructing the next
stage manager. These guards do not add scene teardown ownership or delete actors.

## Validation and remaining work

The focused policy, animation and enemy suites pass: 36 tests. The policy suite
includes a compiled C++ probe for absent-file fallback, separate P1 and Snow
actors, reset, address reuse, individual forget preserving other actors, and
invalid-policy rejection. Real local retail extraction confirmed health 150 and
all nine event entries. Modified pc_p2_enemy.cpp and tekimgr.cpp compiled in an
isolated output directory using production flags.

A full native rebuild and runtime check of initial/max health remain required:
the inline getter affects every native caller. Existing Snow lifecycle playback
predates this health change and does not validate it. Verify a registered Snow
has initial/max 150, an unregistered same-family actor keeps its own parameter
value, and a run without the optional policy keeps prior behavior. No shared
binary or live seed was replaced by this batch.
