# Muse contributor 61: BombOtakara93 natural observer slice (#501, parent #447)

Implementation owner: Codex through shared GitHub account 4laric; actual
contributor Muse Spark 1.3 through OpenCode. Attempt
a86d91d2e2e64f4b9bfa07376232662c, generation 1.

Scope: the two remaining BombOtakara93 gates (`identity_spawn`,
`attacks_receivers`). Reuse integrated lane-22 source behavior and the
natural Otakara runner; observe bomb attachment/blast routing without direct
kill/receiver injection. Real family generator identity chain only; no
globally admitted generated slot. Elemental59-62 defaults unchanged.

## 1. Baseline verified

Wave advance report (`docs/PIKMIN2_ROSTER_ADVANCE_REPORT.md`): BombOtakara93
advances `movement_animation`, `death_corpse`, `transport_reward`,
`cleanup_reentry`; blocking `identity_spawn`, `attacks_receivers`.
Lane-22 fix4 (`docs/PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md` Slice 4, Source ID 93
table): gate 1 PARTIAL (bound as a Chappy body, no Bomb payload actor),
gate 3 N/A (`P2_OTAKARA_DISCHARGE_NONE payload_delegated=1`, delegates to
the lane-20 Bomb payload). Source boundary: `initBombOtakara` captures the
separate `EnemyID_Bomb` payload on the `otakara` joint
(`OtakaraBase.cpp:649-677`); damage/earthquake delegate to that payload
(`BombOtakara.cpp:42-87`); blast routing is the lane-20 shared primitive
(`native/pc_port/pc_p2_bombsarai_blast.h`).

## 2. Ordered commits

Root worktree `C:\Users\alari\pikmin-randomizer\output\msw\l61-root`,
branch `codex/muse-l61-bombotakara`, base
`72a2c450d7b9040545de4a440c2c32e2173ea6fa`:
- (this slice) "muse-bombotakara: natural attach/blast observer + tests + handoff (#501)"
  adds `experimental/pikmin2_muse_bombotakara.py`,
  `tests/test_pikmin2_muse_bombotakara.py`,
  `docs/PIKMIN2_MUSE_BOMBOTAKARA_HANDOFF.md`.

Native worktree `C:\Users\alari\pikmin-randomizer\output\msw\native-l61`,
branch `codex/muse-l61-bombotakara-native`, base
`7b9ecaa668fd55332073446cdbdaf6424b209ea7`:
- (this slice) "muse-bombotakara: natural observation seam + fixture (#501)"
  extends `native/pc_port/pc_p2_bombotakara_policy.h`,
  `native/pc_port/pc_p2_bombotakara.h`,
  `native/pc_port/pc_p2_bombotakara.cpp` (additive only) and adds
  `native/tools/p2_muse_bombotakara_fixture.cpp`.

Both worktrees contain only reserved owned files; no shared-hook edits, no
elemental59-62 changes. Root/native branch pushes (if any) are work-branch
only, never default/`p2-integration`/tags/force.

## 3. What changed and why

- `native/pc_port/pc_p2_bombotakara_policy.h`: new additive
  `p2bombotakara_natural` namespace (engine-free): `isInjectedMarker`,
  `isNaturalIdentityBind` (nonzero generator + source 93),
  `isNaturalBlastRouting` (shared primitive + receivers/hits/pikmin_hits
  >= 1). Existing policy semantics untouched.
- `native/pc_port/pc_p2_bombotakara.h/.cpp`: additive observation seam
  `pc_p2_bombotakara_note_attach_natural` (logs `P2_BOMBOTAKARA_ATTACH ...
  joint=otakara natural=1`) and
  `pc_p2_bombotakara_note_bomb_hit_natural` (logs `P2_BOMBOTAKARA_BOMB_HIT
  ... interaction=InteractBomb natural=1`). Observation only: no health,
  state, transport, kill, or receiver calls; sidecar stub behavior unchanged.
