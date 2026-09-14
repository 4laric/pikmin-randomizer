# Private Demon host runtime

This private PC host loads the converted `demon0.mod` with the staged two-mouth pose
profile, uses the source-backed continuous Attack capture window (frame 17 in the
fixture), and hands a captured captain to the registered Demon receiver. END chooses
CatchFly when the actual receiver owns the captain. Forced release delegates the real
registered damaging drop with a caller-provided 10 damage; host teardown revokes only
its own token.

`tools/p2_demon_host_runtime.cpp` is an injected host/receiver scenario. It places a
captain at the supplied mouth, explicitly advances the continuous attack frame to 17,
and explicitly issues END. It is not a natural Sarai approach, movement, full FSM, or
authored key-event parity claim. The converted pose bank provides translated mouth
positions; the host writes translated joint matrices but does not yet replay full
per-frame mouth basis rotation or scale. Rendering and capture alignment therefore
remain a pose-position approximation.

Evidence from provenance-verified `output/demon-host-fixture-03`:

- `output/demon-host-session-drop-02/run.log`: capture -> CatchFly -> native bounce,
  registered animation delivery, exactly one accepted 10-HP loss (100 to 90), and
  recovery to Walk.
- `output/demon-host-session-teardown-01/run.log`: own-token teardown releases the
  real mouth relation.

The session overlay supplies `demon0.mod` and `demon-mouths.txt` from the converted
asset output. Missing unrelated `chal0` generator files are logged by preview startup
and do not prevent room readiness or either fixture PASS.

## Full mouth pose follow continuation

Native checkpoint ec36f5cc adds source mouth-basis loading and exact-owned
captain following. The P1 mouth stick link alone does not replay P2 joint
transforms: the original full-pose runtime failed its captain-position check
while passing the CollPart matrix check. The scoped bridge now synchronizes
position after native update and supplies jointWorld * Rz(pi/2) for rendering.
It retains real owner-list linkage and requires pre-owner-disposal revocation.

The exporter reads demon.json, validates the source mouth order and radius,
and writes bounded P2_DEMON_MOUTHS_1 data with source JSON hash provenance.
The runtime reader loads exact sampled frames transactionally; no interpolation
or event scheduling is implied. The source hash is metadata, not authentication.

Verified private fixture: output/demon-host-pose-fixture-02, executable SHA256
623912e1b614cdd697664fb42cca70097424f996c849e467e44531bb530ba669.
Production build exited zero. Three fresh fixture processes exited zero:
- output/demon-follow-pose-01: frame17 full joint basis with rotated/scaled host,
  captain position follows, then detach.
- output/demon-follow-drop-01: native bounce, one accepted 100-to-90 damage,
  recovery to Walk.
- output/demon-follow-teardown-01: exact owned link released.
Each directory contains run.log and result.json; the binary's provenance stays
in the immutable fixture directory. These supersede the failed pose fixture,
not the earlier source snapshots.

Limits: frame/END inputs remain fixture-driven; rendered mesh selection is not
yet synchronized with sampled mouth poses. The fixture verifies joint basis and
captain position, not a visual comparison of the captain's rendered orientation.
CatchFly now uses a deterministic, caller-supplied home/radius/angle target and
updates the private host's position on ordinary frame updates. The target
construction follows Sarai's radial `setRandTarget` shape while keeping the
fixture reproducible. The host does not claim map collision, platform/water
handling, random target selection, or manager registration; those remain
separate production integration gates.
