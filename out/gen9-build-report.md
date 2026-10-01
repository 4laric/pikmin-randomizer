# forest_1 P1 gen-9 build + guard evidence (lane shard-caves-forest-forest1-p1, #154)

Attempt b18dfc1aa99ae27ed776b10b9747106aac19aef5477787b5a9b2deb87406124d,
generation 9. Private build dir
`output/.../caves-forest/prepared/forest1-p1/build` under canonical lease
(token 16606bb9, gen 9). No shared builds touched.

## Private builder fix (documented deviation from #642 bytes)

`scripts/build_p2_cave_guarded_boot_fixture.py` (consumed #642 copy) assumed
the reference TU lives in `tools/` (kurage precedent). In trees without the
kurage TU it fell back to `pc_port/pc_main.cpp` and produced either a wrong
`pc_port/` fixture path or a two-source `-o` collision. Fixed in the private
copy only: substitute the reference source path itself with the fixture
source (either slash form), never the bare basename. Upstream #642 copy
untouched; recommend the owner adopt the same form.

## Build evidence (lease-protected)

- Record: `output/.../forest1-p1/out/build-1789621863410023.json`:
  configure 0, pikmin_pc 0 (98 targets), dry-run exit 0 (fresh build, no-work
  false as expected), fixture compile 0, fixture link 0 (82 objects).
- Exe: `.../forest1-p1/build/p2_cave_guarded_boot.exe` sha256
  `f919f5b54b43c2e1e384589e8c38d13b007a70f4c6271d78251fa9a104592f21`.
- Guard self-test: exit 0, `P2_CAVE_GUARDED_SELFTEST_PASS rows=7`
  (`.../forest1-p1/out/selftest-gen9.log`). This is real #632 adoption
  evidence for the guard predicate (orimaDead/NaviDead/HP<=1 truth table).
- Wrapper-spawn note: the builder wrapper subprocess env on this host lacks
  MinGW DLL resolution, so wrapper-invoked exe runs fail DLL-not-found;
  direct invocation with MinGW bin on PATH passes. Environment note, not a
  fixture defect.

## Honest limits (still blocked)

- Negative captain-down run reaches 960x540 centred window + audio init,
  then stalls pre-idle (no legal stage data: `courses/pikmin2room` absent),
  so the forced `CAPTAIN_DOWN`/exit-86 path never executes here -- same
  environmental block #642 documented. No negative-test PASS claimed.
- No floor-1 boot observation for the same reason; all six arena gates
  remain UNTESTED. No ADMIT. #154 stays OPEN.
