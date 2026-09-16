# Queen30 combined-candidate transport QA — lane muse-queen-combined-qa (#529)

Implementation owner: Codex through shared account `4laric`; executing
contributor Muse Spark 1.3 (worker muse-l69, session
`opencode:ses_f57d77bb6ffekDlzMEjJu9W0Sk`, generation 2, attempt
`3ee78cf3…abc79` matched before edits). No nested agents; no ADMIT writes;
legacy lane24 and both maintained checkouts never modified.

## What this slice is

Private integration preparation of EXISTING source, not a new Queen
implementation. The Queen sidecar + runner (lane24 Queen gate5) were absent
from the combined species line (preflight confirmed); this slice applies
only those existing commits atop the current species pins in a private
root/native pair, builds under the spare heavy-build lease, and
independently reproduces natural death → corpse → autonomous carrier latch
→ real Pod receipt in a fresh arena. The #496 review and lane24 gate5
evidence are consumed as-is; no historical audit is repeated here.

## Pins and imported commits (exact)

Species pins (bases, unchanged by me):

- Root base `e72f350ec89321b1b6d321739baa5fb44211614d`, worktree
  `output/qa-root-529`, branch `codex/throughput-qa-529`.
- Native base `f05e3162daa83a03c861867ed3dbb942e3afd0b7`, worktree
  `output/qa-native-529`, branch `codex/throughput-qa-529`.

Imported lane24 Queen gate5 commits (original authorship preserved,
`-x` cherry-pick lines recorded):

| Repo | Commit | Subject |
|---|---|---|
| native | `7c1c54f92e8e50d950a06a74a9677438e9133f02` | Queen Creature host sidecar (new `pc_port/pc_p2_queen_teki.{h,cpp}`, `pc_p2_queen_teki_policy.h`) |
| native | `21e7819e96a5323af2c845afede1e47640618a0b` | Hook Queen Teki host (CMakeLists, teki.h, preview receipt/title, lifetime, gameCoreSection, tekibteki, tekimgr) |
| root | `f1289446e37335a99760f52352a934cbda060792` | Queen Creature fixture + harness (`experimental/pikmin2_queen_creature_runtime.py`) |
| root | `1f8d7b62d6349f4b3831ca87aa96407bf3a45c99` | Queen transport gate validator + tests |

King-only `e8b32e3b` (king_teki param seam) deliberately EXCLUDED.

Private conflict resolution (exactly one, in `21e7819e`):

- `src/plugPikiNakata/tekibteki.cpp` tick hunk: kept the species
  Fuefuki vehicle line + Bombsarai line AND added
  `pc_p2_queen_teki_tick(this)` after `pc_p2_king_teki_tick` (no-op for
  non-bound actors).
- `src/plugPikiNakata/tekibteki.cpp` draw-chain hunk: kept the full
  species chain (sarai/bombsarai/…) AND inserted
  `!pc_p2_queen_teki_draw(…)` after the King entry.
- All other files of `21e7819e` applied cleanly (CMakeLists, teki.h,
  pc_p2_preview receipt + `pc_p2_queen_teki_name` title branches live
  alongside every species branch — verified: waterwraith/king/sheargrub
  branches intact).

Resulting private heads: root `d5054520` (+ this report), native
`eae22571`. Both worktrees clean at each build/provenance step.

Dedicated additive QA files owned by this lane (all on the feature
branches above):

- `experimental/pikmin2_queen_combined_qa.py` — independent QA checker
  (own regexes/structure; zero shared code with lane24 validators).
- `tests/test_pikmin2_queen_combined_qa.py` — 11 unit tests, synthetic
  chains only (pass + 10 failure modes).
- `docs/PIKMIN2_QUEEN_COMBINED_QA.md` — this report.
- `native/tools/p2_queen_combined_qa_fixture.cpp` — isolated pure-C++
  log observer (no engine link; `-Wall -Wextra -Werror` clean).

## Fresh build evidence (combined pin)

Leased heavy-build runner
(`output/muse-wave/control/leased_run.py`, private lease
`build:output/qa-build-529`, aggregate cap respected, auto-renewed,
released after):

- Configure+build log:
  `output/workflow/extra-capacity/muse-queen-combined-qa/build-1789545265302228700.log`
  (SHA-256 `657901c085c32b64e7bd96d5f42a60e6e20402c8edd6e5b3841b5cff08ff8d2b`),
  exit 0, `ninja: no work to do.` dry run, native `eae22571` clean.
- Executable `output/qa-root-529/output/qa-build-529/bin/nectar.exe`
  (private dir; the wrapper's relative `-B` resolved under the lane
  root — recorded honestly; lease covered the build while it ran)
  SHA-256 `01819d075b434c089b381ce5ad89fe84dbe9463fd5885810013bc98b28367dfd`.
- Fixture build log:
  `output/workflow/extra-capacity/muse-queen-combined-qa/build-1789545474506308700.log`
  (SHA-256 `afc8f665c0d17e1a06a06dff0ab9f618f6279b216fb6b9041e86cb5a1296adc0`),
  exit 0; `output/qa-529/queen-fixture/build/provenance.json` status
  `built` vs expected head `eae22571…`; fixture exe
  `output/qa-529/queen-fixture/build/fixture.exe` SHA-256
  `74640532d9c345609cb09016315048b7475adc291ade4bc21e289a1d8d42a149`.

