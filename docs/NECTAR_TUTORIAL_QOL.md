# Nectar tutorial QoL (#463)

Implementation owner: Codex through shared GitHub account 4laric.

Disable the nectar/flower Pikmin popup globally in the normal growth handler, including main campaign and experimental fixtures. Nectar consumption, flower upgrade, sound, result bookkeeping and formation updates are preserved. Mark FirstNectar seen without dispatching TUT_Mitu. No setting or save migration is required; existing saves with the flag unset are covered.

Native base: 5b446a64156b338628c6d636cab3dc76f5a9d224.
Native commit: cc4f6205 (codex/nectar-qol), clean after commit.
Root base: a94fbdf.
Patch: native-candidates/nectar-qol/0001-QoL-suppress-nectar-flower-tutorial-in-all-gameplay-463.patch.

Validation: isolated Release/Ninja/MinGW build of the affected production pikiState.cpp object passed, JAudio and IPO enabled. Repeated object build with ninja -n reports no work to do. Source search confirms the removed call was the only TUT_Mitu dispatch. Only existing compiler warnings were emitted. No GL run performed and no new executable linked; executable SHA-256 is not applicable to this object-only check. Private build: output/native-nectar-qol-build; logs: output/nectar-qol-configure.log and output/nectar-qol-compile.log in the common root.

Integration: cherry-pick native cc4f6205 onto the current maintained source, build and export through the integration lead. The change is intended for main as well as P2. Old already-built game and fixture executables retain the popup until rebuilt. No shared native checkout, maintained binary, session or save was modified by this lane.
