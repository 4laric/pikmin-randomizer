# Floor 3 second treasure plan (#357)

Owner: Codex using shared account 4laric. This extends #344's source-bound
planner with `prepare(..., treasure='donutswhite')`. The default remains
`dia_c_green`; its regenerated plan is byte-identical to frozen #344.
Only the two audited floor3 treasure names are accepted.

The second loose treasure is source row 0, instance
`forest_1:floor3:treasure:donutswhite:0`, worth 230 Pokos with minimum carry
weight 15 and maximum 25 slots. Its frozen converted model hash is
`2f344dc4dc56619b44f0a0895f7acb4fc198241b9dd8489fd3d089115f2fdf5f`.
The plan uses authored assembly instance 0, `room_block1_3_hiba_tsuchi`, source
type2 slot 2 at `[175,20.5,-55]`. Choosing this source slot is an engineering
placement, not a reproduction of retail seeded placement selection.

The existing Pod remains `[-85,0,-280]`. The actual directed graph provides
route **6 → 4 → 3 → 0**; no reverse links or geometry were added. The plan binds
the source catalog, imported room collision, assembly outputs, treasure model,
source definition and actual disc economy using the existing validation path.

All 258 probes in the 50-unit strip have floor support. This is **not a verified
native haul route**: heights span 0 to 111.142285, and the largest adjacent
same-lane probe change is +90.642285 on the initial treasure-to-waypoint segment.
The diagnostic groups samples by segment and lateral offset so it does not
mistake lateral samples or segment boundaries for forward height changes.
It applies no invented native climb threshold. The strip is narrower than the
converted donut's approximately 108 by 114 model footprint, before carriers.
Raised-platform departure, full footprint clearance and actual native transport
must be tested separately; the graph's existence does not settle these questions.

Local evidence under the private root `output/p2-cave-lane`:

- `output/beasts357-final/first/haul.json` and `repeat/haul.json` are byte-identical,
  SHA-256 `8b4473f051ffc894e87fea21d98d1d70e3d783ff8d0d1c6381f6f7d8c5380139`.
- `output/beasts357-final/default/haul.json` is byte-identical to
  `output/beasts344/first/haul.json`, SHA-256
  `fdfe3547276574a3655196e543fcf12177f1b2a750853ff726d39f21171034c6`.
- Source inputs are the GPVE01 rev0 disc, `output/p2-cave-catalog-batch/audit-final`,
  `output/p2-mapcode0-batch/import`, and the floor3 worker's frozen
  `output/floor3-306/final-a` assembly and `output/floor3-295/final-a` package.
- 22 tests and 28 subtests passed across second-haul, haul, floor3, assembly and
  collision tests. New coverage checks selection rejection, source slot/economy,
  model tampering and same-lane vertical observations.

No native code, receipt authorization, checkpoint schema, route links or assets
are changed or redistributed. `native_ready`, `campaign_reward_authorized` and
the new terrain diagnostic's `native_traversability_verified` remain false.
The older #343 runtime stage accepts only its green-treasure contract; this
donut plan requires a separate runtime milestone before it can be consumed.
