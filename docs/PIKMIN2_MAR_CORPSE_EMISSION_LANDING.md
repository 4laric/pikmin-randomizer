# Mar corpse-emission landing (#720)

Lane `mar-corpse-emission-landing`, issue #720. Owner: Codex through shared
account `4laric`. This lane lands the done-but-unlanded #716 corpse emission
via handoff + integration packet. Owns only the landing validator, its tests
and this doc. The #716 implementation was taken read-only (no re-derivation,
no duplication, no family/shared/native edits, no runtime, no ADMIT).

## Pinned #716 evidence (re-verified hash-identical this turn)

- Native `.../mar-corpse-emission-native-native` commit `0306b0d0`
  ("Emit a corpse pellet on natural Mar death for the #668 receipt arm",
  branch `codex/mar-corpse-emission-native`, base `780de444` = the #668 head):
  `pc_port/pc_p2_mar.h` sha256
  `9a1b617c4bcaebbc1590b5e3be000aef791a88bd20cc7df1978be9ad51617816`,
  `pc_port/pc_p2_mar.cpp` sha256
  `c5bed43d25e819a57356bcaced9779d1d9d806cc43d6816a036b3e31d9c06a33`,
  `tools/p2_mar_corpse_emission_fixture.cpp` sha256
  `75f7c6b7fe1fc23a5cade178b10bc2a746a932712e358b9a2515668142ac9975`.
- Root commit `2e2eda6a` ("Mar corpse-emission proof tooling", base
  `ecf5f53a`): helper, evidence module, 8 tests (re-run green read-only),
  doc.
- Compiled evidence: provenance `built` (expected head `780de444`; the #716
  tree built as base + same-content dirty tree);
  `fixture.exe` sha256
  `eb371ba5a770bc16883aac8672b1df81ad8a0e26ad93986779a5d1e60be5584e`;
  production `nectar.exe` sha256
  `93b83d7d1e4783f768a04f7e69ef216f2c1d0bad45563010c50450001cb2267c`
  (exit-0 build, re-verified present).
- Guard reference: `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
  (no runtime Mar run exists, so no guard-trip evidence applies).

## #668 receipt-arm validation (read-only)

Emission (`MAR_DEAD` end -> `pc_p2_mar_emit_corpse` -> `becomePellet`, once-
guarded, `P2_MAR_CORPSE_EMITTED generator=%u source_id=29` only when a pellet
is bound to the dead actor) produces exactly what the #668 arm resolves: the
adapter registry persists view->generator past death, `pc_p2_mar_receipt(view)`
resolves the delivered corpse pellet, `P2_MAR_CORPSE_READY ... receipt=
corpse:mar:%u` fires, and `pc_p2_preview.cpp:337` consumes it into Pod
dispatch. All seven compatibility checks green
(`experimental/pikmin2_mar_corpse_emission_landing.py:verify_arm_compat`).

## Arena sequencing (breaks the #716/#375 circle)

1. Land #716 now on compiled evidence + fixture (this packet; no runtime Mar
   claim). 2. #375 (`shard-enemies-2-mar29-observer`, blocked gen 9, natural
   kill already PASS with `P2_MAR_DEAD`) lands the emission and runs its kills
   in the Mar arena (flying-install, generator 375001). 3. The arena kill runs
   prove #716 (corpse pellet + receipt), closing `transport_reward`.

## Packet

The hashed integration-ready packet for the single-writer integrator and
existing-owner/#186 reviewers names the exact commits/hashes above plus
downstream consumer #375 (runtime proof via #375 arenas as the documented
follow-on). No #716-file duplication; owner + #186 review still required
before shared-line landing.

## Gates

All six runtime gates UNTESTED (no Mar arena claimed here).
