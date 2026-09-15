# Lane 05 (Installation) — DeepSeek handoff: identity-to-runtime binding

Parent issue: [#442](https://github.com/4laric/pikmin-randomizer/issues/442). Implementation owner: Codex through shared account 4laric. Executing agent/session: DeepSeek lane 05 worktree (`output/dsw/l05-root`, branch `deepseek/p2-l05`).

## Source IDs and files owned

- **Concrete consumer (one real family):** Dwarf Orange Bulborb — `BlueKochappy`, source id **44** (enum `BlueKochappy`), which is the second identity in the Snow/Dwarf Orange cohort (family lane 13). Its assets model `Kochappy` and the existing bespoke installer `experimental/pikmin2_dwarf_orange_install.install(bank, profile_dir, run, generator_ids)` are consumed as-is; lane 05 only adapts and sequences them.
- **Owned/edited files (root only):**
  - `experimental/pikmin2_family_install.py` — identity→family binding layer, adapter validate hooks, session-level content cache.
  - `randomizer/runner.py`, `randomizer/__main__.py` — launcher `--p2-content` / `--p2-actors` wiring + `<session>/p2-content-cache`.
  - `tests/test_pikmin2_install_binding.py` — new (16 tests).
  - `scripts/probe_p2_install_binding.py` — new product-path probe for the install-binding path.
  - `docs/PIKMIN2_CONTENT_STAGING.md` — documented the binding layer, cache and launcher flags.

## Ordered commits / dirty state

- **Root** branch `deepseek/p2-l05`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` (`codex/p2-main-review`). Clean at head.
  1. `7ab7d79` — `lane05: identity-to-runtime binding for family content install (#442)`
  2. `642e398` — `lane05: document identity-to-runtime binding layer (#442)`
  3. `9a3b647` — `lane05: handoff (identity-to-runtime binding) (#442)`
  4. `021fafa` — `lane05: review fixes - session cache, validate hook, source-id agreement (#442)`
  5. `dfb83a3` — `lane05: handoff after review fixes (#442)`
  6. `545edbe` — `lane05: review fixes 2 - launcher cache-replay test + probe log paths (#442)`
- **Native** branch `deepseek/p2-l05-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`. **No changes** (`git status` clean). Lane 05 required no native edits: the `ENEMY_P2` parser/roster seam is already integrated (lane 03), and the native Dwarf Orange config reader (`pc_port/pc_p2_dwarf_orange.cpp`, reads `p2-dwarf-orange-*.txt`) already exists in the maintained line.

## Interfaces/hooks touched and why

- `resolve_family(identity)` (new): `int` source id or `str` enum name → lane-05 family key. Narrow by design; `44`/`BlueKochappy` → `dwarf_orange`, anything else raises `ValueError` (no silent P1 fallback). Does not depend on roster eligibility (that stays lane 02/03); it is lane 05's own identity→content knowledge.
- `install_layout(run, layout, content_root, actor_bindings=None, retail_assets=None, cache_dir=None)` (new): binds every `p2_layout.binding` (`{target, source_id, enum_name}`) to its family installer, sourcing from `<content_root>/<enum_name>`. Requires the binding's `source_id` and `enum_name` to resolve to the same family. Runs each adapter's `validate(source)` pre-flight in the plans loop *before* `prepare_private_destination`, so a wrong source leaves nothing behind. Cache: without `cache_dir`, a matching `<run>/p2-binding-receipt.json` is a cached replay; with `cache_dir` (session-level), content is stored under `<cache>/p2bind-<plan digest>/tree` + `cache-receipt.json` and a later launch materializes it into a fresh run, reporting `cached=True` without re-reading sources.
- `ADAPTERS` registry (now `{'name': {'install', 'validate'}}`) + `_adapt_dwarf_orange` / `_validate_dwarf_orange`: the bespoke `pikmin2_dwarf_orange_install.install` is wrapped to the shared `install(source, run, actors)` shape, with a source-only pre-flight so a wrong source fails before mutation.
- Launcher (`--p2-content PATH`, `--p2-actors JSON`): stages a generated `p2_layout` seed automatically, keyed by identity, with a session-level cache at `<session>/p2-content-cache`; mutually exclusive with `--content-manifest` and `--family-install`. The `PIKMIN_P2_BOUND` line reports the `cached` flag.

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

- `py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q` → **17 passed** (includes `test_launch_replays_from_session_cache`, which calls `runner.launch` twice on one session, deletes the sources in between, and asserts the second run's `p2-binding-receipt.json` is `cached: true` with byte-identical actors/model files).
- `py -3.12 -m pytest tests/test_pikmin2_install_binding.py tests/test_pikmin2_family_install.py tests/test_pikmin2_staging.py tests/test_pikmin2_session_staging.py tests/test_pikmin2_seed_bridge.py tests/test_pikmin2_seed_generation.py tests/test_pikmin2_dwarf_orange.py tests/test_pikmin2_dwarf_orange_install.py tests/test_pikmin2_roster.py tests/test_pikmin2_kochappy_bank.py tests/test_pikmin2_kochappy_arena.py -q` → **140 passed, 1 failed** (the one failure is the pre-existing `test_pikmin2_kochappy_bank.py::test_compiled_family_policy`, which compiles C++ against `l05-root/native/pc_port` — the root worktree has no `native/` directory by design; unrelated to this slice).
- Regression smoke on launcher-adjacent suites (`test_p2_placement`, `test_ap_reconnect`, `test_emperor_goal`, `test_all_areas`, `test_death_link`) → **65 passed, 17 subtests**.
- `py -3.12 scripts/test_p2_generated_session.py <build>/pc_randomizer_probe.exe` → **passed** (real `ENEMY_P2` bootstrap, native parse/bind, content stage+cache, 5 rejection cases); log at `C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/p2-generated-session.txt`.
- `py -3.12 scripts/probe_p2_install_binding.py --output <out>` → **passed**: generated `p2_layout` seed → `runner.launch --p2-content` → real Dwarf Orange adapter (15 room models) → second launch replays from the session cache with `cached=True` (fresh flags `[False, True]`); log at `C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/probe-install-binding.txt`.

## Assumptions

- The Dwarf Orange adapter's source layout is `<content_root>/BlueKochappy/{bank,profile}`; a real family bank/profile is produced by the family lane, not lane 05.
- `actor_bindings` (target → native generator id) is a caller/lane-04/native input: the runtime generator id is resolved by the `ENEMY_P2`/`pc_randomizer_bind_generator` seam, not install time. A missing binding fails closed rather than fabricating an id.
- The session-level cache is keyed by the binding plan (bindings + actor map), not by the family bank bytes; a family-content change under the same plan requires clearing `<session>/p2-content-cache`. The cached receipt still records the family's own bank/profile hashes for diagnosis.
- Lane 05's registry is deliberately narrow (one adapter). Snow/Kochappy and all other bespoke families need their own adapter + optional `validate` hook before `install_layout` resolves them.
- Native branch needs no commit because nothing in the engine changed for this slice.

## Remaining blockers (naming the provider lane)

- **Lane 02 (#438):** the admission set is empty, so a real accepted `p2_layout` cannot be generated; tests/probe repro the product path by monkeypatching `admitted_ids`.
- **Lane 13 / family:** produce the real Dwarf Orange bank+profile and accept the native actor binding so the content staged here is consumed by a live actor (the native reader `pc_p2_dwarf_orange.cpp` already exists).
- **Lane 01:** export/merge the launcher/`experimental` changes into the maintained line after review.

## Reproduction (one command)

```powershell
py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q
```

## Subagent usage

This fix slice delegated three tasks:

- **#1 — Dwarf Orange validate() contract (explore):** extracted the exact `plan()`/`install()` source-side validation rules, constants, required files and "before any mutation" guarantees with `file:line` citations. Used as-is to author `_validate_dwarf_orange` and confirm the synthetic bank/profile fixture shape.
- **#2 — cache + session-dir layout (explore):** pinned `stage_session_content`'s cache layout (`<cache>/<key>/tree` + `cache-receipt.json`, `.staging` temp suffix) and confirmed `session.directory` is stable across launches (while `run.directory` is per-token). Used as-is to implement the session-level `cache_dir` in `install_layout` and the `<session>/p2-content-cache` wiring.
- **#3 — test authoring (general):** wrote/updated `tests/test_pikmin2_install_binding.py`: renamed the seed, used a distinct generator id, added an autouse `_isolate_overrides` fixture, and added four new tests (source-id mismatch, real dwarf-orange adapter, validate-hook fail-closed, session-cache replay). The real-adapter test passed immediately; the other three failed only because the contract land (source-id agreement, `validate` hook, `cache_dir`) did not exist yet — exactly the intended TDD separation. I implemented to the contract and all 16 pass. One subagent-authored assertion (order-sensitive `cached == [False,True]` on unsorted token globs) surfaced in my probe script, not the tests; I corrected the probe to use `sorted(cached)`.

Estimate: the two explores saved ~30 min of my own contract/layout reading; the test-first split made the three contract gaps explicit before I wrote production code. Cost was minimal reconciliation (one order-sensitive assertion, one `_OVERRIDES`-aware `_validator` fix for fake-registered tests).

### fix2 pass (review follow-up)

- **#1 explore — log paths + line numbers:** confirmed the two probe logs live under the worktree-relative (gitignored) `output/dsw/l05-out/` and that the absolute `C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/` was empty, and returned the exact `pytest.raises` args to tighten. Used as-is to copy the logs to the absolute path and cite it.
- **#2 explore — launcher session-cache mechanics:** confirmed `session.directory`/`run.directory` split, the cache marker path, `_replay_from_cache` `cached=True`, `_content_files` exclusions, and that a fake override skips `validate`. Used as-is to write a correct `test_launch_replays_from_session_cache` (order-independent `cached` assertion).
- **#3 general — test edits:** wrote `test_launch_replays_from_session_cache` and tightened `test_install_layout_source_id_mismatch_rejected` to `pytest.raises(StagingError)`; 17 passed. Used as-is.

## Slice 2

Second bounded slice: **second family adapter (Snow) + interrupted-staging / wrong-source fail-safe**.

### Source IDs and files

- **Second real consumer:** Snow Bulborb — `YellowKochappy`, source id **45** (`common_name` "Snow Bulborb"), family lane 13. Staged through lane 13's existing Snow stager `experimental/pikmin2_enemy.install(imported, run, generator_ids)` (flat bank: `snow.json` + `p2-snow.txt` + `snow_*.mod`), consumed as-is.
- **Changes:**
  - `experimental/pikmin2_family_install.py` — added `IDENTITY_FAMILY` entries (45/`yellowkochappy` → `snow`), the `snow` adapter (`_adapt_snow`/`_validate_snow`), and strengthened `_validate_dwarf_orange` to reject a bank whose identity or `reference_sha256` does not match its profile (before any asset tree).
  - `tests/test_pikmin2_install_binding.py` — added `make_snow_source` + `SNOW_CLIPS`, and tests: `test_resolve_family_snow`, `test_install_layout_real_snow_adapter`, `test_install_layout_two_families_staged_together`, `test_install_layout_rejects_wrong_source_hash_before_tree`, `test_interrupted_cache_staging_fails_safe` (22 total).
  - `scripts/probe_p2_install_binding.py` — extended to stage BOTH identities through `runner.launch` (fresh + cached replay) and to prove wrong-source fail-closed at the launcher; log under the ABSOLUTE `C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/`.
  - `docs/PIKMIN2_CONTENT_STAGING.md` — documented the Snow adapter, the strengthened validate (identity + reference hash) and the write-last cache marker.

### Deliverables (a/b/c)

- **(a) Snow adapter** — `resolve_family(45|YellowKochappy) == "snow"`; `_validate_snow` checks `snow.json`/`p2-snow.txt` presence and `schema==1` + `species=="YellowKochappy"`; `_adapt_snow` unpacks `(generator, species)` and delegates to `pikmin2_enemy.install`, returning a small receipt (the family installer returns `None`). Real-adapter test passes; a single `install_layout` call stages Dwarf Orange + Snow together (30 room models, both `p2-*-actors.txt`).
- **(b) Interrupted staging fails safe** — `test_interrupted_cache_staging_fails_safe` injects a `copyfile` failure on the 2nd file during `_populate_cache`; the cache marker (`p2bind-*/cache-receipt.json`) is written last, so the interrupted run leaves no marker, and the next launch treats it as a miss and does a fresh install (all three files present). Partial tree is neither reused nor left corrupting the result.
- **(c) Wrong-source rejection at launcher level** — `_validate_dwarf_orange` now rejects a bank with a wrong `reference_sha256` (or wrong identity); the probe tampers the bank's `reference_sha256`, `runner.launch` raises `StagingError`, and no `runs/*/assets` tree is created (`bad-session asset trees: 0`).

### Tests run

- `py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q` → **22 passed**.
- Broader lane-05/adjacent subset (install_binding, family_install, staging, session_staging, seed_bridge, seed_generation, dwarf_orange, dwarf_orange_install, enemy, animation, snow_policy, roster) → **165 passed, 2 failed** — both failures are the pre-existing root-`native/` C++ compile tests (`test_pikmin2_animation.py::test_native_playback_and_validation`, `test_pikmin2_snow_policy.py::test_native_policy_isolation_and_recycled_address_teardown`); the root worktree has no `native/` by design.
- `py -3.12 scripts/probe_p2_install_binding.py --output C:/Users/alari/pikmin-randomizer/output/dsw/l05-out` → **passed** (log `C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/probe-install-binding.txt`): two bindings (`YellowKochappy`, `BlueKochappy`), two launches cached `[False, True]`, 15+15 room models, both actor files, wrong-source fail-closed with 0 asset trees.

### Six-gate update

Still an installation/provider lane: identity→content binding for BOTH cohort dwarfs is now PASS at the content/staging level; live native gameplay gates (spawn/movement/combat/death/transport/cleanup) remain source-backed N/A here and belong to family lane 13 + independent QA (33). No admission claim is made (lane 02's admission set is still empty; the probe monkeypatches `admitted_ids` to `[44, 45]`).

### Remaining blockers

- **Lane 02 (#438):** empty admission set — no real accepted `p2_layout`; probes/tests monkeypatch `admitted_ids`.
- **Lane 13 / family:** produce the real banks (Dwarf Orange + Snow) and accept the native actor binding (native readers `pc_p2_dwarf_orange.cpp` / `pc_p2_enemy.cpp` already exist) so the staged content is consumed by live actors.
- **Lane 01:** export/merge the launcher/`experimental` changes into the maintained line.

### Subagent usage (slice 2)

- **#1 explore — Snow bank/installer source audit:** extracted `pikmin2_enemy.install`'s required inputs (flat `snow.json`/`p2-snow.txt`/`snow_*.mod`), its `ValueError`s, that it performs NO reference-hash check (unlike Dwarf Orange), the `parse_bank`/`validate_files` formats, and the existing synthetic Snow fixture in `tests/test_pikmin2_animation.py`. Used as-is; drove `_adapt_snow`/`_validate_snow` and the synthetic `make_snow_source`.
- **#2 explore — Snow candidate + adapter inventory:** inventoried every Snow/`YellowKochappy` module/test/doc/native reader, confirmed `IDENTITY_FAMILY`/`ADAPTERS` shapes, the flat-vs-bank/profile layout difference, and the one-sided sibling overlap checks. Used as-is; avoided reimplementing `pikmin2_enemy`.
- **#3 general — test authoring:** wrote the 5 new tests + `make_snow_source` + `SNOW_CLIPS`; 4 failed initially only because the Snow adapter and the strengthened dwarf-orange validate did not exist yet, and `test_interrupted_cache_staging_fails_safe` passed immediately (marker written last already). Used as-is (one of #3's assertions — Snow receipt `is truthy` — required me to make `_adapt_snow` return a receipt instead of `None`, which is the correct adapter contract anyway).

Estimate: the two explores saved ~25 min of Snow-layout/validation reading; the test-first split made the adapter + validate strengthening gaps explicit before I touched production code. Cost: one reconciliation (Snow receipt must be non-`None`).
