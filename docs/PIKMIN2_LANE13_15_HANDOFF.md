# Lane 13/15 integration handoff (2026-09-14)

Owner: Codex via shared account `4laric`. Executing agent/session: opencode
(deepseek-v4.1-flash). Coordination #186; lane parents #120 (13), #166 (15).

This consolidates the lane-13/15 native candidates and root tooling for lane 01.
Root branch `opencode/p2-lane13-15` (pushed). All native branches are **private**
and were never pushed; they are based on the approved native baseline
`f14c6851`. No maintained checkout or engine export was modified.

## Native candidates

| Candidate | Branch @ commit | Build dir | `nectar.exe` SHA-256 | Base |
|---|---|---|---|---|
| Lane 13 Dwarf Orange (`pc_p2_dwarf_orange`) | `opencode/p2-lane13-orange-native` @ `2e3941c8` | `output/native-lane13-orange-build` | `F72EF559FB45147FB7468D54C636E3DC6F6BFB871B84D470E195F5358DAEBCFD` | `f14c6851` |
| Lane 15 Qurione (ported) | `opencode/p2-lane15-qurione-r2` @ `7a6e7885` | `output/native-lane15-qurione-r2-build` | `C370D61B147D82CFAFDD53FC6784F4904D02F254BBD9D0561566D07504E1234C` | `f14c6851` |
| Lane 15 combined (Qurione + Shijimi) | `opencode/p2-lane15-combined-native` @ `e2b49b90` | `output/native-lane15-qurione-r2-build` (relinked) | `B7313A15D7CB8A6C29088A5CD6BC7621AE40292DC5DC5ECAE498E6552573818B` | `f14c6851` |

All three: private Ninja/MinGW `g++ 16.2.0` Release builds, `PIKMIN_NATIVE_JAUDIO=ON`,
`ninja -n` reports no work. Lane 15's `combined` merges the two lane-15
candidates; lane 13's candidate is independent.

**Superseding single head:** `opencode/p2-lane13-15-combined-native` @ `099b022c`
merges all three plus the opt-in `pc_p2_kochappy_fsm` source FSM; build
`output/native-lane15-qurione-r2-build`, exe SHA-256 `2005BB81…4588`
(`docs/PIKMIN2_LANE1315_COMBINED.md`). Prefer this one for integration.

## Shared semantics needing lane-01 review

- `pc_p2_kochappy_stun_register(BTeki*, float fitDuration)` and
  `p2purpleimpact::updateFit(state, dt, interrupted, fitDuration)` are
  parameterized (Dwarf Red 10 s / Dwarf Orange 5 s); the native policy test was
  updated. `pc_p2_purple_impact.cpp` accepts either bulborb registration.
- `include/teki.h` `TPF_Life` chain includes `pc_p2_dwarf_orange_max_health`,
  `pc_p2_qurione_param_f`, and `pc_p2_shijimi_param_f` (composed additively over
  the existing Kogane/Sokkuri/Armor chain).
- `src/plugPikiNakata/tekibteki.cpp`: `pc_p2_qurione_update` / `pc_p2_shijimi_update`
  joined the maintained `#if PIKI_PC_PORT` update block; `pc_p2_qurione_suppress_ai`
  and `pc_p2_shijimi_suppress_ai` guard `doAI`.
- Everything else is additive/opt-in modules plus `CMakeLists.txt` /
  `pc_p2_preview.cpp` / `tekimgr.cpp` hook additions.

## Root tooling, evidence and docs

- `experimental/pikmin2_dwarf_orange_runtime.py`, `…_delivery.py`, `…_reentry.py`,
  `…_restart.py`; `experimental/pikmin2_mixed_bulborb_runtime.py`;
  `experimental/pikmin2_lane15_mixed_runtime.py`.
- Tests: `tests/test_pikmin2_dwarf_orange_runtime.py`, `…_chain.py`,
  `…_restart.py`, `…_mixed_bulborb_runtime.py`, `…_lane15_mixed_runtime.py`.
- Docs: `docs/PIKMIN2_DWARF_ORANGE_NATIVE.md` (gates, evidence),
  `…_DWARF_ORANGE_RESTART.md`, `…_MIXED_BULBORB.md`, `…_LANE15_MIXED.md`,
  `…_QURIONE_LIFECYCLE.md` §8 (r2 port).
- Evidence roots: `output/p2-lane13-orange-arena2/bd2b9fff…/` (combat + delivery),
  `output/p2-lane13-restart-root/output/p2-lane13-dwarf-orange-restart/`,
  `output/p2-lane13-mixed-arena/30f460e6…/`, `output/p2-qurione-lane15/r2-run/`,
  `output/p2-lane15-mixed-arena/5619907c…/`.

## Gate summary

| Identity | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| Dwarf Orange 44 | PASS | PARTIAL (host P1 AI) | PASS P1-proxy | PASS P1-proxy carry | BLOCKED (#397) | PASS (restart) | PASS probe (mixed) |
| Qurione 16 | PASS | PASS (source FSM) | N/A | source-level | BLOCKED (#397) | UNTESTED | PASS probe (mixed) |
| Shijimi 77 | PASS | PASS (source FSM) | N/A | UNTESTED | BLOCKED (#397) | UNTESTED | PASS probe (mixed) |

## Exact integration request

1. Review the shared `teki.h` / `tekibteki.cpp` / stun-parameterization changes.
2. Cherry-pick/rebase the three native candidates onto the maintained native
   line (they are already on `f14c6851`) and run the maintained build/export.
3. Consume the root tooling for the admission ledger once lanes 02/03/05 open
   the generated-session path.

Remaining blockers are all shared: lane 01 integration, lane 02/03/05
generated-session admission, lane 06 rewards, and #397 lifetime/cleanup.
