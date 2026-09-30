# CI builds (native Windows exe and root tests)

Heavy native builds and headless game sessions run in GitHub Actions, not on the
owner's PC (parallel local builds have crashed it). Tracking issue: #937.

## Native: `Windows build` (`native/.github/workflows/windows.yml`)

Runs on `windows-2022` with MSYS2 MINGW64 gcc/g++, Ninja and SDL2, the same
toolchain as the local recipe, and the maintained cache options (Release,
`PIKMIN_NATIVE_JAUDIO=ON`, `PIKMIN_NATIVE_OPTIMIZE=OFF`, `PIKMIN_ENABLE_IPO=ON`).

- Triggers: push to `main` and `claude/**`, every `pull_request`, manual dispatch.
  Other lane prefixes (`codex/**`, `opencode/**`) get a build once they open a PR.
- Builds `pikmin_pc` plus every executable behind a `p2_` ctest, then runs
  `ctest -R p2_`. `pc_bbft_test`/`pc_bbft_background_test` are not built: that
  Windows-only target has a known MinGW link failure that reproduces at base.
  The full ctest (all targets) still runs in the Linux workflow.
- Uploads artifact `nectar-windows-<head sha>`: `nectar.exe`, every DLL it loads
  from the MINGW64 prefix (SDL2, libstdc++, libgcc, winpthread, ...),
  `BUILD_INFO.txt` and `sha256.txt`. Retained 14 days.
- ccache is cached between runs; the proprietary game-data check from the Linux
  workflow is kept. No game data is needed.

The Linux workflow (`linux.yml`) is unchanged and still runs on every push.

## Root: `Root tests` (`.github/workflows/tests.yml`)

Python 3.12 on `windows-2022`: a deterministic, green-on-main slice of the P2
pool, sampling, placement, roster, boss/cave arena, playable-pool and
seed-bridge tests, then `python -m randomizer generate --p2-enemies
--p2-species playable` for seeds 1234 and 98765, each generated twice and
compared byte for byte. The excluded files and the reason for each are listed at
the top of the workflow; re-add a file once it is green on `main`.

## Getting an exe: `scripts/ci_native_build.py`

```powershell
git -C output/native-<lane> push fork HEAD:claude/my-branch   # native: fork remote, never origin
py -3.12 scripts/ci_native_build.py claude/my-branch        # waits for CI, prints exe path
py -3.12 scripts/ci_native_build.py <sha> --no-wait --json  # fail fast, JSON summary
```

It resolves the ref to a commit on `4laric/Open-Nectar---Pikmin-Native-PC-Port`,
finds the `Windows build` run for that commit (preferring a successful push run,
waiting while one is in progress, failing if every run failed), downloads the
artifact into `output/ci-bin/<sha>/`, verifies every file against `sha256.txt`
and prints the path of `nectar.exe`. A second call for the same sha re-verifies
the local copy without downloading. Use the printed sha and exe SHA-256 as build
evidence in place of the local build-dir record.
