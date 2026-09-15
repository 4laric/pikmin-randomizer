# Waterwraith dependency integration (#437 / #443)

Owner: Codex through shared account 4laric. Root base 3851d4b. Native ab7a900b95206370f2f45619ed5e2264eb2ab029, clean; prior native f14c6851. Pre-existing untracked experimental/pikmin2_dwarf_orange_runtime.py is worker-owned and excluded.

Integrated only six Waterwraith files from native a4526e6a: roller policy, actor phase machine and their two standalone tests (originating f5274522 / 45a509b9). Added both translation units to the private production target and both tests to the maintained gate. No shared gameplay hooks changed. Registration, host and visual files are not integrated by this slice.

This gives lane 31 a current-line dependency for roller ownership, Purple-only policy damage, host-fed phase transitions, host-driven waypoint travel, death events and reset. It does not establish natural AI navigation, engine damage receivers, real drops, ordinary spawns or randomizer eligibility. Worker real-GL evidence in 9217a93 remains tied to a4526e6a and its own executable.

Validation: all 33 native probes PASS; receiver ownership regression 1 passed / 2 subtests passed. Exact native-to-engine parity across 1730 tracked source files; native dirty state clean. Production build PASS; dry run: ninja: no work to do. Executable SHA-256 A085DB18E4834B806F510E32772BEC2DBC20D26DE04F313ADD40F1296636DDA2. Private build output/p2-upstream433-build, Ninja Release/MinGW with JAudio enabled; two compile jobs to share host capacity. Local logs output/p2-waterwraith-sweep-build.log and output/p2-waterwraith-sweep-tests.log.

## Next queue

- Lane 31: reconcile host/visual/room registration atop ab7a900b, retaining opt-in behavior. Regenerate fixture and record observed live starting Pikmin and centred 960x540; no adoption PASS claimed from source here.
- Shared provider series c03be34 (17 patches) still needs native reconciliation. Active shared sessions retain ownership.
- Species 8c8cda8 supplies ground lifecycle/Hana/Catfish diagnostics; lane 01 candidate 2c306cc supplies older species native export. Review together against current lifecycle safeguards; do not wholesale replace engine.
- Titan ca7ae78 adds merged encounter/motion/save candidate evidence. Save semantics need shared-lane review; worker completion is not combined acceptance.
- Groink 9e0a76b remains held for tracker capacity; Candypop actor remains held for colour and output conservation. Earlier review criteria remain applicable.

No native origin/upstream push, main merge, shared checkout cleanup or real-GL run.
