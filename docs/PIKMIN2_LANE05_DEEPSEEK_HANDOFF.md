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
- **Lane 13 / family:** produce the real banks (Dwarf Orange + Snow) and accept the native actor binding (native readers `pc_p2_dwarf_orange.cpp` / `pc_p2_enemy.cpp` already exist) so the staged content is consumed by live actors. **Snow has no bank↔identity hash binding** (`pikmin2_enemy.install` performs no `reference_sha256`/source-hash check, unlike Dwarf Orange), so wrong-source detection (c) covers Dwarf Orange only; lane 13 should add a content-hash binding to the Snow installer so a mismatched Snow bank is rejected at install/validate time too.
- **Lane 01:** export/merge the launcher/`experimental` changes into the maintained line.

### Subagent usage (slice 2)

- **#1 explore — Snow bank/installer source audit:** extracted `pikmin2_enemy.install`'s required inputs (flat `snow.json`/`p2-snow.txt`/`snow_*.mod`), its `ValueError`s, that it performs NO reference-hash check (unlike Dwarf Orange), the `parse_bank`/`validate_files` formats, and the existing synthetic Snow fixture in `tests/test_pikmin2_animation.py`. Used as-is; drove `_adapt_snow`/`_validate_snow` and the synthetic `make_snow_source`.
- **#2 explore — Snow candidate + adapter inventory:** inventoried every Snow/`YellowKochappy` module/test/doc/native reader, confirmed `IDENTITY_FAMILY`/`ADAPTERS` shapes, the flat-vs-bank/profile layout difference, and the one-sided sibling overlap checks. Used as-is; avoided reimplementing `pikmin2_enemy`.
- **#3 general — test authoring:** wrote the 5 new tests + `make_snow_source` + `SNOW_CLIPS`; 4 failed initially only because the Snow adapter and the strengthened dwarf-orange validate did not exist yet, and `test_interrupted_cache_staging_fails_safe` passed immediately (marker written last already). Used as-is (one of #3's assertions — Snow receipt `is truthy` — required me to make `_adapt_snow` return a receipt instead of `None`, which is the correct adapter contract anyway).

Estimate: the two explores saved ~25 min of Snow-layout/validation reading; the test-first split made the adapter + validate strengthening gaps explicit before I touched production code. Cost: one reconciliation (Snow receipt must be non-`None`).

### fix3 pass (review follow-up)

Review items 1–2 (blocking) and 3–7 addressed; acceptance wording is no longer narrower than the code.

