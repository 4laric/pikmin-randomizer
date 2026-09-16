# Muse lane l67 (fixturetools, #507) — preflight/diagnostic adapter handoff

Slice: **additive fixture-build preflight adapter + focused tests + exact
reproduction of the maintained-builder `@response file` blocker**.
Tooling-only: Source IDs `[]`, no actor, no arena run, no admission claim.
It changes no shared runner, builder, workflow, existing script, or other
lane build; it only adds four reserved files and private-output evidence.

- Parent issues: family/dependency parent #397; wave #491; child #507.
- l52-l61 failure logs were inspected read-only; nothing outside the
  private worktrees was edited.

## Source ID and files owned (all new, additive)

- Root (new):
  - `experimental/pikmin2_muse_fixturetools.py` — dependency-free
    `preflight()`/`diagnose_commands()` plus CLI (`preflight`, `diagnose`).
    Checks, fail-closed in builder order: source identity files, build
    cache presence, fixture/output path validity, `CMAKE_GENERATOR=Ninja`,
    configured-source agreement, cached-compiler/ninja existence (with the
    exact `-DCMAKE_MAKE_PROGRAM=` remediation the leased runner uses),
    expected native HEAD, and read-only `ninja -n -d explain` freshness.
    The `diagnose` subcommand names raw `@...rsp` link lines the
    maintained builder rejects. Never configures, builds, or launches.
  - `tests/test_pikmin2_muse_fixturetools.py` — 19 contract tests: missing
    ninja (remediation names `CMAKE_MAKE_PROGRAM`), wrong generator,
    configured-source mismatch, missing toolchain, output-inside-source,
    bad fixture suffix, malformed expected head, path gates, grammar
    (`@rsp`/empty unparsable, plain compile parses, cmd-wrapper unwrap),
    real l60 link-line diagnosis, clean-command pass, JSON serialisability.
  - `docs/PIKMIN2_MUSE_FIXTURETOOLS_HANDOFF.md` — this file.
- Native (new, engine-independent):
  - `native/tools/p2_muse_fixturetools_fixture.cpp` — stdlib-only
    preflight self-check (`<source-dir> <build-dir>` argv, `P2_MUSE_`
    `FIXTURETOOLS_*` markers, exit 0/1/2). MinGW `-Wall -Wextra -Werror`
    clean; not linked into any game target.

## Ordered commits (clean)

