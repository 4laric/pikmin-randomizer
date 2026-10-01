# Muse Armor15 natural death/transport/re-entry observer - handoff (#165)

Lane `armor15-death-transport-reentry-observer`, issue #165, generation 4.
Implementation owner: Codex through shared account `4laric`; executing Muse
Spark 1.3 Contributor. Outcome: **implementation-ready runtime handoff** for
gates 4/5/6; gates 1/2/3 preserved unchanged. No ADMIT, no ledger writes.

## Result

Fresh private arena, live bound Armor actor (generator 346001), real squad
combat, exit 0:

- Natural drain with real receivers: 25 `P2_ARMOR_RECEIVER ... decision=accept`
  hits, then `P2_MUSE_ARMOR_DRAIN events=8 min=90.00 start=300.00` and
  `P2_ARMOR_DEAD ... health=0` (`native.log:1345, 1398, 1399`).
- Corpse: `P2_MUSE_ARMOR_CORPSE pellet=1 generator=346001` (`:1469`).
- Ordinary FreeMode carry + Pod credit on the same generator:
  `P2_MUSE_ARMOR_CARRY ... transport=6` (`:1548`),
  `P2_POD_RECEIPT id=corpse:346001 value=2 new=1 pokos=2` (`:1897`),
  `P2_MUSE_ARMOR_DELIVER pokos=2` (`:1898`).
- Cleanup/re-entry: `P2_MUSE_ARMOR_FORGET count=0 registered=0` (`:1899`) and
  `P2_MUSE_ARMOR_REENTRY old=... new=... stale=0 fresh=1 count=1` (`:1904`).
- `PASS P2_MUSE_ARMOR death=Armor corpse=1 receipt=1 reentry=1 injected=0`
  (`:1908`); window `Experimental preview window set to 960x540 windowed and
  centered` (`:7`).

### Staged evidence (labelled, not disguised as natural)

The arena Armor loads no collision weakpoint (`P2_ARMOR_RECEIVER_PART ...
dmg1=absent weakpoint=none mode=reject_all`), so the source receiver rejects
all damage. The fixture opens the source damage window through the module's
own documented host input `pc_p2_armor_set_bittered(armor, true)` and marks it:
`P2_MUSE_ARMOR_WINDOW bittered=1 source=armor_module_input` (`:1332`). Every
accepted hit is then real `InteractAttack` receiver damage (`reason=bittered`,
`:1345`), and the reader requires this marker. **No `mHealth` write and no
`TransportMode` write exist anywhere in the fixture** (test grep-asserted).

## Six-gate status

| Gate | Status | Evidence | Method |
|---|---|---|---|
| 1. identity_spawn | PASS (natural, preserved) | lane-14 evidence; `native.log:1302` re-observed at run start | natural |
| 2. movement_animation | PASS (natural, preserved) | lane-14 evidence; not re-run or relabelled | natural |
| 3. attacks_receivers | PASS (natural, preserved) | lane-14 evidence; receiver accepts re-observed `:1345` | natural |
| 4. death_corpse | PASS | `native.log:1345,1398,1399,1469` | staged damage window + natural combat |
| 5. transport_reward | PASS | `native.log:1548,1897,1898` | natural FreeMode carry + Pod receipt |
| 6. cleanup_reentry | PASS | `native.log:1899,1904` | natural rebirth/re-bind |

Gates 1/2/3 are cited from the existing lane-14 evidence and were re-observed,
never upgraded or relabelled.

## Build / run provenance

- Lane native pin: `codex/autofill-shard-armor15-native` head
  `0a32249ab40bbf424403437b7b6dec4ed0529323`, clean (base
  `6a87eb2994b66355b05ce40bf3a8823884236299`).
- Private native build dir: `output/armor15-build`; `pikmin_pc` `nectar.exe`
  SHA-256 `57823aed3a6c78787e5816a458c3b6c8181b3d57b9448c04ed60caceadde1c42`
  (built from the same compiled sources; the only tree change between the exe
  build and this commit is the non-compiled fixture file). `ninja -n` no work.
- Fixture: `output/armor15-fixture3/fixture.exe` SHA-256
  `ae666fb4a9ec98027e278678ae29cd77f5fb21a5e3bc856bcf51c36515e974b5`,
  provenance `built` (`.../baseline/provenance.json`).
- Run: `output/armor15-run2/029a582a08124f0893411d3f2a32bf00`, exit 0,
  `native.log` SHA-256
  `8ccbb58b99e145577fae057e8452ccfd576763c8065fd8af80a00c52bb7cd1e8`.
- Arena inputs: assets `C:/Users/alari/bbft/dist/cohesion/pikmin/assets`,
  imported ground bank `output/dsw/l14-out/ground`, Pod package
  `output/dsw/l19-out/pod`; fresh overlay arena with the starting squad.

### Tool provenance (separate from lane pins)

- Canonical builder: `C:/Users/alari/pikmin-randomizer/scripts/build_pikmin2_fixture.py`
  SHA-256 `f94905d917e1c5d3b654139d324820a0773f762678c7840c851463e8528b24af`.
- Lane worktree copy of the builder is byte-identical
  (`f94905d917e1c5d3b654139d324820a0773f762678c7840c851463e8528b24af`).

## Tooling gap found (provider repair contract; shared builder NOT edited)

The canonical builder rejects Ninja response files and the host toolchain
emits `@CMakeFiles\pikmin_pc.rsp` for the link:

- Bounded reproduction with the canonical CLI:
  `py -3.12 scripts/build_pikmin2_fixture.py --build output/armor15-build
  --source <private-native> --fixture <owned fixture> --output
  output/armor15-fixture-canonical --expected-native-head
  e8506aa340ebe7aeaf74d0be40c7556d3ac598eb`
  -> stderr `Empty command or unsupported response file`, exit 1
  (`output/workflow/autofill/planning-shards/enemies-2/prepared/armor15-observer-output/build-1789580282328310700.log`).
- Root cause: `windows_args` rejects any `@` argument and the canonical script
  has no `expand_response_line`/`expand_response_files` (the newer integration
  script at `output/msw/l62-root/scripts/build_pikmin2_fixture.py` adds them at
  lines 111/128, applied at 421, expanding via `ninja -t compdb -x`).
- Repair contract (for the runtime-fixtures provider): backport
  `expand_response_line(line, build)` and
  `expand_response_files(text, ninja, build)` into
  `scripts/build_pikmin2_fixture.py`, called immediately after
  `ninja -t commands pikmin_pc` and before `select_commands`; acceptance: the
  canonical CLI above produces `{"status": "built"}` for a fixture whose link
  rule carries `RSP_FILE`. Ninja deletes rsp files after a run, so expansion
  must use `ninja -t compdb`/`-t compdb -x` (not the on-disk file alone).
- This lane's unblocking workaround is a bounded in-module shim in the reserved
  `experimental/pikmin2_muse_armor.py` (`_expand_response_files`) that wraps
  only the builder's `select_commands` call for the duration of the build; the
  shared builder is untouched. It is removed when the provider backports the
  fix.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_muse_armor.py -q` -> 11 passed,
7 subtests passed (valid log; prefixed receipt; both injected markers rejected;
written-to-zero rejected; missing receipt; zero transport; missing re-entry;
failure exit code; dependency-free reader; fixture no-write grep; staged
window required).

## Residual / next

- The staged bittered window is the module's documented host input, not full
  source-lifecycle parity; the arena Armor still loads no collision weakpoint
  (family/asset concern, lane-14 scope, read-only here).
- Provider repair above removes the private shim.