- **1 interrupted cache leaves nothing.** `_populate_cache` now wraps its copy loop in `try/except BaseException: shutil.rmtree(cache_root, ignore_errors=True); raise`, so a mid-copy interrupt removes the whole `p2bind-<digest>/` tree (not just the missing marker). `test_interrupted_cache_staging_fails_safe` asserts `not list(cache.glob("p2bind-*"))`.
- **2 wrong-source leaves no run tree.** `runner._launch` wraps `install_layout` in `try/except StagingError: shutil.rmtree(run.directory, ignore_errors=True); raise` (NativeRun's bootstrap.txt/state.txt are removed, not left behind). The probe and a new `test_launch_wrong_source_leaves_no_run_dir` assert `list((bad_session/"runs").iterdir()) == []`.
- **3 real-adapter mid-copy crash.** `install_layout` wraps the install loop in `try/except BaseException: shutil.rmtree(run/'assets', ignore_errors=True); raise`. New `test_real_adapter_mid_install_failure_cleans_assets` injects the copyfile crash inside the REAL Snow adapter and asserts no `run/assets` remains, then a re-run is a fresh install (15 snow models). `shutil.rmtree` was verified junction-safe in this environment (retail P1 assets are never followed through the overlay's `CreateJunction`/`os.link` overlay).
- **4 probe/docstring path.** Removed the absolute `l05-out` path from `probe_p2_install_binding.py` module docstring and aligned `docs/PIKMIN2_CONTENT_STAGING.md` (both now use a `<out>` placeholder; the absolute `C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/` stays only in this handoff).
- **5 Snow wrong-source gap recorded** under Remaining blockers (lane 13 ask: add a Snow bank↔identity hash binding).
- **6 `SNOW_CLIPS` aliases `DWARF_ORANGE_CLIPS`.**

Commit: `lane05: review fixes 3 - safe interrupt cleanup + wrong-source run-tree removal (#442)`.

Tests: `py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q` → **24 passed**. Probe re-run to the absolute `l05-out` → **passed** (two-identity cache replay `[False, True]`, wrong-source `bad-session run dirs: 0`).

#### Lesson (subagent use)

The delegated `test_interrupted_cache_staging_fails_safe` injected the crash in the fake-installer cache-populate step, where the WriteLast marker already made it pass, not in the real-adapter copy the brief asked for. I added `test_real_adapter_mid_install_failure_cleans_assets` myself to cover the real-adapter scenario and fixed the wording drift (partial tree IS now removed; wrong-source leaves no run tree). Going forward I will cross-check delegated tests against the brief's exact scenario before adopting them.

## Slice 3

Third bounded slice: fold in the two fix3 advisory cleanup gaps (with flip tests) and attempt the end-to-end generated-session → native launch proving the staged bank/sidecars are the ones the engine loads.

### Deliverables

1. **(root) `randomizer/runner.py`** — `_launch` now removes the run tree on **any** install failure (`except Exception`, was `except StagingError`). A `ValueError` or an adapter `RuntimeError` from `install_layout` no longer leaves `runs/<token>/{bootstrap.txt,state.txt}` behind.
2. **(root) `experimental/pikmin2_family_install.py`** — `install_layout`'s mid-install cleanup now also removes run-root sidecars an adapter already copied (e.g. `p2-snow.txt` from `pikmin2_enemy.install`), preserving only `SESSION_FILES` and the (not-yet-written) binding receipt — not just `run/assets`.
3. **(root tests) two flip-tests in `tests/test_pikmin2_install_binding.py`** — `test_launch_install_error_leaves_no_run_dir[ValueError|RuntimeError]` (launcher cleanup) and `test_install_layout_mid_failure_removes_run_root_sidecars` (adapter sidecar removal). **Verified flipping**: with the two fixes stashed these run as 3 failed; with the fixes applied, 27 passed.
4. **(evidence) native build + bounded GL launch** — built `pikmin_pc` (nectar.exe); a real `slot.py run gl l05` launch with `PIKMIN_P2_ROOM_WINDOW=960x540` + `PYTHONUTF8=1` reached the room preview with the 960×540 centred window; the family bank load is blocked by family-lane artifacts (below).

### Ordered commits / dirty state

- **Root** `deepseek/p2-l05`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`. Clean. Full ordered list now (includes the fix3 items `8510b02`, `e12c429`, `5ec78d6` that the earlier list stopped short of):
  1. `7ab7d79` identity-to-runtime binding → 2. `642e398` doc → 3. `9a3b647` handoff → 4. `021fafa` review fixes → 5. `dfb83a3` handoff → 6. `545edbe` review fixes 2 → 7. `8510b02` handoff → 8. `e12c429` slice 2 → 9. `5ec78d6` review fixes 3 → 10. **`b4263a8` slice 3** (new).
- **Native** `deepseek/p2-l05-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Clean. **No change** — the bank/sidecar readers already exist on the base (`pc_p2_enemy.cpp`, `pc_p2_dwarf_orange.cpp`).

### Build evidence (`output/dsw/l05-build-evidence.txt`)

```
2026-09-14T21:23:50 lane=l05 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l05-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l05-build\bin\nectar.exe sha256=039db847a1818fb41ee7c3a3dd90e5f5c027619b58af41e522b9d8f0ea65fbdb ninja_n="ninja: no work to do." seconds=126
```

### Native launch attempt (bounded, `slot.py run gl l05`)

- Staged Snow + Dwarf Orange (15+15 room models) through the **real** adapter path into a real P1-retail junction overlay; `install_layout` produced `courses/pikmin2room/{snow,dwarf_orange}_*.mod` plus `p2-snow*.txt` and `p2-dwarf-orange-*.txt` at the run root.
- `nectar.exe --experimental-pikmin2-room` booted with the **960×540 windowed + centred** preview window (adoption evidence) and reached `[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`, then aborted at `pc_p2_preview_setup` with `P2 preview: duplicate treasure` (exit 3).
- Root cause: I overlaid the **stock P1 `chal0`** generator set, which exposes two `pr05` treasures; the single-treasure preview layout (`preview_pikmin2_room.generator()` + empty `plants.gen`) is required and the converted room (`pikmin2-room105`) is absent from `C:/Users/alari/pikmin-randomizer/output/`.
- **Bank-load markers are already on the base and consume exactly what `install_layout` stages** — `P2_SNOW_BANK` / `P2_ENEMY_READY species=YellowKochappy` (`pc_p2_enemy.cpp:234`/`:128` reading `p2-snow.txt:147`, `p2-snow-actors.txt:239`, `courses/pikmin2room/snow_*.mod:180`); `P2_DWARF_ORANGE_BANK` / `P2_ENEMY_READY species=BlueKochappy source_id=44` (`pc_p2_dwarf_orange.cpp:84`/`:82` reading `p2-dwarf-orange-{profile,bank,actors}.txt:35`, `courses/pikmin2room/dwarf_orange_*.mod:52`). Retail P1 assets contain none of these files, so there is no retail fallback for them.

### Tests run

- `py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q` → **27 passed**.
- Wider lane-05-adjacent subset (install_binding, family_install, staging, session_staging, seed_bridge, seed_generation, dwarf_orange, dwarf_orange_install, enemy, roster) → **139 passed**.
- `py -3.12 scripts/probe_p2_install_binding.py --output <out>` → **passed** (two-identity `runner.launch` staging, cache replay `[False, True]`, 15+15 room models, both actor files, wrong-source fail-closed `bad-session run dirs: 0`).

### Six-gate update (unchanged: content-level provider lane)

Staging/install binding for BOTH cohort dwarfs remains **PASS at the content level** (real runner entry point, cache replay, wrong/missing content fail-closed, and now full run-tree + run-root sidecar cleanup on any failure). The live native bank-load/spawn gates remain **UNTESTED** and are blocked below; no gameplay PASS is claimed.

### Remaining blockers (all non-lane-05)

- **Lane 13 / family:** the **real** Snow/Dwarf pose banks (render-able `.mod` from `pikmin2_dwarf_orange_bank.build`/`pikmin2_enemy.extract`) — my synthetic chunk-bank passes the hash/chunk pre-flight but cannot be `gameflow.loadShape`-rendered, so a live `P2_*_BANK` run needs the family bank artifact.
- **Lane 13 / family:** Research Pod assets (`p2-pod.txt`/`pod.mod`) — `pc_p2_snow_setup` refuses to load the Snow bank in preview mode without a Pod (`pc_p2_enemy.cpp:161`).
- **Lane 01 / shared asset:** `pikmin2-room105` converted room (`room.mod`/`room.ini`/`treasure.mod`) — absent; the single-treasure preview generator/room needs it.
- **Lane 02 (#438):** admission set still empty; probes/tests monkeypatch `admitted_ids`.

### Reproduction

```powershell
py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q
```

### Subagent usage (slice 3)

This slice ran with **no subagents**: the `task` subagent tool was not available in this execution session, so I did the source audit, candidate inventory and test scaffolding myself (the brief's split was applied as a mental checklist instead). Honest cost: the read-heavy native audit (`pc_p2_enemy.cpp`/`pc_p2_dwarf_orange.cpp`/`pc_p2_preview.cpp`/`gameSetup.cpp`/`Generator.cpp`) consumed the bulk of my context that two `explore` subagents would otherwise have absorbed. Net estimate: **+~25 min** versus the intended 3-way parallel split, with no correctness risk (single-owner, no reconciliation drift).
