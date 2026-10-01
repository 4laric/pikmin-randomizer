# Shared provider integration (#437)

Owner: Codex through shared 4laric. Base root 161994b; native ab7a900b95206370f2f45619ed5e2264eb2ab029 unchanged, clean. Worker edits to bulborb contracts/model and Dwarf Orange fixture files preserved and excluded.

Integrated d86fd03 (roster admission / roles / aliases) as 2a61434, and 35aa932 (concrete placement catalog / cohort constraints) as 1e23df4. Default admission remains empty; profiles have no accepted gates and native terrain/route evidence remains false. Compatibility is diagnostic, not permission to spawn. Combined roster, placement, enemy slots, seed bridge and staging tests: 98 passed, 17 subtests passed. No native changes/build/export or runtime acceptance in this pass.

## Consumer handoffs

- Lane 03, candidate 0241099: generator calls resolve_admitted_layout, but manifest validate calls validate_layout, which uses eligible_identity rather than require_admitted. Enforce current admission on the loaded product-manifest path as well, and test manually supplied layouts containing a candidate identity. Keep diagnostic explicit-cohort APIs separate from product acceptance. Placement targets also need the accepted placement contract, not just arbitrary target strings.
- Lane 05, candidate 27f424d: staging writes session/content and logs a receipt, but the launch change does not connect the resulting destination to native asset lookup or bind it to the seed's P2 identities. Finish that consumer connection and test actual launch inputs. The documented whole-tree atomicity is also stronger than the per-file materialization implementation; label resumable partial staging accurately or implement whole-tree publication.
- Lanes 02/04: shared contracts are now in draft #432. No family is newly admitted. Keep native terrain/route and family gate evidence explicit before proposing admission.

Other queues remain in PIKMIN2_WATERWRAITH_INTEGRATION_437.md and PIKMIN2_WAVE3_REVIEW_437.md. Active owners retain their lanes. All runtime runs still require current starting-Pikmin overlay, fresh arenas, centred 960x540 and observed adoption evidence. No main merge or upstream writes.
