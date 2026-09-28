# Pikmin 2 overworld-course CMake membership (#802)

Consumer proof: `pc_port/pc_p2_overworld_course.cpp` has no `PC_PORT_SOURCES`
membership, so the #738 smoke fixture link fails with undefined
`pc_pikipelago_overworld_course_*` symbols.

## Private candidate (not landed)

One line added to `native/CMakeLists.txt` inside `set(PC_PORT_SOURCES ...)`,
right after `pc_port/pc_p2_preview.cpp`:

```diff
     pc_port/pc_p2_preview.cpp
+    pc_port/pc_p2_overworld_course.cpp
     pc_port/pc_p2_captain.cpp
```

Byte-identical otherwise. The maintained landing is SERIALIZED behind blocked
#755 (which claims `native/CMakeLists.txt`) plus #186 review plus the
integrator; this lane never edits that file.

## Proof in this lane

A leased private build compiles the module TU with reference flags and links
both the new membership probe (`tools/p2_overworld_course_membership_fixture.cpp`)
and the #738 smoke fixture (`tools/p2_overworld_boot_smoke_fixture.cpp`)
against the private `pikmin_pc` graph plus the module object:

- probe exit 0 with `P2_OVERWORLD_COURSE_MEMBERSHIP_LINKED` and
  `PASS P2_OVERWORLD_COURSE_MEMBERSHIP` (no undefined refs at link);
- headed smoke boot exit 0 with `P2_OVERWORLD_BOOT_COURSE_FLAG`,
  `P2_OVERWORLD_BOOT_COURSE_REGISTERED` and `PASS P2_OVERWORLD_BOOT_SMOKE`
  under the #632 guard (vendored verbatim, sha256 `d2f678c9...`);
- unguarded runs refused (`--allow-unguarded` exits 2).

Acceptance: link + guarded boot only. Remaining gates UNTESTED. No ADMIT.
