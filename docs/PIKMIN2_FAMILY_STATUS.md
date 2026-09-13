# P2 enemy family — ownership and next-step status

Live tracking: this file. Batch assignments and per-session mandates: [PIKMIN2_FAMILY_BATCHES.md](PIKMIN2_FAMILY_BATCHES.md).

Coordination: [#186](https://github.com/4laric/pikmin-randomizer/issues/186). This is the single tracking view for the P2 enemy-family import pipeline. Evidence levels are defined in [PIKMIN2_ENEMY_IMPORT_PIPELINE.md](PIKMIN2_ENEMY_IMPORT_PIPELINE.md). Under the 2026-09-13 revision, family owners own extraction, conversion, native modules, narrow additive registration hooks, private builds and runtime evidence; #186 reviews shared semantics.

Shared, serialized resources (one at a time): the maintained `native/` build and any real-GL runtime fixture. The ISO is `output/pikmin2-runtime/pikmin2-source-test.iso` (GPVE01 rev 0, private). Native origin is never pushed.

| Family | Parent | Source contract | Install + arena | Native registration | Evidence level | Next step | Owner |
|---|---|---|---|---|---|---|---|
| Ground invertebrates & disguises | #165 | #346 ✅ | other agent (batch2) | `pc_p2_batch2` committed | Converted assets | export + spawn fixture → Native display | other agent |
| Flying enemies & fliers | #166 | #348 ✅ | #375 ✅ | `pc_p2_batch3` candidate | Converted assets | export + spawn fixture → Native display | this session |
| Aquatic/hopping | #167 | #347 ✅ | #374 ✅ | `pc_p2_batch3` candidate | Converted assets | export + spawn fixture → Native display | this session |
| Cannon larvae / projectiles | #169 | #350 ✅ | other agent (batch2) | `pc_p2_batch2` committed | Converted assets | export + spawn fixture | other agent |
| Blowhogs / dweevils / hazards | #170 | #349 ✅ | other agent (batch2) | `pc_p2_batch2` committed | Converted assets | export + spawn fixture | other agent |
| Flora & Candypops | #171 | #353 ✅ | other agent (batch2) | `pc_p2_batch2` committed | Converted assets | export + spawn fixture | other agent |
| Snagrets & Segmented Crawbster | #174 | #351 ✅ | #376 ✅ | `pc_p2_batch3` candidate | Converted assets | export + spawn fixture → Native display | this session |
| Waterwraith / rollers / Titan | #175 | #352 ✅ | other agent (batch2) | `pc_p2_batch2` committed | Converted assets | export + spawn fixture | other agent |
| Careening Dirigibug (BombSarai) | #244 | native policy + probes | #244 ✅ | `pc_p2_bombsarai_*` in native worktree | P2 mechanics | register in shared native → run gates | this session |
| Antenna Beetle (Fuefuki) | #245 | native FSM + binding | #245 ✅ | `pc_p2_fuefuki_*` in native worktree | P2 mechanics | register in shared native → run gates | this session |
| Titan Dweevil (BigTreasure) | #246 | native attacks + seam | #246 ✅ | `pc_p2_bigtreasure_*` in native worktree | P2 mechanics | register in shared native → run gates | this session |
| Long Legs / Man-at-Legs | #173 | #312 ✅ | #312 ✅ | none | Converted assets | native registration | other agent |
| Empress/Emperor Bulblax & larvae | #172 | #217 ✅ (+#120) | #389 ✅ install+arena+runtime; #392 ✅ material profile | `pc_p2_bulblax_visual` (native registration; root export pending) | Native display (noninteractive display overlay; #239 material profiled, host-lighting/BTK limits recorded) | boss gameplay native (Queen/King actors); #239 host lighting/BTK; root export | this session (batch 5) |
| Jellyfloat | #243 | worktree | none | `pc_p2_jellyfloat*` worktree | Playable proxy | install + arena, then native | unclaimed |
| Bumbling Snitchbug / Demon family | #215–#242 | many slices | partial | `pc_p2_demon*` worktrees | P2 mechanics | consolidate drop/capture gates | other agent |
| Beetles / Breadbug / Mamuta | #168 | #212–#214 ✅ | #219–#221 ✅ | `pc_p2_kogane/mamuta/...` committed | P2 mechanics | runtime gates | other agent |

## Orchestration rule

Each family owner prepares its next-step artifact and a precise, reproducible run command. Shared native builds and real-GL fixtures are serialized by the orchestrator (this session) so no two families build or launch a GL window at once. A family that needs the disc assets reads only the private ISO above and commits no extracted assets.
