# Ordinary bounded cave fresh entry (#1121)

Owner: Codex through shared GitHub account `4laric`.

Fresh `stage_pikmin2_playable_cave.stage()` now writes 20 Red leaf Pikmin
to `p2-cave-entry.txt`. The native restored-squad species IDs are Blue 0,
Yellow 1 and Red 2. The previous default used 1, making ordinary entry Yellow
despite the required Red baseline and the Red starting squad in #1086.

Checkpoint entry still uses the exact saved squad, maturity, captain health,
bud state and receipt text. There is no starter top-up. Generator placement,
native source and the immutable #1086 handoff are unchanged.

Validation from root base `6ed2b6a4e07c44af515e32961e97a0da97fb226b`:

- The new serialization regression fails against the original stage function
  (20 Yellow), then passes with the correction. Nine bounded cave tests pass.
- Real staging with existing local legal assets and the native cave generator
  produced fresh 20 Red and an exact 15 Red / 5 Blue re-entry from the actual
  #1086 checkpoint. Both generated 20 actor records at the original valid
  positions. The unit regression also checks a smaller mixed squad with mixed
  maturity and half captain health, preserving its count without top-up.
- Local proof: `output/cave-entry-red/staging-proof-01.json`, SHA-256
  `ddc058d6f83582b9ae48dd3bdfee45b64e8483060f967f9c865f533cb50fc555`.
  New packages are `output/cave-entry-red/fresh-01` and `resume-01`.

This is staging correctness evidence. No runtime was launched and no native
build was needed. The copied #1086 executable and historical generator are
hashed staging inputs, not certification of the newest native integration.
Window/guard/runtime adoption, manual plucking, mixed hazard traversal, exit UI,
second procedural floor descent, full supervisor recovery and campaign resume
remain open. Ordinary bounded cave checkpoints still re-enter floor 1.
