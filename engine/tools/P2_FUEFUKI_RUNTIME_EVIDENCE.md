# Pikmin 2 Fuefuki — whistle-path runtime evidence against retail assets (#245)

Status: **executed, PASS**. All `P2_FUEFUKI_RT_*` markers below were produced
by an actual real-GL run of the lane fixture against the retail-derived
asset tree and the converted Pikmin 2 room arena. Nothing on this page is
simulated from the mock-host policy fixtures.

## Scope (what is real here, what is not)

Real in this run:

- the frozen P1 host booted with `--experimental-pikmin2-room` on a real
  SDL2/OpenGL 3.3 window (first GX draw logged, GL status 0x0000);
- a real captain (`naviMgr->getNavi()`) and six real `pikiMgr->birth()`
  Pikmin with real positions on the converted room collision;
- the lane-owned `pc_p2_fuefuki_binding.h` seam driven with host adapters
  implemented over **real engine queries**: the squad scan iterates the
  real `pikiMgr` with XZ distance from real `mSRT.t` positions, alive/mode
  reads are real;
- the captain-whistle reclaim executed through the **real P1 whistle
  path** `Navi::callPikis` (native/src/plugPikiKando/navi.cpp:1141) after
  the lane interception accepted; the resulting `PIKISTATE_LookAt` transit
  and the real formation join (`mMode == PikiMode::FormationMode` 20
  frames later) are engine behavior, not fixture writes.

Mock-only / not covered (unchanged from `P2_FUEFUKI_BINDING.md` gaps):

- no Fuefuki beetle actor exists; the anchor is a policy-side position;
- no Fuefuki visual/audio assets;
- P1 has no follow-teki action, so follow **locomotion** stays
  policy-fixture-only (the claim/release bookkeeping and non-routing are
  real here);
- P1 has no verified panic state: released followers stay in
  `PIKISTATE_Normal`; the reclaim is verified through the real whistle
  gather instead.

## Environment and build

- Host: Windows, MinGW-w64 g++ 16.2.0 (`C:/msys64/mingw64/bin` on PATH),
  ninja at
  `C:/Users/alari/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0/LocalCache/local-packages/Python312/Scripts/ninja.exe`.
- Native lane branch `codex/pikmin2-room-preview`, HEAD
  `e3079bdab64b4db03c806e7bcc256f05c714c789` (fixture commit). Parallel
  lanes share this branch; only Fuefuki files were touched by this slice.
- Isolated fixture build (verifies HEAD == expected, ninja freshness,
  records git state; output dir must not pre-exist):

  ```
  python scripts/build_pikmin2_fixture.py \
      --build native/build-randomizer --source native \
      --fixture native/tools/p2_fuefuki_runtime.cpp \
      --output output/fuefuki-runtime-fixture-03 \
      --expected-native-head e3079bdab64b4db03c806e7bcc256f05c714c789
  ```

  Result: `{"status": "built", ...}`; provenance in
  `output/fuefuki-runtime-fixture-03/provenance.json`. Two earlier output
  dirs (`-01`, `-02`) are superseded iterations of the same fixture.

## Staging and run (verbatim commands)

```
python -c "import sys; sys.path.insert(0,'scripts'); from pathlib import Path; from preview_pikmin2_room import prepare; print(prepare(Path('C:/Users/alari/pikmin-local/game/assets'), Path('output/pikmin2-room105').resolve(), Path('output/fuefuki-arena-preview')))"
# -> C:\Users\alari\pikmin-randomizer\output\fuefuki-arena-preview\a1037a2f12c448558547aeabe028c43a

cd <printed run dir>
cp C:/Users/alari/pikmin-randomizer/output/fuefuki-runtime-fixture-03/fixture.exe .
./fixture.exe --experimental-pikmin2-room > run.log 2>&1   # exit=0
```

Assets: retail-derived tree at `C:/Users/alari/pikmin-local/game/assets`,
converted room at `output/pikmin2-room105` (both gitignored local state;
no disc data committed).

## Retail parameters used