- `experimental/pikmin2_muse_bombotakara.py`: pure log observer `validate`.
  Natural identity requires `P2_OTAKARA_BIND ... source_id=93` (nonzero
  generator) + `P2_ENEMY_READY species=BombOtakara ...
  attack=payload_delegated` + natural ATTACH; natural attack requires a
  routed `P2_BOMBOTAKARA_BLAST ... shared_primitive=1` (receivers/hits/
  pikmin_hits >= 1) + natural BOMB_HIT. Any injection marker
  (`P2_BOMBOTAKARA_INJECT`, `p2-bombotakara-inject`, `injection=1`, fixture
  guard Pikmin, `*_DEATH_INJECT`) fails the natural checks. Launches,
  stages, and touches nothing.
- `tests/test_pikmin2_muse_bombotakara.py`: 9 unit tests (good natural log,
  missing attach/blast/hit, zero-hit blast, injected trigger, guard Pikmin,
  nonzero exit, zero generator). All pass; lane-22 otakara suites still pass
  (26 passed), so elemental59-62 behavior is preserved.
- `native/tools/p2_muse_bombotakara_fixture.cpp`: replacement-main fixture
  reusing the lane-22 Otakara runner. Binds through the real family
  generator chain (`p2-dweevil-actors.txt` BombOtakara entry) via
  `pc_p2_otakara_setup`; never writes `p2-bombotakara-native.txt` or
  `p2-bombotakara-inject.txt`; kills nothing and stimulates no receiver.
  Without a real `EnemyID_Bomb` payload actor the blast half stays
  unobserved and the fixture exits with an explicit
  `P2_MUSE_BOMBOTAKARA_BLOCKED reason=no_bomb_payload_actor` marker after a
  bounded tick budget; it never hangs.

## 4. Build evidence

- Private configure+build via the wave leased runner
  (`output/muse-wave/control/leased_run.py`, private build dir
  `C:\Users\alari\pikmin-randomizer\output\msw\native-l61-build`, Ninja +
  MinGW g++, Release, `PIKMIN_NATIVE_JAUDIO=ON`): full link
  `[616/616] Linking CXX executable bin\nectar.exe`, then
  `ninja: no work to do.` Log
  `output/muse-wave/l61/build-1789515339749264600.log`.
  Executable `bin/nectar.exe` SHA-256
  `21da8f205d35aff5a8c902995f0bb65cac0677197bfdc510ad987cb5e7adb5ad`.
