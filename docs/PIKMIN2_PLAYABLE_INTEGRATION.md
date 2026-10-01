# Combined P2 integration baseline

Tracking: #1073 under #109. Integration owner: Codex through shared account `4laric`.

The source snapshot contains the merged AP catalog/event bridge, White Ivory
conversion budget, Purple campaign/combat, procedural cave and captain switching
work, plus the tested Man-at-Legs/larva admissions and later Maw, bomb, Jellyfloat,
controller-binding and captain re-entry fixes. Imported full courses are still a
separate gameplay track. Source integration is not full P2 campaign acceptance.

Final source candidate: native `a301346b7225dee5ba6156b46b6d6cc708032162`, clean,
in `output/native-p2-playable-1073`; root base
`0b42bddae0809c7b8f9bc47932809c0443cf18a1`. Private build:
`output/native-p2-playable-build-1073`. Build and export receipts are under
`output/p2-playable-1073/`; no shared checkout, player save or installed AP package
was changed. The existing shared native dirty baseline is recorded separately.

The final export verifies all 4,004 selected native files byte for byte. It uses
the current exporter, retaining licensed Windows packaging icons and skipping
53 Android/touch binary assets. Historical root-only source files are retained
for review; this export does not delete them or copy untracked native work.

At native `a01f90b72c0e357a15f959046d56b47c1f8aa8f1`, the private production build
and no-work dry run passed. Executable SHA-256:
`5a2737107eb2d73f45b862a815deece57d20bda6ff198cf691f5a4665c170ef8`.
A fresh provenance-built captain fixture passed in 26.203 seconds under a
60-second supervisor. Its fresh 20-Red P1 practice arena observed a centered
960×540 window and actual whistle/hold/throw/switch/death-reconciliation paths.
Positions, captivity and lethal attacks are labelled fixture injections; this
does not prove natural combat, imported geometry or campaign save/resume.
The negative captain-down case exited 86 in 7.359 seconds, with no PASS marker.
Final source rebuild/export receipts are separate from this earlier runtime pin.
The final production build at `a301346b` also passed with no remaining work;
executable SHA-256 is
`fc076ee8e6b4debef24db61887291fa587fd88c10486f1baf9a03c4be347c4d3`.
The final provenance-built fixture at this same clean source passed its fresh
20-Red arena in 25.906 seconds. Its captain-down negative exited 86 in 7.469
seconds without a PASS marker. Both used a 60-second supervisor. Final export
receipt: `output/p2-playable-1073/export-02/export.json`, SHA-256
`fd2bd5d119e903f03f3c4bb17b49f92ac66f96a17b4d47c4241445861d0782b4`.
Two pre-existing native EOF whitespace warnings are preserved byte for byte
in `pc_p2_elecbug.cpp` and `pc_p2_generated_placement.h`.

Root validation: 450 passed, 14 skipped, one deselected and 55 passing subtests in
the configured CI slice; seeds 1234 and 98765 reproduced byte-identically.
Focused catalog/native IPC/captain/Purple/cave/level tests passed 60 with two
asset-dependent skips. The separately built AP archive passed isolated zip
imports, admitted placement, denied/invalid placement, deterministic P2 fill,
full proxy-pool packaging and manifest export round-trip checks.

The captain re-entry slice (#1074) separately observes three real scenes and two
manager reconstructions, with switching, camera bindings, movement and transient
capture cleanup in each scene, plus active/inactive captain-down negative tests.
It does not serialize or resume a campaign save. Controller binding source has
green compiled/CI checks; the automated interactive menu attempt is inconclusive,
and physical gamepad/touch acceptance remains open.

Active next slices cover ordinary Ivory acquisition, Purple transport/combat,
full cave squad traversal and guarded imported-surface boot. Full retail geometry,
water/generator loading, actual carry routes, saves, mixed-scene performance and
an ordinary AP campaign remain acceptance work. Do not mark those gates PASS
from this export, headless tests or isolated fixture results.
