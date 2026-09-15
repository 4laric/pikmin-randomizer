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

Third bounded slice: fold the two fix3 advisory cleanup gaps into the launcher/adapter (with flip tests), then prove end-to-end that the staged real banks and sidecars are the ones the engine loads.

### Deliverables

1. **(root) `randomizer/runner.py`** — `_launch` now removes the run tree on **any** install failure (`except Exception`, was `except StagingError`). A `ValueError` or an adapter `RuntimeError` from `install_layout` no longer leaves `runs/<token>/{bootstrap.txt,state.txt}` behind.
2. **(root) `experimental/pikmin2_family_install.py`** — `install_layout`'s mid-install cleanup now also removes run-root sidecars an adapter already copied (e.g. `p2-snow.txt` from `pikmin2_enemy.install`), preserving only `SESSION_FILES` and the (not-yet-written) binding receipt. The run-root allowlist is shared with `_content_files` via a new `_installer_sidecar(path)` helper (deduplicates the `:277`/`:448` loops the review flagged).
3. **(root tests) two flip-tests in `tests/test_pikmin2_install_binding.py`** — `test_launch_install_error_leaves_no_run_dir[ValueError|RuntimeError]` + `test_install_layout_mid_failure_removes_run_root_sidecars`. **Verified flipping**: with the fixes stashed → 3 failed; applied → 27 passed.
4. **(proof) native cohort load** — `scripts/probe_p2_cohort_native.py` (new) stages Snow + Dwarf Orange + Pod through `install_layout` using the **preview-generator room** (`scripts/preview_pikmin2_room` overlay + the lane-20 converted `pikmin2-room105` copy) and the **real** banks, then launches `nectar.exe --experimental-pikmin2-room` via `slot.py run gl l05` and asserts the bank/sidecar load markers.

### Native cohort load (bounded, `slot.py run gl l05`, PASS)

Roster: `preview_pikmin2_room.generator()` + two clean Chappy rows (`211001` Dwarf Orange, `5001` Snow) over the converted room; `install_layout` staged the **real** `p2-dwarf-orange-bank` (64 poses) + Snow bank (60 poses) + Pod into `courses/pikmin2room` and the run root. Log markers (evidence: `l05-out/slice3b/native.log` + `evidence.json` `passed=true`):

```
[PC Port] Experimental preview window set to 960x540 windowed and centered ...
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_SNOW_BANK poses=60 mod_bytes=960000 texture_attach_calls=1 load_seconds=0.020 ...
P2_ENEMY_READY species=YellowKochappy native_family=Chappy generator=5001 behavior=P1
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 ... health=250.0 ...
P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000 texture_attach_calls=1 load_seconds=0.021
P2_DWARF_ORANGE_DRAW corpse=0
P2_SNOW_DRAW corpse=0
```

`P2_*_BANK` is the engine parsing the staged bank; `P2_ENEMY_READY species=…` is the staged sidecar identity line; `P2_*_DRAW corpse=0` proves the real (render-able) banks are actually drawn — not just hash-checked. The room's `default.gen` is the curated 25-row roster (20 reds + 1 treasure + 2 Chappies), not the stock 80-generator set, so there is no “duplicate treasure” abort and **no retail fallback** (the bank/sidecar files exist only in the private staged tree).

### Ordered commits / dirty state

- **Root** `deepseek/p2-l05`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`. Clean. Ordered list:
  1. `7ab7d79` binding → 2. `642e398` doc → 3. `9a3b647` handoff → 4. `021fafa` review fixes → 5. `dfb83a3` handoff → 6. `545edbe` review fixes 2 → 7. `8510b02` handoff → 8. `e12c429` slice 2 → 9. `5ec78d6` review fixes 3 → 10. `b4263a8` slice 3 (cleanup fixes + flip tests) → 11. `0f2e2e1` handoff (superseded) → 12. `630f622` slice 3b (native-cohort proof + `_installer_sidecar` dedup).
- **Native** `deepseek/p2-l05-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Clean. **No change** — the bank/sidecar readers already exist on the base (`pc_p2_enemy.cpp`, `pc_p2_dwarf_orange.cpp`).

### Build evidence (`output/dsw/l05-build-evidence.txt`)

```
2026-09-14T21:23:50 lane=l05 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l05-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l05-build\bin\nectar.exe sha256=039db847a1818fb41ee7c3a3dd90e5f5c027619b58af41e522b9d8f0ea65fbdb ninja_n="ninja: no work to do." seconds=126
```

