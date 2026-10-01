# Mar29 native receipt registration (#668)

Lane `mar-native-registration-668`. Implementation owner: Codex through
shared GitHub account 4laric; contributor Muse Spark 1.3 via OpenCode.
Private native worktree `.../mar-native-registration-668-native` (base
`babbdddb`). No shared native edits; no ADMIT. All unobserved gameplay
gates remain UNTESTED. Downstream #375 resumes only after verified source
integration (integrator retains merge/export authority).

## Producer consumed (verified, not re-derived)

- #650 adapter commit `be977b60` ("mar29 receipt provider: corpse receipt
  adapter + guarded receipt fixture (#650)"): `pc_p2_mar_receipt.{h,cpp}`
  checked out verbatim into this private worktree (staged, not yet
  committed at the time of writing).
- #665 preparation evidence (`mar29-pod-dispatch-candidate`, issue #665):
  exact 5-line shared dispatch-arm patch + integration-ready packet naming
  commits/hashes for the single-writer integrator after the #186 owner
  decision. The dispatch arm below follows that packet; the #665 packet
  itself was a planning artifact (no maintained/shared edits).

## Production wiring implemented (this lane, additive only)

1. `pc_p2_mar.cpp`: includes `pc_p2_mar_receipt.h`; `pc_p2_mar_setup()`
   calls `pc_p2_mar_receipt_setup()` after reset; each bound Mar actor is
   passed to `pc_p2_mar_receipt_bind(actor)` at the `P2_MAR_BIND` site;
   `pc_p2_mar_reset()` calls `pc_p2_mar_receipt_reset()`;
   `pc_p2_mar_forget()` additionally calls
   `pc_p2_mar_receipt_forget(actor)`.
2. `pc_p2_preview.cpp`: includes `pc_p2_mar_receipt.h`; additive dispatch
   arm after the mamuta arm:
   `pc_p2_mar_receipt(pellet->mPelletView, generator)` resolving to
   `receipt="corpse:"+pc_p2_cave_receipt_prefix()+"mar:"+generator` with
   `value=corpseValue`. Unknown/non-Mar corpses fall through unchanged;
   exactly-once semantics stay with the adapter registry + lane-06 host.
3. `CMakeLists.txt`: `pc_port/pc_p2_mar_receipt.cpp` added to the main
   target sources; new `p2_mar_receipt_registration_test` target
   (tool + adapter sources, `pc_port` includes, `NATIVE_COMPILE_OPTIONS`,
   CTest entry), mirroring the `p2_dangomushi_hazard_test` pattern.
4. `tools/p2_mar_receipt_registration_test.cpp` (new): compiled
   positive/negative checks over the fail-closed adapter contract WITHOUT a
   live engine — lifecycle empty/count, null-actor rejection on every entry
   point, null-output preservation, reset disarm/re-arm. Live-actor
   bind/resolve positives belong to the #650 natural-run fixture and are
   explicitly not fabricated here.

## Verification

- Focused compiled tests: `p2_mar_receipt_registration_test` exit 0.
- Private leased production build: executable SHA256 recorded in the
  handoff; `ninja no-work` dry run clean; exact source/dirty evidence in
  the handoff source records.
- Preserved families/guards: no other lane module modified; #632 captain
  guard untouched.

## Shared-file review requests (for #186 / integrator)

The following additive changes need existing-owner review before any
maintained merge (filed, not landed by this lane):

- `pc_port/pc_p2_preview.cpp`: one include + one 3-line dispatch arm
  (additive `else if`, fail-closed, no existing arm touched).
- `CMakeLists.txt`: one source line + one test-target block (mirrors
  existing pattern).
- `pc_p2_mar.cpp`: five hook call lines (include, setup/reset/forget/bind).