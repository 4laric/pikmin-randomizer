# Reward beetle natural press receiver (lane 17, #168/#219)

Implementation owner: Codex through shared account `4laric`. Executing agent:
DeepSeek (`deepseek/p2-l17`), 2026-09-14. Completes the smallest missing end-to-end
slice for the reward-beetle family: the **natural press receiver**. The accepted
batch-4 behavior fixture (`docs/PIKMIN2_KOGANE_ARENA.md`,
`experimental/pikmin2_kogane_behavior.py`) drives flips/drops/escape with *injected*
`InteractPress` stimuli; this slice removes that injection and proves a real Pikmin
attack drives the finite flip/drop/escape cycle on the P1 host.

## Source ID and gate addressed

- **Source ID: 9 Kogane (Iridescent Flint Beetle)** — canonical first identity.
- **Gate: natural combat / receivers** (the family's "attack" is the flip-on-press
  from a Pikmin landing; there is no health damage or corpse).
- The remaining gate (real collection/Onion transport) is left honest as unmeasured;
  see the gate table.

## Native change (worktree `output/dsw/native-l17`, branch `deepseek/p2-l17-native`, @ `14e88cc3`)

`pc_port/pc_p2_kogane.{h,cpp}`. The source flip trigger is a Pikmin stomp/hipdrop
(Kogane.cpp `pressCallBack`/`hipdropCallBack`/`earthquakeCallBack`). The P1 host has
no distinct stimulus for a Pikmin landing on a beetle: a thrown Pikmin's landing is
the C-stick stick-attack, which reaches the engine as `InteractAttack`. Before this
slice `pc_p2_kogane_attacked` merely swallowed that attack (no damage, no flip), so a
registered beetle could never be flipped naturally. Now:

- `pc_p2_kogane_attacked` routes a landed attack to the flip via a shared `doFlip`
  entry, emitting `P2_KOGANE_NATURAL_ATTACK generator=<id> source_id=<id> flip=<n>`.
  It still applies no health damage (source: only the press affects a beetle).
- `pc_p2_kogane_pressed` (the historical `InteractPress` path) now shares the same
  `doFlip`; its `P2_KOGANE_FLIP` log is unchanged, so the batch-4 fixtures stay green.
- A new `recoverTimer` (the full 50-frame damage clip) holds further presses/attacks
  until the damage animation completes, so a continuously-stuck Pikmin flips at most
  once per damage clip (source `NoInterrupt` at damage.bca KEYEVENT_2..4) instead of
  draining all three flips on consecutive frames. The third flip still forces the
  source escape, and the finite cap / on-disk receipts / corpse suppression are
  unchanged.

The only shared-file touch is the pre-existing `InteractAttack::actTeki` hook call to
`pc_p2_kogane_attacked` in `src/plugPikiNakata/tekiinteraction.cpp` — unchanged this
slice, since that call was already wired in the maintained native line.

## Runtime fixture (root worktree, `experimental/pikmin2_kogane_natural.py`)

A new fixture/validator module mirroring the batch-4 parameterized fixture. It stages
the same P1 Impact Site arena + beetle bank + `P2_KOGANE_NATIVE_1` sidecar, then a
private `RoomApp` issues the engine's own C-stick transition —

```cpp
p->mActiveAction->abandon(nullptr);
p->mActiveAction->startAction(PikiAction::Attack, beetle);
p->mMode = PikiMode::AttackMode;
```

— which is exactly what `piki.cpp` runs when the player releases a Pikmin at a target.
The approach, attack-animation timing and the `InteractAttack` stimulus are the
Pikmin's own AI; the flip, frame-7 drop, finite cap and escape are all native. The
fixture never calls `stimulate`/`eventPerformed`, verified by
`tests/test_pikmin2_kogane_natural.py` (`test_instrument_splices...`).

Intervention (labelled, not an injected interaction): the observing squad is pinned
clear of the drop zone so drops persist for the census, and up to five attackers are
co-located near the wandering beetle and re-queued (no teleport) when one falls out of
`AttackMode`, guarded so a drinking Pikmin (`PIKISTATE_Absorb` / `mCurrNectar`) is
never interrupted (this was the cause of an earlier `mizunomi err!` panic in the
first attempt). The beetle, drops and escape path are all driven natively.

## Accepted run