### Native readers consume exactly what `install_layout` stages (no retail fallback)

- Snow: `pc_p2_enemy.cpp` opens `p2-snow.txt` (`:147`), `courses/pikmin2room/snow_*.mod` (`:180`), `p2-snow-actors.txt` (`:239`); prints `P2_SNOW_BANK` (`:234`) and `P2_ENEMY_READY species=YellowKochappy` (`:128`).
- Dwarf Orange: `pc_p2_dwarf_orange.cpp` opens `p2-dwarf-orange-{profile,bank,actors}.txt` (`:35`), `courses/pikmin2room/dwarf_orange_*.mod` (`:52`); prints `P2_DWARF_ORANGE_BANK` (`:84`) and `P2_ENEMY_READY species=BlueKochappy source_id=44` (`:82`).
- Retail P1 assets contain none of these files; the Snow preview Pod gate (`pc_p2_enemy.cpp:161`) is satisfied by the staged `p2-pod.txt` + `pod.mod`.

### Tests run

- `py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q` → **27 passed**.
- Wider lane-05-adjacent subset (install_binding, family_install, staging, session_staging, seed_bridge, seed_generation, dwarf_orange, dwarf_orange_install, enemy, roster) → **139 passed**.
- `py -3.12 scripts/probe_p2_install_binding.py --output <out>` → **passed** (two-identity `runner.launch` staging, cache replay `[False, True]`, 15+15 room models, both actor files, wrong-source fail-closed `bad-session run dirs: 0`).
- `py -3.12 scripts/probe_p2_cohort_native.py stage/run …` under `slot.py run gl l05` → **passed** (`evidence.json` `passed=true`; all six markers present, quotes above).

### Six-gate update (installation/provider lane)

- **Installation acceptance (A-content / G-product): PASS at the content level** — real runner staging, cache replay, wrong/missing content and interrupted staging fail-closed, full run-tree + run-root sidecar cleanup.
- **Live native spawn/visual bind: PASS (stage/bank + sidecar identity + draw observed)** — the engine loads and draws the staged real banks (`P2_*_BANK`, `P2_ENEMY_READY`, `P2_*_DRAW`). This is a private staged arena, not a generated-session admission, and no combat/lifetime gameplay PASS is claimed (family lane 13 + QA 33 own those).

### Remaining blockers

