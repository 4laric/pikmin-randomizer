# Nectar tutorial QoL (#463)

Implementation owner: Codex through shared GitHub account 4laric.

Disable the nectar/flower Pikmin popup globally in the normal growth handler, including main campaign and experimental fixtures. Nectar consumption, flower upgrade, sound, result bookkeeping and formation updates are preserved. Mark FirstNectar seen without dispatching TUT_Mitu. No setting or save migration is required; existing saves with the flag unset are covered.

Native base: 5b446a64156b338628c6d636cab3dc76f5a9d224.
Native commit: cc4f6205 (codex/nectar-qol), clean after commit.
Root base: a94fbdf.
Patch: native-candidates/nectar-qol/0001-QoL-suppress-nectar-flower-tutorial-in-all-gameplay-463.patch.

Validation: isolated Release/Ninja/MinGW build of the affected production pikiState.cpp object passed, JAudio and IPO enabled. Repeated object build with ninja -n reports no work to do. Source search confirms the removed call was the only TUT_Mitu dispatch. Only existing compiler warnings were emitted. No GL run performed and no new executable linked; executable SHA-256 is not applicable to this object-only check. Private build: output/native-nectar-qol-build; logs: output/nectar-qol-configure.log and output/nectar-qol-compile.log in the common root.

Integration: cherry-pick native cc4f6205 onto the current maintained source, build and export through the integration lead. The change is intended for main as well as P2. Old already-built game and fixture executables retain the popup until rebuilt. No shared native checkout, maintained binary, session or save was modified by this lane.

## Maintained integration completed

User confirmed this task owns integration. Main PR #464 merged as b851f6d6ac2a0d9bfd750c2bdb889b88763d5d79; maintained P2 source exported in de38c35 and pushed to codex/p2-main-review. Exact export changed only pikiState.cpp (1994 files exported). Earlier handoff-only status above is superseded.

Full production build PASS at clean native cc4f62050548dfc0e7cad52e433c7674898066ad in output/native-nectar-qol-build, Release/Ninja/MinGW, JAudio and IPO ON. Final ninja -n: no work to do. Executable: output/native-nectar-qol-build/bin/nectar.exe in the common root. SHA-256: C14043DB39DC8BB98EBFEE093EEB4248EEDFD9352EBF7E386F17FF79C42B5FFF. Build log: output/nectar-qol-full-build.log. No live GL acceptance claimed. Existing running/immutable fixture executables are not replaced automatically.

Other informational candidates: TUT_BombInfo, TUT_Limit100, TUT_Rute, TUT_NukiAndFree and TUT_InfoDisplay. Not changed in this issue. Extinction is driven by MOVIECMD_GameEndCondition and starts movies, sets game-end flags and advances day-end; hiding its window alone does not repair a zero-Pikmin fixture.
