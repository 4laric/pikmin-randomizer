# Lanes 08/09 native candidate bundle

Reviewable native patches for lane 01, extracted from the private worktree
`output/tracks/p2-lanes89-next/native` (branch `opencode/p2-lanes89-native-v2`).
Native origin was not pushed.

- Base: `f14c6851473ac1161be56c8b98f4f905232f3635` (clean)
- Head: `8c9a6cb`
  - `0001` lane08 Armor sampled-clock event migration (#431)
  - `0002` lane09 billboard flag + initial draw (superseded by 0004/0005)
  - `0003` lane09 pivot/facing probe
  - `0004` lane09 apply in the OGL/DGX backends (`Joint::render` is dead on PC)
  - `0005` lane09 key the rotation to the active GPU matrix

Apply on the maintained native pair in order; all touch shared renderer/event
semantics and need #186 review before export. 0002/0003 are intermediate history;
squashing 0002-0005 into one lane09 commit is fine.

```powershell
git am native-candidates/lanes89-next/*.patch
```

Private build evidence (not committed):

- `output/tracks/p2-lanes89-next/native-build`, Ninja/Release/JAudio ON
- `[542/542] Linking CXX executable bin\nectar.exe`; `pikmin_pc` dry run -> no work
- `bin\nectar.exe` SHA-256 `F35DE2B45B9B319E22CE08D98A5502C79A85FB60788C9F15BB996C9244C45A0E`
- CTest `p2_armor_events_test` -> `PASS p2_armor_events`
- CTest `p2_billboard_test` -> `PASS p2_billboard`
- Real-GL Hikari fixture -> `PASS HIKARI_BILLBOARD draws=2 max_offdiagonal=0.000000`

Docs: `docs/PIKMIN2_ARMOR_EVENT_CLOCK.md`, `docs/PIKMIN2_BILLBOARD_NATIVE.md`,
`docs/PIKMIN2_LANES89_NEXT_HANDOFF.md`.