fp01 maxGroundTime = 20.0, fp02 minGroundTime = 10.0, fp12 re-cast
interval = 3.0, fp21 struggleTime = 2.5, attackRadius (whistle ring) =
130, private radius = 60 (probe distance check), health tick input = 700 /
0. From the engine lane disc extraction
(`docs/PIKMIN2_ENGINE_DISC_PARMS.md`); fp11/fp13/fp03/fp22/fp31 were not
in the extraction batch and keep header defaults.

## Marker output (verbatim from run.log)

```
P2_FUEFUKI_RT_READY squad=6 ring=130 private=60 fp12=3.0 fp01=20 fp21=2.5 health=700 no_beetle_actor=1 no_visual_assets=1
P2_FUEFUKI_RT_SCAN claimed=3 outside=0 radius=130.0 squad_active=1 real_pikimgr=1
P2_FUEFUKI_RT_NONROUTE whistle=0 switch=0 combine=0 held=3 writes=0 live_beetle=1
P2_FUEFUKI_RT_DEATH released=3 reason=panic committed_before_callback=1
P2_FUEFUKI_RT_RECLAIM id=1 writes=1 real_callPikis=1 state=26 navi_match=1 outside_untouched=3
P2_FUEFUKI_RT_FORMJOIN id=1 mode=1 frames=20
P2_FUEFUKI_RT_KILL carcass=carry_anim
PASS FUEFUKI_RUNTIME
```

Phase detail:

- **READY** — 6 real red Pikmin birthed: ids 1–3 inside the 130 ring at
  70–90 units from the anchor, ids 4–6 outside at 220–260; captain staged
  at z = 300 (outside the 60-unit private radius). Fresh births default to
  the captain's formation in this engine (`init(navi)` sets `mNavi`), so
  the fixture explicitly stages them `PikiMode::FreeMode` to own the
  baseline the seam must not disturb.
- **SCAN** — the lane scan over the real `pikiMgr` claimed exactly the 3
  inside-ring Pikmin, none outside; the retail ring grew to its full 130.0;
  the per-tick ping from real alive followers kept the squad active.
- **NONROUTE** — while the (policy-side) beetle is live, captain whistle,
  captain switch and party combine all refuse to route to held Pikmin; no
  ownership write fired; the held Pikmin's real `mMode` stayed at the
  recorded free-roam baseline and never entered `FormationMode`.
- **DEATH** — health 0 routed to `Dead`; exactly 3 panic releases, each
  observed already committed in the ownership table before `followEnd`
  ran.
- **RECLAIM / FORMJOIN** — `onCaptainWhistle(1, 0)` accepted exactly once
  (single ownership write; second call rejected), then the REAL
  `Navi::callPikis(140)` gathered the released follower: `mNavi` rebound
  and `PIKISTATE_LookAt` (state 26) entered immediately, real
  `FormationMode` (mode 1) reached 20 frames later. The 3 outside-ring
  Pikmin were untouched by the real whistle.
- **KILL** — dead-anim END delivered `kill` + `carcassCarryAnim` through
  the seam exactly once.

## Standalone lane fixtures (re-run this slice)

```
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_interference_policy_test.cpp -o ../fuefuki-policy-test.exe   # PASS
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_fsm_test.cpp -o ../fuefuki-fsm-test.exe                         # PASS
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_binding_test.cpp -o ../fuefuki-binding-test.exe                 # PASS
g++ -std=c++17 -Wall -Wextra -Werror -Iinclude -Ipc_port -c tools/p2_fuefuki_native_compile_check.cpp \
    -o ../output/fuefuki-binding/p2_fuefuki_native_compile_check.o                                                              # compiles clean
```

All from `native/` with MinGW64 on PATH; warning-clean under `-Werror`.

## Remaining gaps

Everything in `P2_FUEFUKI_BINDING.md` "Gaps" still stands: beetle actor,
visual assets, follow locomotion, and a true panic-state staging remain
open and are tracked by the lane. This slice closes the "no real-GL
runtime evidence for the binding seam" gap only.
