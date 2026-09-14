# Lane 05 (Installation) — DeepSeek handoff: identity-to-runtime binding

Parent issue: [#442](https://github.com/4laric/pikmin-randomizer/issues/442). Implementation owner: Codex through shared account 4laric. Executing agent/session: DeepSeek lane 05 worktree (`output/dsw/l05-root`, branch `deepseek/p2-l05`).

## Source IDs and files owned

- **Concrete consumer (one real family):** Dwarf Orange Bulborb — `BlueKochappy`, source id **44** (enum `BlueKochappy`), which is the second identity in the Snow/Dwarf Orange cohort (family lane 13). Its assets model `Kochappy` and the existing bespoke installer `experimental/pikmin2_dwarf_orange_install.install(bank, profile_dir, run, generator_ids)` are consumed as-is; lane 05 only adapts and sequences them.
- **Owned/edited files (root only):**
  - `experimental/pikmin2_family_install.py` — added identity→family binding layer.
  - `randomizer/runner.py`, `randomizer/__main__.py` — launcher `--p2-content` / `--p2-actors` wiring.
  - `tests/test_pikmin2_install_binding.py` — new (12 tests).
  - `docs/PIKMIN2_CONTENT_STAGING.md` — documented the binding layer + launcher flags.

## Ordered commits / dirty state

- **Root** branch `deepseek/p2-l05`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` (`codex/p2-main-review`). Clean at head.
  1. `7ab7d79` — `lane05: identity-to-runtime binding for family content install (#442)`
  2. `642e398` — `lane05: document identity-to-runtime binding layer (#442)`
- **Native** branch `deepseek/p2-l05-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`. **No changes** (`git status` clean). Lane 05 required no native edits: the `ENEMY_P2` parser/roster seam is already integrated (lane 03), and the native Dwarf Orange config reader (`pc_port/pc_p2_dwarf_orange.cpp`, reads `p2-dwarf-orange-*.txt`) already exists in the maintained line.

## Interfaces/hooks touched and why

- `resolve_family(identity)` (new): `int` source id or `str` enum name → lane-05 family key. Narrow by design; `44`/`BlueKochappy` → `dwarf_orange`, anything else raises `ValueError` (no silent P1 fallback). Does not depend on roster eligibility (that stays lane 02/03); it is lane 05's own identity→content knowledge.
- `install_layout(run, layout, content_root, actor_bindings=None, retail_assets=None)` (new): binds every `p2_layout.binding` (`{target, source_id, enum_name}`) to its family installer, sourcing from `<content_root>/<enum_name>`, validating everything before any write, writing `run/p2-binding-receipt.json`, and replaying from a matching receipt (cached replay) without re-reading sources.
- `ADAPTERS` registry + `_adapt_dwarf_orange` (new): wraps the bespoke `pikmin2_dwarf_orange_install.install` into the shared `install(source, run, actors)` shape; source layout `<source>/bank` + `<source>/profile`.
- Launcher (`--p2-content PATH`, `--p2-actors JSON`): stages a generated `p2_layout` seed automatically, keyed by identity; mutually exclusive with `--content-manifest` and `--family-install` (each owns the private asset tree).

No shared native files, no `teki.h`/manager/CMake hooks were needed for this slice.

## Build evidence (`output/dsw/l05-build-evidence.txt`)

```
2026-09-14T19:53:49 lane=l05 target=pc_randomizer_probe native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l05-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l05-build\pc_randomizer_probe.exe sha256=e16b0fb356d9b797d0a7c90bd0868b1b5038035e223be124fe03e67f1fa479cf ninja_n="ninja: no work to do." seconds=5
```

Built with the lane wrapper (`build_lane.py l05 --target pc_randomizer_probe`); cmake + Ninja + MinGW g++ 16.2, `-DPIKMIN_NATIVE_JAUDIO=ON`. `ninja -n` dry run: `ninja: no work to do.` The full `pikmin_pc` target was not built because this slice makes no native/engine change; the probe is the native half of the lanes 02/03/05 product probe.

## Fixture adoption evidence

Not applicable to this slice and reported honestly: lane 05 made no real-GL runtime fixture run, so there is no 960×540 centred-window / live-starting-Pikmin screenshot for THIS slice. That startup-adoption requirement remains for the first runtime acceptance run, which is the family lane's (13) and independent QA's (33) job, not the installation/staging boundary. The product-path native probe (`scripts/test_p2_generated_session.py`) ran headless (no GL) and passed.

## Six-gate table (honest; installation = provider lane, natural vs injected labels)

| Gate | Status | Label / note |
|---|---|---|
| Exact identity and spawn | source-backed N/A (content level) / UNTESTED (native spawn) | Lane 05 binds the seed identity (`BlueKochappy`/44) to content at generation time; the live native actor spawn is the family+native `ENEMY_P2` seam, not lane 05. |
| Autonomous movement and animation | source-backed N/A | Not an installation-lane gate. |
| Attacks and receivers | source-backed N/A | Not an installation-lane gate. |
| Death and corpse | source-backed N/A | Not an installation-lane gate. |
| Actual transport and reward | source-backed N/A | Not an installation-lane gate. |
| Cleanup and re-entry | source-backed N/A | Not an installation-lane gate. |
| **Installation acceptance (A-content / G-product)** | **PASS (Python, real generated seed)** / UNTESTED (live actor) | Fresh install, cached replay, missing/wrong source, missing actor binding, and interrupted/conflicting/stale tree all fail closed; an end-to-end generated `p2_layout` seed stages through the launcher without per-family manual flags. Proof is synthetic-source Python + a monkeypatched admission cohort, because the live admission set is empty (lane 02) and the real Dwarf Orange bank is a family-lane artifact. No gameplay PASS is claimed. |

## Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q` → **12 passed**.
- `py -3.12 -m pytest tests/test_pikmin2_family_install.py tests/test_pikmin2_staging.py tests/test_pikmin2_session_staging.py tests/test_pikmin2_install_binding.py tests/test_pikmin2_seed_bridge.py tests/test_pikmin2_seed_generation.py tests/test_pikmin2_dwarf_orange.py tests/test_pikmin2_dwarf_orange_install.py tests/test_pikmin2_kochappy_fsm.py tests/test_pikmin2_roster.py -q` → **121 passed, 1 skipped** (skip is asset-dependent).
- Regression smoke on launcher-adjacent suites (`test_p2_placement`, `test_ap_reconnect`, `test_emperor_goal`, `test_all_areas`, `test_death_link`) → **65 passed, 17 subtests**.
- `py -3.12 scripts/test_p2_generated_session.py <build>/pc_randomizer_probe.exe` → **passed** (real `ENEMY_P2` bootstrap, native parse/bind, content stage+cache, 5 rejection cases).

## Assumptions

- The Dwarf Orange adapter's source layout is `<content_root>/BlueKochappy/{bank,profile}`; a real family bank/profile is produced by the family lane, not lane 05.
- `actor_bindings` (target → native generator id) is a caller/lane-04/native input: the runtime generator id is resolved by the `ENEMY_P2`/`pc_randomizer_bind_generator` seam, not install time. A missing binding fails closed rather than fabricating an id.
- Lane 05's registry is deliberately narrow (one adapter). Snow/Kochappy and all other bespoke families need their own adapter before `install_layout` resolves them.
- Native branch needs no commit because nothing in the engine changed for this slice.

## Remaining blockers (naming the provider lane)

- **Lane 02 (#438):** the admission set is empty, so a real accepted `p2_layout` cannot be generated; tests repro the product path by monkeypatching `admitted_ids`.
- **Lane 13 / family:** produce the real Dwarf Orange bank+profile and accept the native actor binding so the content staged here is consumed by a live actor (the native reader `pc_p2_dwarf_orange.cpp` already exists).
- **Lane 01:** export/merge the launcher/`experimental` changes into the maintained line after review.

## Reproduction (one command)

```powershell
py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q
```

## Subagent usage

- **#1 — family-installer source audit (explore):** inventoried all `*_install.py`/`*_bank.py` signatures and the Dwarf Orange bank/plan constants. Used as-is; drove the adapter contract and roster facts (no edits).
- **#2 — lane-05 existing-candidate inventory (explore):** confirmed first that no `resolve_family`/`install_layout`/identity→family mapping existed, and that the native side already reads `p2-dwarf-orange-*.txt` and parses `ENEMY_P2`. Used as-is; prevented reimplementing an existing bridge.
- **#3 — test authoring (general):** wrote `tests/test_pikmin2_install_binding.py` (11 tests) against my specified contract; all initially failed with `AttributeError` (contract functions absent), exactly as expected. Used as-is, then I implemented to the contract and added a 12th end-to-end launch test myself (the first version restored the admission monkeypatch too early and failed `fingerprint()` re-validation — corrected by keeping the patch through `launch`).

Estimate: source/audit inventory deferred ~30–45 min of my own grepping/reading; the test-first contract caught the admission-set interaction before commit. Cost was minor reconciliation on the launch test.
