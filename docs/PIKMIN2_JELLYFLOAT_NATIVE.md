# Jellyfloat / Kurage (Lesser Spotted Jellyfloat, EnemyID 57) native source behavior

Issue [#243](https://github.com/4laric/pikmin-randomizer/issues/243). Taken over
from the completed `codex/p2-jellyfloat-kurage` lane and integrated into the
species lane branch (`opencode/p2-species-native` @ `4597eaee`). Owner: Codex via
shared `4laric`.

## What was integrated

The Kurage lane delivered a source-faithful FSM plus a bounded host/receiver,
verified by standalone policy tests and an instrumented automatic-binding
runtime fixture:

- `pc_port/pc_p2_kurage_fsm.h` — fixed-step transcription of all eleven
  `KurageState.cpp` states (`Dead, Wait, Move, Chase, Attack, Fall, Land, Ground,
  TakeOff, FlyFlick, GroundFlick`), composing `pc_p2_kurage_flight_policy.h`.
- `pc_port/pc_p2_kurage_flight_policy.h` — source flight/suction numerics
  (climb velocity, pitch keyframes, fall timer, `getFlyingNextState`, scan and
  suction-admission geometry).
- `pc_port/pc_p2_kurage_receiver.cpp/h`, `pc_p2_kurage_digestion.h` — bounded
  receiver/ingestion host.
- `pc_port/pc_p2_kurage_teki.cpp/h`, `pc_p2_kurage_visual.cpp/h`,
  `pc_p2_kurage_arena.cpp/h` — binding/draw/arena adapters.
- `pc_port/pc_p2_motion_events.h`, `pc_p2_retail_player.h` — bounded retail
  motion/event player used by the host clock.
- Additive hooks in `pc_window.{cpp,h}`, `src/plugPikiKando/creature.cpp`,
  `gameCoreSection.cpp`, `piki.cpp`, `src/plugPikiNakata/tekibteki.cpp`,
  `tekimgr.cpp`, `pc_p2_preview.cpp`, `CMakeLists.txt`.
- `tools/` policy docs and standalone tests.

Source: revision `632af93787b9c95b63f0c13be32b161375ce3a96`
(`Kurage.cpp`/`KurageState.cpp`, `Kurage.h`).

## Verification after takeover

- Integrated build (`output/native-species-jelly2-build`, Ninja, MinGW 16.2.0,
  Release, JAudio ON): `[534/534] Linking CXX executable bin\nectar.exe`;
  `ninja -n` → no work to do.
- Standalone policy tests: `p2_kurage_fsm_test PASS checks=35` and
  `p2_kurage_flight_policy_test PASS checks=35`.
- Runtime fixture rebuilt against the integrated source via
  `scripts/build_pikmin2_fixture.py` (`output/kurage-jelly2-fixture-01`,
  provenance `status=built`, fixture SHA-256
  `94101B04…8AF2E0505`), then run:
  - `P2_KURAGE_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1`
  - `[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`
    (live 20-red starting squad present)
  - `P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter`
  - `P2_KURAGE_AUTO_BIND_PASS generator=201001 type=0
    source=GameCoreSection::finalSetup sidecar=p2-kurage-teki.txt
    direct_bind_calls=0`
  - `returncode: 0` (`output/kurage-jelly2-run-01/automatic-binding.json`;
    log SHA-256 `42B9C8C9…45529B`).

## Gate status

| Gate | Result | Evidence |
|---|---|---|
| Identity + spawn/binding | PASS | `P2_KURAGE_TEKI_READY` / `P2_KURAGE_AUTO_BIND_PASS` at `GameCoreSection::finalSetup` |
| Window + squad baseline | PASS | 960×540 centered=1; `red=20` |
| FSM + flight/suction policy | PASS (unit) | 35 + 35 standalone assertions |
| Attack / suction receiver | implemented + policy-tested | FSM/policy; no natural-play capture run |
| Ingestion / digestion lifecycle | bounded host | `pc_p2_kurage_receiver`/`digestion.h`; full stomach-timer/captain-release lifecycle UNTESTED |
| OniKurage (#72) | not implemented | shared-base Greater variant remains open |
| Material / opacity fidelity | UNTESTED | `kurage` material/opacity |

## Notes / coordination

- This branch modifies shared semantics (`creature.cpp`, `piki.cpp`,
  `gameCoreSection.cpp`, `pc_window.*`); per the fan-out those edits need
  focused #186 review before the maintained build/export.
- A visible/extinction-free runtime capture of the suction lifecycle, the
  Greater Spotted Jellyfloat, and the full stomach-timer release paths remain
  open.
