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
| Careening Dirigibug (BombSarai) | #244 | native policy + probes | #244 ✅ | `pc_p2_hardlanes` seam + `pc_p2_bombsarai_*`; candidate `opencode/p2-hardlanes-native` @ `086ed858` | P2 mechanics — shared registration + runtime PASS | ✅ integrated (native `78734504`; root export `87204df`) | batch 2 |
| Antenna Beetle (Fuefuki) | #245 | native FSM + binding | #245 ✅ | `pc_p2_hardlanes` seam + `pc_p2_fuefuki_*`; candidate @ `086ed858` | P2 mechanics — shared registration + runtime PASS | ✅ integrated (native `78734504`; root export `87204df`) | batch 2 |
| Titan Dweevil (BigTreasure) | #246 | native attacks + seam | #246 ✅ | `pc_p2_hardlanes` seam + `pc_p2_bigtreasure*`; candidate @ `086ed858` | P2 mechanics — shared registration + runtime PASS | ✅ integrated (native `78734504`; root export `87204df`) | batch 2 |
| Long Legs / Man-at-Legs | #173 | #312 ✅ | #312 ✅ | none | Converted assets | native registration | other agent |
| Empress/Emperor Bulblax & larvae | #172 | #217 ✅ (+#120) | #389 ✅ install+arena+runtime; #392 ✅ material profile | `pc_p2_bulblax_visual` + `pc_p2_queen`/`pc_p2_king` actors (six-lane; root export `6e79fe6`) | P2 mechanics (Queen #256 gates PASS; King #289 required gates PASS on six-lane `opencode/p2-batch5-bulblax`; #239 material profiled) | King WarCry/cross-Emperor + flakiness; #239 host lighting/BTK; Baby attack | this session (batch 5) |
| Jellyfloat | #243 | worktree | none | `pc_p2_jellyfloat*` worktree | Playable proxy | install + arena, then native | unclaimed |
| Bumbling Snitchbug / Demon family | #215–#242 | many slices | partial | `pc_p2_demon*` worktrees | P2 mechanics | consolidate drop/capture gates | other agent |
| Beetles / Breadbug / Mamuta | #168 | #212–#214 ✅ | #219–#221 ✅ | `pc_p2_kogane/mamuta/...` committed | P2 mechanics | runtime gates | other agent |

## Handoffs / integration queue

- **Batch 2 hard lanes (#244/#245/#246) — ✅ integrated and exported.** Root handoff branch [`opencode/p2-batch2-handoff` @ `3d30774`](https://github.com/4laric/pikmin-randomizer/pull/new/opencode/p2-batch2-handoff). Native merge `opencode/p2-integration` @ `78734504` (fast-forwarded onto the maintained `codex/pikmin2-room-preview`) unifies `pc_p2_batch2.*` (batch-2 visuals) with `pc_p2_hardlanes.*` (BombSarai/Fuefuki/BigTreasure seam); conflicts were additive only. Maintained `pikmin_pc` rebuild PASS + `ninja -n` clean (`nectar.exe` `854B68E2…AFF26`); root `engine/` exported at `87204df`. Blocked gaps are #128-gated. Also posted on #186.

## Orchestration rule

Each family owner prepares its next-step artifact and a precise, reproducible run command. Shared native builds and real-GL fixtures are serialized by the orchestrator (this session) so no two families build or launch a GL window at once. A family that needs the disc assets reads only the private ISO above and commits no extracted assets.