- Dedicated fixture via the same leased wrapper (worktree
  `scripts/build_pikmin2_fixture.py`; the maintained-workspace copy predates
  the `@response`-file expansion fix and rejects this Ninja/CMake output, so
  the lane's own pinned script was used and is recorded here):
  `output/muse-wave/l61/fixture-build/` status `built`, `fixture.exe`
  SHA-256 `d645ada5f693fa7c499c805824ef97206a242a08dea53d189827ef970dc26f5d`.
  Provenance `output/muse-wave/l61/fixture-build/provenance.json` pins native
  HEAD `7b9ecaa668fd55332073446cdbdaf6424b209ea7` plus the tracked-modified
  BombOtakara files.
- Ninja note: `ninja.exe` is the Python-bundled binary and is not on the
  default PATH on this host; the lease command prepends its Scripts
  directory. No native/build-randomizer use; no shared AP/BBFT changes.

## 5. Tests

```
py -3.12 -m pytest tests/test_pikmin2_muse_bombotakara.py -q
# 9 passed
py -3.12 -m pytest tests/test_pikmin2_otakara_runtime.py tests/test_pikmin2_otakara_native.py -q
# 26 passed
```

## 6. Six arena gates (natural vs injected)

Source ID: 93 `BombOtakara`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | docs/PIKMIN2_MUSE_BOMBOTAKARA_HANDOFF.md observer requires P2_BOMBOTAKARA_ATTACH joint=otakara natural=1; lane-22 bound Chappy body only, no Bomb payload actor, see docs/PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md fix4-BombOtakara output/l22-out/fix4-BombOtakara/72ff8fec895a46ea8595d380f41f8896/capture/native.log:763 | natural |
| 2. Autonomous movement and animation | PASS (natural, prior) | docs/PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md fix4-BombOtakara output/l22-out/fix4-BombOtakara/72ff8fec895a46ea8595d380f41f8896/capture/native.log:775 P2_OTAKARA_STATE state=flick | natural |
| 3. Attacks and receivers | BLOCKED | docs/PIKMIN2_MUSE_BOMBOTAKARA_HANDOFF.md observer requires routed P2_BOMBOTAKARA_BLAST shared_primitive=1 plus P2_BOMBOTAKARA_BOMB_HIT interaction=InteractBomb; delegation only, see docs/PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md fix4-BombOtakara output/l22-out/fix4-BombOtakara/72ff8fec895a46ea8595d380f41f8896/capture/native.log:778 | natural |
| 4. Death and corpse | PASS (natural, prior) | docs/PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md fix4-BombOtakara output/l22-out/fix4-BombOtakara/72ff8fec895a46ea8595d380f41f8896/capture/native.log:974 P2_OTAKARA_CORPSE pellet=1 | natural |
| 5. Actual transport and reward | PASS (natural, prior) | docs/PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md fix4-BombOtakara output/l22-out/fix4-BombOtakara/72ff8fec895a46ea8595d380f41f8896/capture/native.log:1111 corpse:otakara:349001 receipt | natural |
| 6. Cleanup and re-entry | PASS (natural, prior) | docs/PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md fix4-BombOtakara output/l22-out/fix4-BombOtakara/72ff8fec895a46ea8595d380f41f8896/capture/native.log:1112 P2_OTAKARA_FORGET count=0 | natural |

Prior PASS rows are lane-22 evidence restated for continuity, not new
claims; this slice adds no new runtime PASS. Gates 2/4/5/6 are preserved
unchanged. No runtime was launched in this slice, so no new `native.log`
citation exists yet; the observer, tests, and built fixture above are the
reproducible artifacts. The sidecar `p2-bombotakara-native.txt` profile and
`p2-bombotakara-inject.txt` triggers remain labeled injections and are
explicitly rejected by the observer.

## 7. Exact blocker (gates 1 and 3)

A natural BombOtakara93 attack IS its carried Bomb: source delegates damage
and earthquake to the separate `EnemyID_Bomb` payload (`BombOtakara.cpp:42-87`)
captured on the `otakara` joint (`OtakaraBase.cpp:649-677`). No real payload
actor exists in any integrated runner yet (lane-22 binds the carrier body
only; the lane-20 shared Bomb blast contract covers routing, not the live
payload birth/attachment). Until a real payload actor is born, attached on
the `otakara` joint, and detonated against live receivers through the shared
primitive, gates 1 and 3 cannot advance naturally. The built fixture
(`output/muse-wave/l61/fixture-build/fixture.exe`) is ready to observe
exactly that run once the payload side exists; its BLOCKED exit names the
missing artifact rather than hanging or faking a PASS.

## 8. Reproduction

```powershell
$env:PYTHONUTF8='1'
py -3.12 -m pytest tests/test_pikmin2_muse_bombotakara.py tests/test_pikmin2_otakara_runtime.py tests/test_pikmin2_otakara_native.py -q
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_BOMBOTAKARA_HANDOFF.md
```

Fixture rebuild (leased, private dir):

```powershell
py -3.12 C:/Users/alari/pikmin-randomizer/output/muse-wave/control/leased_run.py --lane-file C:\Users\alari\pikmin-randomizer\output\muse-wave\l61/lane.json -- py -3.12 C:/Users/alari/pikmin-randomizer/output/msw/l61-root/scripts/build_pikmin2_fixture.py --source C:\Users\alari\pikmin-randomizer\output\msw\native-l61 --build C:\Users\alari\pikmin-randomizer\output\msw\native-l61-build --fixture C:\Users\alari\pikmin-randomizer\output\msw\native-l61\tools\p2_muse_bombotakara_fixture.cpp --expected-native-head 7b9ecaa668fd55332073446cdbdaf6424b209ea7 --output C:\Users\alari\pikmin-randomizer\output\muse-wave\l61\fixture-build
```

## 9. Remaining work

- Stage the real `EnemyID_Bomb` payload birth/attachment (provider: lane-20
  Bomb blast/payload contract) and run the built fixture to capture the
  natural ATTACH + routed BLAST/BOMB_HIT markers; then flip gates 1 and 3
  with `native.log:line` citations in a follow-on slice.
- Scene re-entry for the BombOtakara binding (lane-07 harness) stays
  UNTESTED, same as lane-22.