- Native commit `14e88cc33e91a2847bd3e496f4705040184f14ee` (clean), built with
  `PIKMIN_NATIVE_JAUDIO=ON`; `nectar.exe` SHA-256
  `2829048967b3a754fb3dabd9b3839b0bf0e8ced526f20ef385c43bbfad0299fa`, `ninja -n`
  "no work to do".
- Fixture `output/dsw/l17-out/natural-fixture/fixture.exe` SHA-256
  `27dba46398fb464a72bcdc0d5630fe10951ce3a70cc7926e78d249e1bf9dbacc`, `status: built`.
- Run `output/dsw/l17-out/natural-run/stages/1d8b02c97210472db021d6338f8b4146`.
  Startup: `SDL2 Window & OpenGL Context initialized successfully (960x540)` +
  `Experimental preview window set to 960x540 windowed and centered`; 20 red Pikmin
  live; no extinction. Exit 0.

Markers (native.log line refs are approximate):

```
P2_KOGANE_BIRTH id=219001 type=3 x=-150.000 y=30.000 z=1850.000
P2_KOGANE_NATURAL_ATTACK generator=219001 source_id=9 flip=1 (then 2, 3)
P2_KOGANE_DROP generator=219001 source_id=9 flip=1 pellet1=1 nectar=0
P2_KOGANE_DROP generator=219001 source_id=9 flip=2 pellet0=0 nectar=2
P2_KOGANE_DROP generator=219001 source_id=9 flip=3 pellet0=0 nectar=3
P2_KOGANE_ESCAPE generator=219001 source_id=9 flips=3
P2_KOGANE_NATURAL_CENSUS pellets=4 nectar=9 pikis=20
PASS P2_KOGANE_NATURAL natural_attack flip3 escape1 control_alive
```

The neighbouring Wealthy (219002) was also naturally pressed to its own three-flip
escape (the attackers re-targeted to the nearest enemy after Kogane's final damage
clip); this is honest natural behaviour and does not mask Kogane's clean sequence.

## Six arena gates

| Gate | Result | Evidence / label |
|---|---|---|
| 1. Exact identity and spawn | PASS | `P2_KOGANE_BIRTH` ×4 exact stored XYZ; `P2_KOGANE_BIND source_id=9` karada 60; native draw logged |
| 2. Autonomous movement/animation | PASS | wander driver + pose bank already accepted (`docs/PIKMIN2_KOGANE_ARENA.md`); unchanged |
| 3. Attacks and receivers | **PASS (natural)** | `P2_KOGANE_NATURAL_ATTACK` ×3 on 219001; real Pikmin `InteractAttack` → flip; no injected stimulus |
| 4. Death and corpse | PASS (source-backed N/A corpse) | 3rd flip → `P2_KOGANE_ESCAPE`; beetles burrow away, no corpse pellet (source-faithful) |
| 5. Actual transport and reward | UNTESTED (spawns proven) | drops are real `Pellet`/`OBJTYPE_Water` (`P2_KOGANE_DROP` + census); carry-to-Onion collection not observed |
| 6. Cleanup and re-entry | PASS | reset/re-entry + on-disk receipts accepted earlier (`docs/PIKMIN2_KOGANE_REWARDS.md`); full scene/day reload still uncovered |

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_kogane_natural.py -q` → 7 passed.
- Full lane-17 suite `tests/test_pikmin2_kogane_*.py` → 116 passed, 11 subtests.

## Remaining (not claimed here)

- Real carry-to-Onion collection of the dropped pellets/nectar (lane 06 reward
  endpoint); the drops persist in the arena but transport was not driven.
- Cave treasure override and cave relocation (`Cave::randMapMgr`) — no P2 cave in the
  P1 host; the first-flip treasure is a labelled P1 number-pellet stand-in.
- Full scene/day reload and P2-save bridge (lane 01/06).

## Reproduction command

```powershell
py -3.12 -m experimental.pikmin2_kogane_natural build `
  --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l17 `
  --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l17-build `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/natural-fixture `
  --head 14e88cc33e91a2847bd3e496f4705040184f14ee
py -3.12 -m experimental.pikmin2_kogane_natural run `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --bank C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/bank `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/natural-run `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/natural-fixture/fixture.exe
```

(The `run` step opens a real-GL window and must be wrapped by the host `gl` slot; the
`--bank` is regenerated from `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso` via
`py -3.12 -m experimental.pikmin2_kogane_assets --iso <iso> --output <bank dir>`.)