- **Lane 02 (#438):** admission set still empty; probes monkeypatch `admitted_ids`, so this stays a private arena proof, not an ordinary generated-session spawn.
- **Lane 13 / family:** the Pod (`p2-pod.txt`/`pod.mod`) is not a lane-05 family sidecar — `install_layout` does not stage it; the proof copies it from the family's cohort-arena run root. If generated-session Snow admission is to reach `P2_SNOW_BANK` in preview mode, the Pod staging belongs to lane 13 (or a lane-05 Pod adapter), citing `pc_p2_enemy.cpp:161`.

### Reproduction

```powershell
py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q
# native cohort proof (real assets):
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l05 -- py -3.12 scripts/probe_p2_cohort_native.py run --stage <staged-run> --exe <nectar.exe> --out <dir>
```

### Subagent usage (slice 3)

Task-tool subagents unavailable; worked solo (see the slice-3 fix note). Net +~25 min vs. the intended 3-way split (read-heavy native audit done in this context).

## Slice 4

Fourth slice: the generated seed end-to-end through staging — a real `randomizer.seed.generate` seed (one admitted identity on an injected cohort) staged through the **real runner entry point** (`runner.launch` → `install_layout`), then booted in `nectar.exe --experimental-pikmin2-room` and proven to load exactly the identity/slot the seed chose.

### Deliverables

1. **`scripts/run_p2_generated_seed.py` (new)** — `stage` generates the seed (injecting `bridge.admitted_ids`, lane 02/03 pattern) and calls `runner.launch(assets=curated-retail, p2_content=real-content, p2_actors=seed-targets)`; writes the lane-04 `p2-placement-slots.txt` sidecar (`generator → slot uid`) and the Pod for Snow. `run` boots `nectar.exe` (bounded), and asserts the exact identity set (`P2_ENEMY_READY`, `P2_*_BANK`, `only_seed_identity`, `no_*_unadmitted`) plus the roster/fallback checks.
2. **`experimental/pikmin2_seed_evidence.py` (new)** — `cohort_markers(text)` / `ready_species(text)` / `find_mingw()` (env `MINGW_BIN` → PATH → fallback), shared by the probes and the flip test.
3. **`scripts/probe_p2_cohort_native.py`** — slice-3b review fixes folded in: `passed` now requires `timed_out or returncode==0`; added `roster_read`/`roster_curated`/<`read <N> generators`> + `no_missing_room` (absence of `FAILED to open assets/dataDir/courses/pikmin2room/`); dropped the unused `retail_root` parameter + `mkdir(exist_ok=True)`; MinGW via `MINGW_BIN` env with fallback; preserves `stage.json` and `p2-binding-receipt.json` under `--out`. `build_retail`/`build_content` are now `identities`-parameterised so the roster carries exactly the admitted cohort.
4. **`tests/test_pikmin2_seed_evidence.py` (new)** — flip tests: a stripped `P2_*_BANK` or `P2_ENEMY_READY` line flips its marker (8 tests).

### Native proof (bounded `slot.py run gl l05`, both identities PASS, evidence under `l05-out/`)

- **Dwarf Orange only** (`--cohort 44`, seed `seed-slice4`): bindings `[{target:"401", source_id:44, enum_name:"BlueKochappy"}]`; log has `default: read 24 generators`, `P2_ENEMY_READY species=BlueKochappy source_id=44  generator=211001`, `P2_DWARF_ORANGE_BANK poses=64`; `observed_species == ["BlueKochappy"]`, no `YellowKochappy`. Evidence `l05-out/slice4/{native.log,evidence.json,seed-manifest.json,stage.json,p2-binding-receipt.json}`.
- **Snow only** (`--cohort 45`, seed `seed-slice4-snow`): bindings `[{target:"401", source_id:45, enum_name:"YellowKochappy"}]`; the Pod (`p2-pod.txt` + `pod.mod`) is staged; log has `P2_SNOW_BANK poses=60`, `P2_ENEMY_READY species=YellowKochappy  generator=5001`; `observed_species == ["YellowKochappy"]`, no `BlueKochappy`. Evidence `l05-out/slice4-snow/…`.

In both, `passed=true` with `timed_out=true` (45 s bound, markers flushed before retire): exactly the seed-chosen identity and slot (`generator_slots=[[211001|5001, 401]]`), nothing else.

### Pod ownership decision (as asked)

The Pod (`p2-pod.txt`/`pod.mod`) is a preview/reward anchor, not enemy-family content: `pc_p2_snow_setup` gates preview-mode Snow on `pc_p2_preview_goal()` (the `podAnchor` that `pc_p2_preview.cpp` establishes from `p2-pod.txt`), at `pc_p2_enemy.cpp:161`. Lane-05's `install_layout` is identity-keyed (`resolve_family`/`_OVERRIDES`), stage-by-`enum_name`, and owns only enemy family adapters — a source-id-less Pod has no place in that layout. **Conclusion: the Pod belongs in lane 13** (its `pikmin2_mixed_bulborb_runtime._install_snow` already stages `p2-pod.txt`/`pod.mod`), not lane 05's layout; lane 06 (rewards) is the fallback owner for a non-preview Pod path. My `run_p2_generated_seed.py` stages it only as a preview-enabling step so `pc_p2_enemy.cpp:161` no longer blocks Snow, and labels it `pod.root` not family content.

### Ordered commits / dirty state

- **Root** `deepseek/p2-l05`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`. Clean. Ordered: `7ab7d79` → `642e398` → `9a3b647` → `021fafa` → `dfb83a3` → `545edbe` → `8510b02` → `e12c429` → `5ec78d6` → `b4263a8` → `0f2e2e1` → `630f622` → `cc63388` → **`e698d49` slice 4**.
- **Native** `deepseek/p2-l05-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Clean. **No change** — the bank/sidecar readers and the preview Pod/treasure consumers are already on the base.

### Build evidence (`output/dsw/l05-build-evidence.txt`)

```
2026-09-14T21:23:50 lane=l05 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l05-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l05-build\bin\nectar.exe sha256=039db847a1818fb41ee7c3a3dd90e5f5c027619b58af41e522b9d8f0ea65fbdb ninja_n="ninja: no work to do." seconds=126
```

### Tests run

- `py -3.12 -m pytest tests/test_pikmin2_install_binding.py tests/test_pikmin2_seed_evidence.py -q` → **35 passed** (27 + 8 flip tests).
- `run_p2_generated_seed.py stage/run` (`--cohort 44` and `--cohort 45`) under `slot.py run gl l05` → **both `passed=true`** (evidence JSON under `l05-out/slice4*`).

### Six-gate update (installation/provider lane)

- **Generated-session staging (A / G-product): PASS** — a generated seed's `p2_layout` binds an admitted identity to a slot, `runner.launch` stages it, and the engine loads exactly that identity's bank/sidecar at that slot (plus the seed's `P2_PLACEMENT_SLOTS` sidecar row), nothing else.
- **Live spawn/combat/lifetime gameplay gates:** still family lane 13 + QA 33; the placement-slot native `P2_PLACEMENT_SLOT`/`P2_SEED_RESOLVE` probe is lane 04's native hook (not on `b805d9c6`), so this slice proves the lane-05 content binding (bank + READY identity + actor generator), not lane 04's placement probe markers.

### Remaining blockers

- **Lane 02 (#438):** committed admission still denies by default; the cohort is injected for the seed (documented, same as lane 02/03/04 seed tests).
- **Lane 13:** own the Pod stage for Snow preview-mode (see decision above); lane 04's native placement probe for the `P2_PLACEMENT_SLOT` runtime join.

### Reproduction

```powershell
py -3.12 -m pytest tests/test_pikmin2_seed_evidence.py -q
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l05 -- py -3.12 scripts/run_p2_generated_seed.py run --exe <nectar.exe> --out <staged-out-dir>
```

### Subagent usage (slice 4)

Task tool still absent; worked solo.

## Slice 5

Fifth slice: **the staged seed resolves on the wave native, end to end.** Point the exe at a
self-built `claude/p2-deepseek-wave-native` (tip `b56b97eb`), stage the generated seed through
the real runner exactly as in slice 4, and show the seed's chosen slot resolving natively in one
log: lane-04 `P2_PLACEMENT_SLOT`, lane-03 `P2_SEED_RESOLVE source_id=<n>`, and the family
`P2_ENEMY_READY` for the same generator — plus the Snow run with the Pod present and
`P2_SNOW_BANK` loaded from the staged tree.

### Deliverables

1. `scripts/run_p2_generated_seed.py` — `placement_document` now uses the REAL lane-04 catalog
   (`p2_placement_catalog.build_document()`), restricted to one stage-0 ground slot (the seed's
   chosen slot uid `5465461`), cohort acceptance stamped. `boot_native` boots with
   `--randomizer-seed <bootstrap>` so the wave native parses the `ENEMY_P2` bridge (a full room
   session would hold the preview). `run()` builds its checks from `cohort_markers`, pops the fixed
   bank/ready keys, adds `no_bank_<token>` (an out-of-cohort source must emit neither its bank nor
   its READY line), and adds the wave-native resolve markers.
2. `experimental/pikmin2_seed_evidence.py` — `resolve_markers(text, cohort, generator_for_source)`
   requires the lane-03 `P2_SEED_RESOLVE source_id=<n> target=<uid>` and the lane-04
   `P2_PLACEMENT_SLOT generator=<g> slot=<uid>` to agree on the same uid for the identity's
   generator, alongside the family `P2_ENEMY_READY`; out-of-cohort sources must emit neither.
3. `tests/test_pikmin2_seed_evidence.py` — flip tests for the resolve markers (stripping
   `P2_SEED_RESOLVE` / `P2_PLACEMENT_SLOT` flips the check), 12 tests.

### Native build (own worktree at the current tip)

`output/dsw/native-l05-wave` (detached at `claude/p2-deepseek-wave-native` tip), built through
`build_lane.py l05-wave`; `output/dsw/l05-wave-build-evidence.txt`:

```
2026-09-14T23:26:29 lane=l05-wave target=pikmin_pc native=b56b97eb9a01ecc0bc013a4ed46d1a13bf166585 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l05-wave-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l05-wave-build\bin\nectar.exe sha256=6396e865a8f02367edf33c2a889e6c873b43f029437c78a0daf0678a0b550223 ninja_n="ninja: no work to do." seconds=122
```

### Runtime evidence (both identities, `slot.py run gl l05`)

Evidence lives at the absolute `C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/slice5/{cohort44,cohort45}` (equal to repo-relative `output/dsw/l05-out/slice5/…`):

- **Dwarf Orange (`--cohort 44`)**: `cohort44/native.log` — `P2_SEED_RESOLVE source_id=44 target=5465461`,
  `P2_ENEMY_READY species=BlueKochappy source_id=44 ... generator=211001`, `P2_DWARF_ORANGE_BANK poses=64`,
  `P2_PLACEMENT_SLOT generator=211001 slot=5465461`, `P2_PLACEMENT_PROBE actors=1`. `evidence.json`
  `passed=true` (all checks, incl. `slot_agree_BlueKochappy` + `no_*_YellowKochappy`).
- **Snow (`--cohort 45`)**: `cohort45/native.log` — Pod `pod.mod` opened (`size 72832`),
  `P2_SNOW_BANK poses=60 ... load_seconds=0.032`, `P2_ENEMY_READY species=YellowKochappy ... generator=5001`,
  `P2_SEED_RESOLVE source_id=45 target=5465461`, `P2_PLACEMENT_SLOT generator=5001 slot=5465461`.
  `evidence.json` `passed=true` (incl. `slot_agree_YellowKochappy` + `no_*_BlueKochappy`).

Both use the seed's `p2-placement-slots.txt` sidecar (`_70` → slot uid) and the `ENEMY_P2` bootstrap
target `5465461`; the native reports `P2_PLACEMENT_SLOT ... xyz=0 terrain=none route=0` because the
arena generator sits off the converted room's terrain mesh (a lane-04 placement-quality note, not a
binding failure: the generator→slot→source join and the family READY/bank load are all observed).

### Six-gate evidence (formatted for lane-02 ingestion)

### BlueKochappy (44)

| Gate | Result | Evidence |
|---|---|---|
| 1. identity_spawn | PASS | output/dsw/l05-out/slice5/cohort44/native.log — P2_SEED_RESOLVE source_id=44 target=5465461; P2_PLACEMENT_SLOT generator=211001 slot=5465461; P2_ENEMY_READY species=BlueKochappy source_id=44 generator=211001; P2_DWARF_ORANGE_BANK poses=64 |
| 2. movement_animation | UNTESTED | family lane 13 |
| 3. attacks_receivers | UNTESTED | lanes 10/13 |
| 4. death_corpse | UNTESTED | lane 13 |
| 5. transport_reward | UNTESTED | lane 06 |
| 6. cleanup_reentry | UNTESTED | lane 07 |

### YellowKochappy (45)

| Gate | Result | Evidence |
|---|---|---|
| 1. identity_spawn | PASS | output/dsw/l05-out/slice5/cohort45/native.log — P2_SEED_RESOLVE source_id=45 target=5465461; P2_PLACEMENT_SLOT generator=5001 slot=5465461; P2_ENEMY_READY species=YellowKochappy generator=5001; pod.mod loaded; P2_SNOW_BANK poses=60 |
| 2. movement_animation | UNTESTED | family lane 13 |
| 3. attacks_receivers | UNTESTED | lanes 10/13 |
| 4. death_corpse | UNTESTED | lane 13 |
| 5. transport_reward | UNTESTED | lane 06 |
| 6. cleanup_reentry | UNTESTED | lane 07 |

The `identity_spawn` PASS is a lint-clean, cited, natural resolution (the seed's chosen source id
resolves at ordinary `GenObjectTeki::birth` with the real bank, no P1 fallback). The admission
cohort remains empty in the committed ledger; these runs enable it only for the seed (the same
pattern lane 02/03/04 seed tests use) — that shaping is not part of the gate-1 claim.

### Remaining blockers

- **Lane 02 (#438):** commit/ingest these `identity_spawn` rows (the committed ledger still denies by
  default; the runs enable the cohort locally).
- **Lane 04:** the arena generator is off the converted room's terrain mesh
  (`P2_PLACEMENT_SLOT ... xyz=0 terrain=none route=0`); native XYZ/terrain/route evidence for a
  carrier-compatible slot remains lane 04's.
- **Lane 13:** Pod staging for preview-mode Snow stays lane 13 (slice 4 Pod decision unchanged).

### Tests run

- `py -3.12 -m pytest tests/test_pikmin2_seed_evidence.py tests/test_pikmin2_install_binding.py -q` → **39 passed**.
- `run_p2_generated_seed.py stage/run` (cohort 44 and 45) under `slot.py run gl l05` → **both `passed=true`**.

### Subagent usage (slice 5)

The `task` tool was available; worked solo anyway (the read-heavy native/ingest audit was done in
this context to keep the wave-native reproduction precise). One subagent-style split would have been
possible but added no throughput here.

## Slice 6

Sixth slice: **third KochappyBase adapter (Kochappy Red, source 1)**, completing the family
adapters (`kochappy` + `dwarf_orange` + `snow`). Consumes the existing family stager
`experimental.pikmin2_kochappy_bank.install` through the generated-session launcher/cache path,
with a `validate()` hook, a real-adapter test, and three-identity staging.

### Source IDs and files owned

- **Concrete consumer:** Kochappy — Dwarf Red Bulborb, source id **1** (enum `Kochappy`). Its
  assets model `Kochappy` and the existing bespoke installer
  `experimental.pikmin2_kochappy_bank.install(imported, run, generator_ids)` are consumed as-is;
  lane 05 only adapts and sequences them. Snow (45) and Dwarf Orange (44) adapters are untouched.
- **Owned/edited files (root only):**
  - `experimental/pikmin2_family_install.py` — `IDENTITY_FAMILY` gains `1`/`kochappy` →
    `kochappy`; new `_validate_kochappy` + `_adapt_kochappy`; `ADAPTERS` gains `kochappy`.
  - `tests/test_pikmin2_install_binding.py` — `make_kochappy_source` helper + 4 new tests;
    `test_resolve_family_unknown_identity` updated (1/`Kochappy` now valid).
  - `docs/PIKMIN2_CONTENT_STAGING.md` — binding section + limitations updated (three adapters).

### Ordered commits / dirty state

- **Root** branch `deepseek/p2-l05`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`. Ordered: prior slices
  (`7ab7d79` → … → `958f9a6` slice 5) plus this slice's `lane05: slice 6 - Kochappy Red adapter (#442)`.
  Clean at head after commit.
- **Native** branch `deepseek/p2-l05-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`.
  **No changes** (`git status` clean). Lane 05 required no native edits: the Red config reader
  (`pc_port/pc_p2_kochappy.cpp`, reads `p2-kochappy-*.txt`, emits
  `P2_ENEMY_READY species=Kochappy source_id=1`) already exists on the base.

### Interfaces/hooks touched and why

- `IDENTITY_FAMILY` gains `1: 'kochappy'` and `'kochappy': 'kochappy'`; `resolve_family(1)` /
  `resolve_family("Kochappy")` / `resolve_family("kochappy")` → `kochappy`, anything else unchanged.
  Narrow by design; still raises `ValueError` for unknown identities (no silent P1 fallback).
- `_validate_kochappy(source)` (new): requires `<source>/kochappy-bank.json` +
  `<source>/p2-kochappy-profile.txt` and `(schema, species, source_id, health) ==
  (1, 'Kochappy', 1, 200)`; otherwise `StagingError` before any destination write.
- `_adapt_kochappy(source, run, actors)` (new): delegates to
  `experimental.pikmin2_kochappy_bank.install(source, run, [generator, ...])` and returns a
  small receipt (`species`/`source_id`/`generators`); the family installer itself returns `None`.
- `ADAPTERS['kochappy'] = {'install', 'validate'}`. The `install_layout` plans loop, source-id/enum
  agreement check, session cache, and launcher wiring are untouched and cover the third identity
  without modification.

No shared native files and no family-owned extractors were modified.

### Build evidence

No native rebuild for this slice (no native/engine change). Native branch is clean at the base;
the last lane-05 build evidence remains `output/dsw/l05-build-evidence.txt` (slice 3 era,
`pikmin_pc` on `b805d9c6`) and the slice-5 wave build (`output/dsw/l05-wave-build-evidence.txt`,
tip `b56b97eb`). A `ninja -n` no-work check is vacuous without a rebuild; the Python evidence below
is the slice's proof.

### Fixture adoption evidence

Not applicable and reported honestly: no real-GL runtime fixture for this slice. The Kochappy
evidence is the real family installer executed at the Python level against a synthetic bank whose
schema matches `tests/test_pikmin2_kochappy_bank.py`'s accepted fixture — not a wave-native
resolve run (no real Red bank is available for a GL run, and the admission ledger is still empty).
The 960×540 centred-window / live-squad adoption requirement remains for the next runtime
acceptance run (family lane 13 + QA 33).

### Six-gate table (provider lane; honest)

### Kochappy (1)

| Gate | Result | Evidence |
|---|---|---|
| 1. identity_spawn | UNTESTED | install-layer binding proven via the real `pikmin2_kochappy_bank.install` (identity + bank/profile/motion/file hashes all checked, no P1 fallback) — tests/test_pikmin2_install_binding.py; ordinary-spawn resolve not run (no real Red bank for a wave-native run) |
| 2. movement_animation | UNTESTED | family lane 13 |
| 3. attacks_receivers | UNTESTED | lanes 10/13 |
| 4. death_corpse | UNTESTED | lane 13 |
| 5. transport_reward | UNTESTED | lane 06 |
| 6. cleanup_reentry | UNTESTED | lane 07 |

Gate 1 is UNTESTED (not PASS): the content binding is proven but there is no ordinary-spawn
resolve evidence for source 1, so nothing here advances the gate ledger. No gameplay PASS is
claimed and no injected combat/lifecycle run is presented as one.

### Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q` → **31 passed** (incl. the 4 new
  Kochappy tests: resolve, real adapter, three-family staging, validate fail-closed).
- Wider lane-05 subset (install_binding, family_install, staging, session_staging, seed_bridge,
  seed_generation, dwarf_orange_install, kochappy_bank, seed_evidence, enemy_roster) →
  **149 passed, 1 failed**: the failure is the pre-existing
  `test_pikmin2_kochappy_bank.py::test_compiled_family_policy`, which compiles C++ against
  `l05-root/native/pc_port` — that directory is absent by worktree design (brief §3), so it fails
  identically with and without this slice. Unrelated; not a regression.

### Assumptions made

- The Kochappy adapter's source layout mirrors `pikmin2_kochappy_bank.build` output (flat dir with
  `kochappy-bank.json` + `p2-kochappy-bank.txt` + `p2-kochappy-profile.txt` + `kochappy_*.mod`);
  a real family bank is produced by lane 13, not lane 05.
- `actor_bindings` (target → native generator id) remains a caller input, resolved by lane 03/04 +
  native `ENEMY_P2`, not this lane.
- Kochappy Red is a randomizable `enemy` candidate (spawnable, own id, in the info table); adapter
  presence is not admission (that stays lane 02).

### Remaining blockers naming the provider lane

- **Lane 02 (#438):** admission set still empty; Kochappy (1) joins Snow/Dwarf Orange as adapter-ready
  but unadmitted.
- **Lane 13 / family:** produce the real Kochappy Red bank and accept the native actor binding
  (`pc_p2_kochappy.cpp` reader already exists) so the staged content is consumed by a live actor;
  Pod staging for Snow stays lane 13.
- **Lane 04:** native XYZ/terrain/route evidence for carrier-compatible slots remains lane 04's.
- **Lane 01:** export/merge the launcher/`experimental` changes into the maintained line after review.

### Reproduction (one command)

```powershell
py -3.12 -m pytest tests/test_pikmin2_install_binding.py -q
```

### Subagent usage

- **explore #1 — Kochappy Red stager audit:** extracted `pikmin2_kochappy_bank` PROFILE/HEADER,
  `build`/`install` inputs, the identity tuple, every `ValueError`, the sibling overlap and room
  rules, plus the synthetic-fixture shape and roster confirmation. Used as-is to author
  `_validate_kochappy`/`_adapt_kochappy` and the doc wording. Saved ~30 min of contract reading.
- **explore #2 — Kochappy candidate inventory:** confirmed `IDENTITY_FAMILY`/`ADAPTERS` had no `1`/
  `kochappy`, listed every Kochappy module/test/doc, and pinpointed the exact tests needing updates.
  Used as-is; prevented reimplementing the family bank and scoped the test edits.
- **general #3 — test scaffolding:** wrote `make_kochappy_source` + the 4 tests and updated the
  unknown-identity list against my contract; reported 3 missing-contract failures vs 0 fixture
  mismatches. Corrected: the "real adapter" test needed my `_adapt_kochappy` to return a receipt
  (family installer returns `None`), which the test already assumed — I implemented to that
  contract. Net saved the full test-authoring pass; cost was reconciling the receipt shape.
