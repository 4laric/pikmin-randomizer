# Bulblax lane dependency split

The next Kimi batch is #234, following the converter interface in #233.
Use a separate worktree; do not switch the shared native branch or modify
the shared converter from the Kimi lane.

## Work that can proceed with sampled poses

Rebuild the #223 banks using the explicit converter policies documented by
#233. Preserve the original hashed import. Record the policies in each
conversion report, preserve resource consistency checks, and compare two
fresh builds. Unsupported frames must remain visible in the report.

Prepare a versioned installation manifest and installer using these fields:

- schema version, bank header and SHA-256;
- source species name and numeric ID (Queen 30, Baby 31, KingChappy 53);
- every relative model path, byte size and SHA-256;
- clip name, source duration and ordered sampled source frames;
- explicit placement ID, species, clip and finite XYZ coordinates;
- recorded normal/material approximation policies and unsupported frames.

This is an installation artifact, not a native configuration format. Name it
`bulblax-install.json`, schema 1, and validate it independently. The #235
native adapter will consume that artifact and emit its own configuration;
Kimi does not need to wait for native C++ syntax to prepare or test it.
Reject absolute/traversing paths, duplicate IDs, invalid clips/frames,
changed bytes and an existing destination before copying. Never infer P2
identity from a P1 placement vehicle's type. Include a small starting squad
in later arena fixtures to avoid the extinction tutorial; keep intentional
zero-population cases separate.

## Native work remains owned by Codex

#235 is the first sampled display gate: visible models, deterministic
source-frame selection, disabled control, reset/reload and fixed-launcher
evidence. It does not require completion of all of #128, and does not claim
combat or a live boss actor.

Queen roll/crush, owned larva pools, Emperor burrow/emerge, bomb ingestion,
BTK playback and gameplay acceptance remain separate native work. #128
still tracks full skeletal/material fidelity and performance. A converted
bank or display pass cannot close those gates or the family issue #172.
