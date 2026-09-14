# Lanes 08/09 native candidate bundle

Reviewable native patches for lane 01, extracted from the private worktree
`output/tracks/p2-lanes89-next/native` (branch `opencode/p2-lanes89-native-v2`).
Native origin was not pushed.

- Base: `f14c6851473ac1161be56c8b98f4f905232f3635` (clean)
- Head: `b667eec9`
  - `0001` = `c2ce9216` lane08 Armor sampled-clock event migration (#431)
  - `0002` = `b667eec9` lane09 camera-facing billboard flag + draw (#429)

Apply on the maintained native pair; both touch shared renderer/event semantics
and need #186 review before export.

```powershell
git am native-candidates/lanes89-next/0001-*.patch native-candidates/lanes89-next/0002-*.patch
```

Private build evidence (not committed):

- `output/tracks/p2-lanes89-next/native-build`, Ninja/Release/JAudio ON
- `[542/542] Linking CXX executable bin\nectar.exe`; `pikmin_pc` dry run -> no work
- `bin\nectar.exe` SHA-256 `F52A6435A788A032C1800DD3F086017B0E86E969DC775E3778F305272DB28C0F`
- CTest `p2_armor_events_test` -> `PASS p2_armor_events`
- CTest `p2_billboard_test` -> `PASS p2_billboard`

Docs: `docs/PIKMIN2_ARMOR_EVENT_CLOCK.md`, `docs/PIKMIN2_BILLBOARD_NATIVE.md`,
`docs/PIKMIN2_LANES89_NEXT_HANDOFF.md`. Root converter commit: `da6d20a`.
