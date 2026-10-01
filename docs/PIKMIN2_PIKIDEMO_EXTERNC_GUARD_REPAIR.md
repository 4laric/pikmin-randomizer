# pikidemo.h extern-C guard repair (#776)

Implementation owner: Codex through shared account `4laric`. Lane
`jaudio-pikidemo-externc-guard-repair` (1-file header fix + verification).

## Proven blocker

Consumer verification `6cfb39a0`: `Jac_NoteDemoSkipped` was declared at
`native/include/jaudio/pikidemo.h:41`, AFTER `END_SCOPE_EXTERN_C` (line 36)
inside `#ifdef PIKI_PC_PORT` (line 38). C++ callers therefore mangle the
reference while `src/jaudio/pikidemo.c:54` defines it unmangled: 566/566 TUs
compile, the final link fails on undefined `Jac_NoteDemoSkipped`.

## Fix (zero behavior change, no stub duplication)

Moved the declaration (with its comment and `#ifdef PIKI_PC_PORT` gating
intact) to directly after `Jac_SetDemoPartsCount`, i.e. INSIDE the
extern-C guards before `END_SCOPE_EXTERN_C`:

```c
void Jac_SetDemoPartsCount(int);                            // args
#ifdef PIKI_PC_PORT
/// Records that the current cutscene was skipped ...
void Jac_NoteDemoSkipped(void);
#endif

/////////////////////////////////////////////////////////

END_SCOPE_EXTERN_C
```

`pikidemo.c` is verification scope only (membership exists, no edits).

## Verification

- `experimental/pikmin2_pikidemo_externc_guard_check.py`: fail-closed
  checker (guarded-once/missing/duplicate/unbalanced + C-definition
  presence).
- `tests/test_pikmin2_pikidemo_externc_guard_check.py`: 9 green, including
  the pre-fix shape rejected with the exact defect and the live repaired
  header passing.
- Leased private rebuild of the consumer pin: link clean (no undefined
  `Jac_NoteDemoSkipped`), executable + log SHAs and `ninja -n` dry run
  recorded in the child issue.
- Captain safety #632 adopted for any observed run (guard source + hash in
  the handoff); unguarded runs refused.

## Landing

SERIALIZED via #186 review + integrator. No ADMIT. Issue #776 stays open
until the repair lands.