Root branch `codex/muse-l67-fixturetools` (base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`):

- `32106f16a16f9b23d808f3a87300512268e97dbb` lane67: fixture-build preflight adapter + focused tests (#507)
- (this commit) lane67: fixturetools handoff doc (#507)

Native branch `codex/muse-l67-fixturetools-native` (base `7b9ecaa668fd55332073446cdbdaf6424b209ea7`):

- `7b4d63d93d4b096badfe146c34eafb5a612a47ce` lane67: stdlib-only preflight self-check fixture (#507)

## Failure analysis (read-only evidence)

1. Missing-Ninja configures — RESOLVED infra-side, encoded as preflight
   checks. `output/muse-wave/l52/build-1789515393647383000.log`,
   `l53/build-1789515359537683600.log`,
   `l55/build-1789515273429761500.log`,
   `l60/build-1789515268171709400.log`,
   `l61/build-1789515282282896900.log` all show `CMAKE was unable to find
   a build program corresponding to "Ninja". CMAKE_MAKE_PROGRAM is not
   set.` Those invocations passed `-G Ninja` without
   `-DCMAKE_MAKE_PROGRAM`; current
   `output/muse-wave/control/leased_run.py` passes it (Python-ninja path)
   and prepends MinGW + ninja to PATH. Second attempts configured cleanly.
2. Maintained-builder `@response file` rejection — REPRODUCED as the exact
   unresolved blocker. `output/msw/l60-fixture-01/provenance.json` and
   `output/muse-wave/l61/fixture-build/provenance.json` show status
   `rejected`, error `Empty command or unsupported response file`,
   `commands: []`. The real `native-commands.txt` (616 lines) carries the
   `pikmin_pc` link line `... g++.exe ... @CMakeFiles\pikmin_pc.rsp -o
   bin\nectar.exe ...`; it matches the builder's ` -o ` selector, and the
   maintained argv grammar rejects the `@...rsp` argument. Maintained root
   HEAD `ad5be2e2` carries only `c8acb643` (no expansion); wave base
   `72a2c450` carries the #437 fixes `04773078`/`bf9ff77a`/`bf9ce07c`.
   Positive control: `output/msw/l60-fixture-02/provenance.json` is
   `built` (fixture.exe 1839637 bytes) via the worktree script. l61 never
   retried with it; its manual `fixture-build2/fixture.exe` is 0 bytes.

## This lane's reproduction (private output only)

- Leased configure+build: `output/muse-wave/l67/build-1789517060032849300.log`
  exit 0, `ninja: no work to do.`, `bin/nectar.exe` sha256
  `34a6d4cd43c378e46c2e8dda1eec5658bca7014da2fff03d41ca26c118575a31`,
  native head `7b9ecaa6...`, dirty `?? tools/p2_muse_fixturetools_fixture.cpp`.
- Preflight on the real build: status `ok`, all 8 checks pass.
- Maintained-script repro: `output/muse-wave/l67/repro-maintained/provenance.json`
  status `rejected`, error `Empty command or unsupported response file`
  (leased log `output/muse-wave/l67/build-1789517192331058300.log` exit 1).
- Adapter diagnosis of that `native-commands.txt`: 614 selected lines, one
  `response_lines` entry `@CMakeFiles\pikmin_pc.rsp` (diagnose exit 2).
- Worktree-script build: `output/muse-wave/l67/fixture-built/provenance.json`
  status `built`, fixture.exe sha256
  `3e941de8fc2a4dc26440f69178da20f3872cf3f8a38811704ec1ed1054d8bc47`
  (1836904 bytes; leased log
  `output/muse-wave/l67/build-1789517204080783300.log` exit 0).
- Built fixture run: `output/muse-wave/l67/fixture-run.log`,
  `P2_MUSE_FIXTURETOOLS_PREFLIGHT_OK`, exit 0.
- Standalone probe (`-Wall -Wextra -Werror` clean): exit 2 no-argv, exit 1
  bad-paths/unconfigured-build, exit 0 configured build
  (`output/muse-wave/l67/probe-run.log`).
- `tests/test_pikmin2_muse_fixturetools.py`: 19 passed
  (`output/muse-wave/l67/checks.log`).
- `py -3.12 scripts/check_p2_handoff_gates.py
  docs/PIKMIN2_MUSE_FIXTURETOOLS_HANDOFF.md` → EXIT=0 (tooling-only, no
  PASS rows).

## Six-gate table (tooling-only; Source IDs [])

There is no Source ID in this scope, so no identity-specific table can be
bound; every gate is explicitly N/A for tooling, never PASS.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | N/A | Tooling-only lane, Source IDs []; no actor implemented or spawned | natural (no runtime) |
| 2. Autonomous movement and animation | N/A | Tooling-only lane, Source IDs []; no actor implemented or moved | natural (no runtime) |
| 3. Attacks and receivers | N/A | Tooling-only lane, Source IDs []; no combat implemented | natural (no runtime) |
| 4. Death and corpse | N/A | Tooling-only lane, Source IDs []; no death implemented | natural (no runtime) |
| 5. Actual transport and reward | N/A | Tooling-only lane, Source IDs []; no transport implemented | natural (no runtime) |
| 6. Cleanup and re-entry | N/A | Tooling-only lane, Source IDs []; no scene implemented | natural (no runtime) |

Fixture adoption is N/A: no arena was generated and no gameplay run was
attempted; the `built` provenance above covers the isolated
fixture binary only, not window/squad/gameplay acceptance.
## Exact minimal patch recommendation (outside owned files, for #491)

Sync maintained `scripts/build_pikmin2_fixture.py` with wave-base commits
`04773078` (expand link response files through Ninja's graph), `bf9ff77a`
(expand link/archive `@response` files from disk), and `bf9ce07c`
(verified GCC response files for long commands); until then, direct lanes
to invoke `<lane-root>/scripts/build_pikmin2_fixture.py` instead of the
maintained-checkout copy. One-line brief-template fix: the l67 brief's own
fixture-build example uses the maintained path and reproduces the
rejection verbatim. Do not edit the shared runner's pinned flags; the
Ninja-discovery half is already fixed there.

## Remaining work

None in this bounded slice. The blocked lanes (l61-style invocations) need
the integrator's maintained-script sync decision, not another lane-local
adapter. No ADMIT writes, no allowlist edits, no shared-file edits.

## One exact reproduction command

```
cd C:/Users/alari/pikmin-randomizer/output/msw/l67-root
py -3.12 -m pytest tests/test_pikmin2_muse_fixturetools.py -q   # 19 passed
py -3.12 -m experimental.pikmin2_muse_fixturetools diagnose --commands C:/Users/alari/pikmin-randomizer/output/muse-wave/l67/repro-maintained/native-commands.txt   # exit 2, names @CMakeFiles\pikmin_pc.rsp
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_FIXTURETOOLS_HANDOFF.md  # EXIT=0
```