## Fresh runtime evidence (new private arena, current baseline)

`output/qa-529/queen-run/queen/b7ec6da77c1c482ba90a1b739e03bd7c/native.log`
(1435 lines), staged by the imported runner from the species-pin
`overlay()` with explicit 64-red squad rows, `PIKMIN_P2_ROOM_WINDOW=960x540`,
`SDL_AUDIODRIVER=dummy`; bank `output/dsw/l24-out/bulblax-bank`
(read-only); Pod package `output/dsw/l19-out/pod` (read-only,
`corpseValue=2`):

- log:7 `Experimental preview window set to 960x540 windowed and centered`.
- log:729 `P2_QUEEN_TEKI_READY generator=230010 type=3
  binding=creature_host health=5000.0` (source Queen HP, exact).
- log:730 `P2_QUEEN_TEKI_HOST_AI_SUPPRESSED … eat_state=CHAPPYSTATE_Unk8
  latch_preserved=1`.
- log:755 `P2_QUEEN_CREATURE_BASELINE red=64`; 66 blows-driven
  `P2_QUEEN_TEKI_FLICK`s; attached peak 4.
- log:1392 `P2_QUEEN_TEKI_CORPSE generator=230010 health=0.0`
  (engine-receiver death, no writes); log:1396
  `P2_QUEEN_CREATURE_CORPSE_PELLET found=1`.
- 12 `P2_QUEEN_CREATURE_CARRY` rows, carry peak 3, transport peak 9 —
  autonomous latch, no ring disruption after latch.
- log:1433 `[Pikipelago] P2_POD_RECEIPT id=corpse:queen:230010 value=2
  new=1 pokos=2 seeds=0`; exit 0; log:1435 `PASS P2_QUEEN_CREATURE_RUNTIME`.
- Zero `Extinction`, zero staging markers, no leftover process
  (`result.json`: `passed=true`, `leftover_pid=null`).

Independent adjudication of the SAME fresh log:

- `experimental.pikmin2_queen_combined_qa check` →
  `output/qa-529/qa-result.json`: `passed=true`, `failed=[]`,
  flicks 66, receipt `queen:230010 value=2 new=1`.
- Isolated C++ observer `output/qa-529/queen_qa_observe.exe` (built
  `-Wall -Wextra -Werror` clean): all 9 checks ok, `result=PASS` —
  agrees with Python exactly.

Unit tests: `py -3.12 -m pytest tests/test_pikmin2_queen_combined_qa.py -q`
→ 11 passed
(`output/workflow/extra-capacity/muse-queen-combined-qa/pytest-qa.log`,
SHA-256 `2fac420cbb5e606881ce6a2e0526760f56264dbeb3d822cd6e6e1860bd1c0968`).

## Preserved caveats (not parity — do not relabel)

- Carry counts (peak 3) and transport peak (9) are Chappy-host-derived,
  not source-Queen 20–30-carrier semantics.
- Receipt `value=2` is Pod-package-configured (`P2_POD_1`
  `corpseValue`), owned by lane 06 — not source-Queen reward semantics.
- Gate-1 identity stays the authored carrier binding; only the
  transport chain is adjudicated here.

## Shared-file / seam disposition for the integrator

Every imported/shared file needing explicit source-bound review before
any promotion (none approved here):

- `pc_port/pc_p2_preview.cpp` — queen receipt + title branches (additive
  `else if` + name-chain entry; species branches preserved).
- `include/teki.h`, `pc_port/pc_p2_teki_lifetime.cpp`,
  `src/plugPikiKando/gameCoreSection.cpp`,
  `src/plugPikiNakata/tekibteki.cpp` (private keep-both resolution —
  review the tick/draw hunks), `src/plugPikiNakata/tekimgr.cpp`,
  `CMakeLists.txt` — narrow Queen hook lines only.
- New sidecar `pc_port/pc_p2_queen_teki.{h,cpp}`,
  `pc_port/pc_p2_queen_teki_policy.h` — Queen-scoped, no shared edits.
- Root runner + lane24 validators are lane24-authored evidence tooling,
  not species production code.

No maintained checkout was touched; promotion/build/export decisions
remain solely with the species integrator.

## Recommendation: ACCEPT candidate for integrator review (no ADMIT)

The combined pin reproduces the full natural chain with hash-bound
fresh evidence and two agreeing independent checkers. Requested
disposition: species integrator reviews the listed seams, decides
promotion of the Queen sidecar + hooks into the maintained species
line, and owns any combined-build/export. Next: ElecBug/species
siblings unaffected; cave item5 stays with muse-cave51; admitted cohort
`[23,44,54,57,59,60,61,62,78]` deny-others boundary untouched.

## Reproduction

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
py -3.12 -m pytest tests/test_pikmin2_queen_combined_qa.py -q
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 -m experimental.pikmin2_queen_creature_runtime run --assets <assets> --bank <bulblax-bank> --output <run-out> --exe <fixture.exe> --pod-package <pod-pkg>
py -3.12 -m experimental.pikmin2_queen_combined_qa check --log <run-out>/queen/*/native.log --code 0 --output qa-result.json
```
