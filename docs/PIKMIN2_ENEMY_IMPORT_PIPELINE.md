# Enemy family import pipeline

Owner and integration queue: [#186](https://github.com/4laric/pikmin-randomizer/issues/186). This is the repeatable workflow established by Snow/Dwarf Red Bulborbs, Sheargrubs and small Breadbug. It produces imported visuals and explicitly scoped gameplay slices. It is not a universal P2 AI translator or a one-command enemy port.

## Evidence levels

| Level | Required result |
|---|---|
| Source contract | Concrete identity, resource aliases, retail parameters, FSM/events, collision, drops and unsupported behavior documented |
| Converted assets | Deterministic local model/pose bank and hashes; actual source assets exercised |
| Native display | Correct placement, recognizable materials/poses and ordinary control actor unaffected |
| Playable proxy | Explicit P1 behavior reuse; natural combat/carry or source-backed N/A; lifecycle evidence |
| P2 mechanics | Individually implemented source behavior and receiver/animation-event tests |
| Family complete | All parent issue identities and acceptance gates, including lifecycle and mixed-scene performance |

Close narrow batch issues when their stated level passes integration. Keep full-family umbrellas open until their full criteria pass. A fixture, compile, or screenshot alone does not establish the next level.

## 1. Claim a bounded family slice

Create and assign a child issue before edits. State species IDs, intended evidence level, acceptance, file ownership and dependencies. Record Codex as the worker when using the shared 4laric GitHub account. One family owner at a time; shared resources across variants belong to that owner.

Use new family-prefixed modules and tests. Separate extraction/profile, installation, arena staging, native behavior and evidence parsing. Existing examples:

- `experimental/pikmin2_breadbug_assets.py`: parameters, joints/collision and extraction.
- `experimental/pikmin2_groink_assets.py` and `pikmin2_skinning.py`: weighted pose/muzzle extraction.
- `experimental/pikmin2_kochappy_bank.py`: variant motion bank.
- `experimental/pikmin2_uji_animation_install.py`: bounded optional bank installation.
- `experimental/pikmin2_breadbug_cargo_install.py`: exact-byte, source-bound installation.
- `experimental/pikmin2_kochappy_arena.py`: profile separate from original P1 stage placement.

These are reference implementations, not permission to edit a neighbor's modules. If a common converter is missing a capability, submit a minimal reproducer and requested interface to the integration lead; continue independent source/profile work.

## 2. Establish the source contract

Read the local decompilation and legally supplied local ISO without modifying them. Record decomp revision, disc region/revision, resource paths and hashes. Determine concrete spawnable IDs versus aliases/helpers/nonspawnable bases from registration and resource lookup, not display names alone.

Extract retail parameter blocks by identity; duplicate field keys across blocks must not be flattened. Header defaults can differ from retail values (Purple pound radius is an example). Record state/motion mapping, source duration, loop bounds, event frames, collision and attachment joints, rewards, elemental receivers and cleanup dependencies. Distinguish visual events from gameplay events.

## 3. Convert reproducibly

Use existing archive/model/animation readers. Bake bounded poses using source motion timing. Increase sampling where visual evidence warrants it; report pose count, model count, bytes and conversion time. Rigid and weighted skins require their respective supported path; do not silently drop influences or unsupported attributes.

Preserve important event/loop boundary frames in the bank. Source event metadata does not itself execute damage, capture, sound or drops. Native gameplay owns those actions until translated and tested explicitly.

Run real extraction twice into new private directories and compare generated hashes. Validate malformed inputs, finite values, frame ordering, resource limits, source mismatch and overwrite refusal. Write hashed configs as exact bytes to avoid Windows newline translation. Record material/TEV approximations and unsupported features.

Never commit disc assets, generated models, executables, saves or ISO content. Commit source, tests and source-only documentation; evidence stays under private `output/`.

## 4. Install and stage one controlled actor

Bind bank/profile hashes to the same source import. Refuse conflicting or changed installations before mutation. Optional visual banks must preserve the baseline when absent.

Follow [the arena contract](PIKMIN2_ENEMY_ARENA.md): original map/collision/routes, explicit family actor plus control, unique generator IDs checked against existing placements, full expected XYZ. Generator position plus offset is translation; never encode yaw in the offset. Record unapplied source yaw. Default generator scatter must be accounted for; deterministic fixture overrides are explicit engineering changes, not production placement evidence.

Separate model-space attachments, world position and collision ground height. Verify spawn identity from native logs before interpreting combat results.

## 5. Integrate native hooks serially

Family workers supply new modules and a precise hook request. The integration lead owns CMake, shared setup/update/draw/reset, actor registries, converter changes, save/reward code and exports. Bind opt-in family profiles without changing ordinary control actors. Clear registrations and references on death/reset; never assume a pointer cannot be reused.

Visual timing should follow the authoritative native animation counter where mapped. Document fallback and pause/loop behavior. Do not implement stun by skipping all AI updates if that also skips damage/death. A sampled model bank does not supply P2 collision, FSM or attachment semantics automatically.

Only one shared native build runs at a time. After all edits, run the full build and a no-work dry run. Workers must snapshot copied inputs before further shared edits; never run an executable rejected by freshness checks. Record native commit AND dirty state, executable SHA, asset/config hashes, exact command and run directory.

On this Windows checkout:

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
cmake --build native/build-randomizer --target pikmin_pc -j 6
cmake --build native/build-randomizer --target pikmin_pc -- -n
```

Integration lead commits native locally, runs `py -3.12 scripts/export_native_source.py`, reviews the export and pushes root source. Never push native origin. Keep fixed QA packages and player sessions unchanged.

## 6. Validate behavior, visuals and lifecycle separately

Use the six arena gates: exact spawn, autonomous movement/animation, attacks/receivers, death/corpse, transport/reward, cleanup/re-entry. Mark each PASS, FAIL, BLOCKED, UNTESTED or source-backed N/A with evidence.

- Natural target acquisition differs from injected state/health/task tests; label all fixture interventions.
- Pose logs prove selection, not visibility. Capture the actor in view; camera-only observation may be needed when captain targeting affects AI.
- Transport must actually traverse a route and deliver, not just show a carry count.
- Zero receipts cannot validate duplicate reward protection.
- Manager-subset recreation is not full scene/heap teardown or campaign persistence.
- Injected simulation pause tests animation timing, not physical menu input.
- Hidden mouth/pellet contact does not establish alignment.

Measure frame/update timing, memory and bank size with a mixed roster before scaling counts. Do not extrapolate one actor to a full level. Kimi independently tests fixed bundles with bounded navigation and background-safe input; implementation workers must not rewrite those bundles in place.

## 7. Handoff template

Every worker delivers:

1. Child/parent issue, owner, branch or isolated patch, exact base and ordered commits (if any).
2. Owned file list and requested shared hooks; no surprise central edits.
3. Source IDs/revision/resource hashes, extraction command, real conversion result and resource budget.
4. Tests and build commands/results; fixed runtime executable/config hashes where applicable.
5. Gate table with evidence paths and explicit proxy/injection/visual limitations.
6. Remaining blockers and next bounded slice.

Root reviews and integrates completed slices without waiting for unrelated lanes. Issue progress records the integrated commit; broad parent checklists retain unfinished fidelity requirements.

## Current parallel queue

| Lane | First bounded slice | Parent | Child |
|---|---|---|---|
| Content worker | Frog/MaroFrog model, motion and parameter import | #167 | #194 |
| Lifecycle worker | Tank/Wtank model, motion and parameter import | #170 | #195 |
| Enemy worker | Qurione model, motion, reward attachment contract | #166 | #196 |
| Separate Groink task | Static arena projectile/map collision and visual acceptance | #169 | Existing handoff |
| Integration lead | Shared review/build/export; cave diagnostics #193 | #186 | #193 |
| Kimi | Independent cave return acceptance; later immutable family bundles | #184 | #184 |

These three new lanes initially own extraction/profile work only. Their first handoff determines whether the next step is a compatible P1 proxy or a new native mechanic. No shared native ID ranges or hooks are allocated by this table.

Remaining families are already tracked: Bulborbs #120, ground invertebrates #165, flying #166, aquatic #167, scavengers #168, projectiles #169, elemental #170, flora #171, Bulblax/larvae #172, Long Legs #173, Snagrets/Crawbster #174, Waterwraith/Titan #175. Work can split further by independent resource/FSM group once an owner claims a child issue. Do not concurrently implement variants that share the same base module. Multi-actor bosses and captors need helper/receiver lifetime contracts before gameplay integration; they can still perform isolated extraction audits in parallel.
