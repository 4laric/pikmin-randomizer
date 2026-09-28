# Optional P2 multi-cargo receiver

`p2-cargo.txt` opts in to per-actor cargo. Absent file retains the old one-treasure
path. The strict format is `P2_CARGO_1`, row count1..32, then six whitespace
fields per row: uint32 native generator ID, instance ID, model basename, value,
weight and attachment slots. Instance IDs allow ASCII letters/digits and `_:/-`
(up to90); model names allow letters/digits and `_-` (up to64), without extension.
Values0..1,000,000; weights1..1000; slots1..128. IDs, instances and models must
be unique. Every live generated `pr05` scaffold must bind exactly once.

Models resolve only in `courses/pikmin2room/<basename>.mod`. The first row stays
the legacy selected treasure. Each cargo actor gets a fresh PelletConfig whose
constructor owns its parameter chain/CoreNode links; values are copied
individually from the global scaffold. Configs live on the same App heap as
actors for the one-floor process and remain alive after delivery. Shared global
configs are not changed in cargo mode. Imported visual models do not yet give
each actor source-specific collision geometry.

`pc_p2_preview_cargo_count`, `cargo_at(index)` and `cargo_shape(actor)` expose
the registry to the isolated fixture. Delivery uses the existing atomic Pod
ledger with receipt `treasure:<instance_id>` and retains corpse identity routing.
Duplicate delivery does not grant more Pokos or P1 repairs/seeds.

`tools/test_p2_cargo.cpp` is a standalone strict-parser probe (g++17, include
pc_port). `preview_p2_cargo.inc` adds native checks for private configs/intrusive
links, distinct models, row weights, all receipts and duplicate suppression.
The cave fixture calls it when cargo is present, at90 frames to limit incidental
combat before the synthetic lifecycle checks. Optional `p2-cargo-carry.txt`
instead selects a real transport-AI test of the second cargo, without teleporting
actors or manually awarding receipts. These fixtures still require a real native
run; the parser test alone does not validate rendering/transport.
