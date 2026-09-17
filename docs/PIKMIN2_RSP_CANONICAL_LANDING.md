# @rsp canonical landing producer (#659)

Root-only prerequisite producer unblocking `provider-bomb-mgr-birth` (#616) handoff
validation, then `enemy-bombotakara93-payload` (#573). No builds, no runtime, all six
gates UNTESTED, no ADMIT.

## Gap (verified fresh, byte-exact)

The canonical integration pin `36b868391e62cccf37d992aa2f796f3cc9c6dc31` (and root HEAD
`ecf5f53a`) still reject Ninja `@rsp` response-file link lines in
`scripts/build_pikmin2_fixture.py`:

`if not args or any(arg.startswith("@") for arg in args): raise BuildRejected("Empty command or unsupported response file")`

Reviewed fix commits `2fb2040e` / `0cab1fa1` (content `70d30827`) exist in git history but
are NOT ancestors of the pin. Manifest item `provider-rsp-builder-509-v1` (issue #509)
already owns the two shared files; this lane claims nothing shared.

## Deliverable

`experimental/pikmin2_rsp_canonical_landing.py` re-derives the exact landable rebased
change (pin -> reviewed fix, `git apply --check` clean, 11961 bytes) from git objects at
runtime, re-verifies every #616 handoff evidence hash (root `b779b00f`, native `6d4cbc4a`,
provenance/exe/runlog), and emits `rsp-canonical-landing-packet.json` naming exact
commits/hashes with downstream consumers #616 then #573. Fail-closed (`LandingGapError`)
on missing pins, drifted blobs, or absent evidence.

## Evidence

- Focused tests `tests/test_pikmin2_rsp_canonical_landing.py`: gap proof, fix refs,
  patch validity, 13 #616 evidence hashes, fail-closed negatives.
- The integrator lands the packet patch; #616 re-runs its fixture build through the
  canonical builder and submits its handoff; #573 consumes the seam.