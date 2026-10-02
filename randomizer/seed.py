"""Strict, deterministic identity-placement milestone; no unproven relocation."""
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from .catalog import (GAME, NAMES, PART_IDS, LOCATION_IDS, UNLOCKS,
                      REPAIR, REPAIR_COUNT, CHECK_REQUIREMENTS, active_names, ALL_LOCATION_IDS,
                      can_reach, can_reach_manifest, progression_pool, item_pool, START_AREAS, ALL_AREA_LOCATION_IDS, ALL_PART_IDS, COLLECTION_LOCATION_IDS, PERMANENT_LOCATION_IDS, MODERN_LOCATION_IDS, modern_names)

EXPANDED_CAPABILITIES = ["flarlic-v1", "population-v1", "bestiary-v1", "exploration-v1"]

CAPABILITIES = ["identity-placement-v1", "foh-day2-v1", "repair-goal-v1", "repeat-day29-v1"]

ADMITTED_PLACEMENT_FILENAME = "PIKMIN2_ADMITTED_PLACEMENT.json"
PROXY_PLACEMENT_FILENAME = "PIKMIN2_PROXY_PLACEMENT.json"


def _default_admitted_placement():
    """Committed lane 04 accepted-placement document for the admitted cohort.

    Admitted P2 enemies are eligible for placement behind the ``p2_enemies`` /
    AP ``p2_enemy_randomizer`` option. When no explicit document is supplied this
    finds the committed accepted-placement document (repo ``docs/``, a
    ``PIKMIN2_ADMITTED_PLACEMENT`` path override, or the packaged apworld data
    file). It is deliberately fail-closed: an empty or unaccepted admitted set is
    still rejected by ``resolve_placement_layout``.
    """
    candidates = []
    override = os.environ.get("PIKMIN2_ADMITTED_PLACEMENT")
    if override:
        candidates.append(Path(override))
    try:
        candidates.append(Path(__file__).resolve().parents[1] / "docs" / ADMITTED_PLACEMENT_FILENAME)
    except (NameError, OSError):
        pass
    candidates.append(Path.cwd() / "docs" / ADMITTED_PLACEMENT_FILENAME)
    for candidate in candidates:
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    try:
        from importlib.resources import files
        package = __package__ or ""
        if package.startswith("pikmin_randomizer"):
            resource = files(package) / "data" / ADMITTED_PLACEMENT_FILENAME
            return json.loads(resource.read_text(encoding="utf-8"))
    except (ImportError, ModuleNotFoundError, FileNotFoundError, TypeError):
        pass
    raise ValueError(
        "P2 enemies require the committed admitted-placement document "
        f"(docs/{ADMITTED_PLACEMENT_FILENAME}); set PIKMIN2_ADMITTED_PLACEMENT to override")


def _default_proxy_placement():
    """Stage-A proxy-tier-only sibling document (never used without the tier).

    Loaded only when ``p2_proxy_tier`` is requested; the default (no-tier)
    path never reads this file, so default manifests stay byte-identical.
    Fail-closed: a missing or invalid sibling rejects the proxy seed instead
    of silently falling back to 33 targets.
    """
    candidates = []
    override = os.environ.get("PIKMIN2_PROXY_PLACEMENT")
    if override:
        candidates.append(Path(override))
    try:
        candidates.append(Path(__file__).resolve().parents[1] / "docs" / PROXY_PLACEMENT_FILENAME)
    except (NameError, OSError):
        pass
    candidates.append(Path.cwd() / "docs" / PROXY_PLACEMENT_FILENAME)
    for candidate in candidates:
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    try:  # packaged apworld: the sibling ships next to the admitted-placement document
        from importlib.resources import files
        package = __package__ or ""
        if package.startswith("pikmin_randomizer"):
            resource = files(package) / "data" / PROXY_PLACEMENT_FILENAME
            return json.loads(resource.read_text(encoding="utf-8"))
    except (ImportError, ModuleNotFoundError, FileNotFoundError, TypeError):
        pass
    raise ValueError(
        "p2_proxy_tier requires the proxy-placement sibling "
        f"(docs/{PROXY_PLACEMENT_FILENAME}); set PIKMIN2_PROXY_PLACEMENT to override")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def fingerprint(manifest):
    validate(manifest)
    return hashlib.sha256(canonical(manifest)).hexdigest()


class SeedRandom:
    """SHA256 counter stream, rejection sampling; independent of Python random."""
    def __init__(self, seed):
        self.seed = seed.encode()
        self.counter = 0

    def below(self, n):
        limit = (1 << 256) - ((1 << 256) % n)
        while True:
            value = int.from_bytes(hashlib.sha256(self.seed + b"\0" + self.counter.to_bytes(8, "big")).digest(), "big")
            self.counter += 1
            if value < limit:
                return value % n

    def shuffle(self, values):
        values = list(values)
        for i in range(len(values) - 1, 0, -1):
            j = self.below(i + 1)
            values[i], values[j] = values[j], values[i]
        return values


# Admission table for the playable P2 pool. Each row names one campaign-proven
# species (source id + enum name) and cites the evidence that admitted it: what
# was run and where the log lives, plus the family installer that stages it.
# Adding a row does NOT admit a species on its own -- see
# docs/PIKMIN2_PLAYABLE_POOL.md for the admission bar and procedure (owner
# power-mode ruling 2026-09-25). Species not yet admitted (45 Snow,
# 57 Kurage, 26 Catfish, 27 Tadpole, 84 Hana, 93 BombOtakara, 66 Houdai,
# 97 FminiHoudai) join when their natural campaign evidence lands; nothing
# else keeps them out (#948, #951 R10). 9 Kogane stays out by owner ruling and
# 10/11/16 carry no check (#888, p2_proxy.NO_CHECK_SOURCE_IDS). 0/1/3/4/5/29 are
# P1 duplicates withdrawn by owner ruling 2026-10-01 (p2_proxy.WITHDRAWN_SOURCE_IDS).
P2_PLAYABLE_POOL = (
    {
        "source_id": 44,
        "enum_name": "BlueKochappy",
        "family": "dwarf_orange",
        "evidence": {
            "run": "Dwarf Orange natural run (#461): BlueKochappy spawned, "
                   "movement/animation and attack-state transition observed, "
                   "native death at health 0, corpse, Bestiary delivery check",
            "log": "docs/PIKMIN2_DWARF_ORANGE_NATURAL_RUN_461.md; "
                   "docs/PIKMIN2_DWARF_ORANGE_ROUTE_ACCEPTANCE_440.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 44 -> dwarf_orange "
                         "(experimental/pikmin2_dwarf_orange_install)",
        },
    },
    {
        "source_id": 54,
        "enum_name": "Miulin",
        "family": "mamuta",
        "evidence": {
            "run": "Mamuta natural territory/flick/kill observation "
                   "(lane 19, #221): squad entered territory, three natural "
                   "buries, natural kill at tick 957, carryable corpse",
            "log": "docs/PIKMIN2_MAMUTA_NATURAL.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 54 -> mamuta "
                         "(experimental/pikmin2_mamuta_install)",
        },
    },
    {
        "source_id": 59,
        "enum_name": "FireOtakara",
        "family": "dweevil",
        "evidence": {
            "run": "Lane-22 elemental dweevil native slice (#447): real "
                   "actor-bound FSM (pc_p2_otakara) as a damageable enemy; "
                   "runtime gate covers natural death, corpse, receipt, forget",
            "log": "docs/PIKMIN2_DWEEVIL_NATIVE.md; "
                   "tests/test_pikmin2_otakara_native.py; "
                   "tests/test_pikmin2_otakara_runtime.py",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 59 -> dweevil (p2-dweevil-actors.txt)",
        },
    },
    {
        "source_id": 60,
        "enum_name": "WaterOtakara",
        "family": "dweevil",
        "evidence": {
            "run": "Lane-22 elemental dweevil native slice (#447): real "
                   "actor-bound FSM (pc_p2_otakara) as a damageable enemy; "
                   "runtime gate covers natural death, corpse, receipt, forget",
            "log": "docs/PIKMIN2_DWEEVIL_NATIVE.md; "
                   "tests/test_pikmin2_otakara_native.py; "
                   "tests/test_pikmin2_otakara_runtime.py",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 60 -> dweevil (p2-dweevil-actors.txt)",
        },
    },
    {
        "source_id": 61,
        "enum_name": "GasOtakara",
        "family": "dweevil",
        "evidence": {
            "run": "Lane-22 elemental dweevil native slice (#447): real "
                   "actor-bound FSM (pc_p2_otakara) as a damageable enemy; "
                   "runtime gate covers natural death, corpse, receipt, forget",
            "log": "docs/PIKMIN2_DWEEVIL_NATIVE.md; "
                   "tests/test_pikmin2_otakara_native.py; "
                   "tests/test_pikmin2_otakara_runtime.py",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 61 -> dweevil (p2-dweevil-actors.txt)",
        },
    },
    {
        "source_id": 62,
        "enum_name": "ElecOtakara",
        "family": "dweevil",
        "evidence": {
            "run": "Lane-22 elemental dweevil native slice (#447): real "
                   "actor-bound FSM (pc_p2_otakara) as a damageable enemy; "
                   "runtime gate covers natural death, corpse, receipt, forget",
            "log": "docs/PIKMIN2_DWEEVIL_NATIVE.md; "
                   "tests/test_pikmin2_otakara_native.py; "
                   "tests/test_pikmin2_otakara_runtime.py",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 62 -> dweevil (p2-dweevil-actors.txt)",
        },
    },
    {
        "source_id": 79,
        "enum_name": "Sokkuri",
        "family": "sokkuri",
        "evidence": {
            "run": "Bot-driven power-mode campaign bc5 (owner ruling 2026-09-25: power mode admits): campaign bind, drawn, fight, natural death, corpse carried by 6, Onion receipt onion:p2:79:3; reveal also seen in owner playtest",
            "log": "C:/cop/botcamp-bc5-79-Sokkuri/session/runs/ec5a69e36cc98c686de365365d36a3a064593214bce92675d457dbe183e5a6ec/native.log (sha256 77b9adba1959e718...) L1281 dead, L1413 receipt; output/claude-orch/evidence/botcamp-bc5.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 79 -> sokkuri",
        },
    },
    {
        "source_id": 2,
        "enum_name": "Chappy",
        "family": "chappy",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst-chappy-2r2c (owner ruling 2026-09-25: power mode admits): campaign bind, P2 FSM fight, P2_CHAPPY_DEAD on its own generator, corpse carried, Onion receipt onion:p2:2:3",
            "log": "C:/cop/botcamp-inst-chappy-2r2c-2-Chappy/session/runs/d317bc9411398f68bdfd6b5de32cb13fb87f93208db0bc130e89799ec76b69f9/native.log (sha256 42b170b28c6c721d...) L1463 bind, L2384 dead, L2552 receipt; output/claude-orch/evidence/botcamp-inst-chappy-2r2c.md; output/claude-orch/review/rev2-chappy.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 2 -> chappy "
                         "(experimental/pikmin2_chappy_content)",
        },
    },
    {
        "source_id": 33,
        "enum_name": "FireChappy",
        "family": "chappy",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst-chappy-33r2c (owner ruling 2026-09-25: power mode admits): campaign bind, fire-aura + bite fight, P2_CHAPPY_DEAD on its own generator, corpse carried, Onion receipt onion:p2:33:3",
            "log": "C:/cop/botcamp-inst-chappy-33r2c-33-FireChappy/session/runs/3a4e60615eaab89ae7b8a7dcbe99523433f78bfe2b66497f753ebbf5ca51bb67/native.log (sha256 ad190f3ef357cc3c...) L1484 bind, L2427 dead, L2725 receipt; output/claude-orch/evidence/botcamp-inst-chappy-33r2c.md; output/claude-orch/review/rev2-chappy.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 33 -> chappy "
                         "(experimental/pikmin2_chappy_content)",
        },
    },
    {
        "source_id": 35,
        "enum_name": "KumaChappy",
        "family": "chappy",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst-chappy-35r2c (owner ruling 2026-09-25: power mode admits): campaign bind, patrol/chase/attack fight, P2_CHAPPY_DEAD on its own generator, corpse carried, Onion receipt onion:p2:35:3",
            "log": "C:/cop/botcamp-inst-chappy-35r2c-35-KumaChappy/session/runs/9d74523516ee05540f6899e4f1e75089825c8816cd1dcba9df5173f11433bcfe/native.log (sha256 c327f8233b524391...) L1379 bind, L2236 dead, L2379 receipt; output/claude-orch/evidence/botcamp-inst-chappy-35r2c.md; output/claude-orch/review/rev2-chappy.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 35 -> chappy "
                         "(experimental/pikmin2_chappy_content)",
        },
    },
    {
        "source_id": 43,
        "enum_name": "YellowChappy",
        "family": "chappy",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst-chappy-43r2b (owner ruling 2026-09-25: power mode admits): campaign bind, bite/eat/swallow fight, P2_CHAPPY_DEAD on its own generator, corpse carried, Onion receipt onion:p2:43:3",
            "log": "C:/cop/botcamp-inst-chappy-43r2b-43-YellowChappy/session/runs/f73bd35b8d5753209de5eb1ba39bb200463284099a515cf3d198526a67f4d9d8/native.log (sha256 cb6622f8fb4afa5e...) L1535 bind, L2888 dead, L4275 receipt; output/claude-orch/evidence/botcamp-inst-chappy-43r2b.md; output/claude-orch/review/rev2-chappy.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 43 -> chappy "
                         "(experimental/pikmin2_chappy_content)",
        },
    },
    {
        "source_id": 53,
        "enum_name": "KingChappy",
        "family": "chappy",
        "evidence": {
            "run": "Bot-driven power-mode campaign (owner ruling 2026-09-25: power mode admits) of the OWN-behaviour Emperor Bulblax (wave-3 lane 53, #289): buried HideWait spawn and proximity wake with the Appear shake-off, tongue/eat/swallow fights with the tongue-tip terrain trace, checkFlick shake-offs, WarCry x7, dive (Hide) and re-Appear, retail collision tree with head/nose/mouth stickable parts, P1 Emperor sound bank; P2_CHAPPY_DEAD on its own generator 1945764764, corpse carried, Onion receipt onion:p2:53:3 (AUTOPLAY_RESULT killed=1 carried=1 received=1). Seed: spring_init_7002 smoke-override slot (PIKMIN_P2_SMOKE_ANY_SLOT, scripts/p2_smoke_seed.py --slot-uids); native claude/p2-wave3-53-emperor 03e8fd23f, exe sha256 da96b5ff... (private IPO build); a second run on the previous exe (s9) killed, carried and delivered the same way.",
            "log": "output/claude-orch/p2-w3-53/runs/s12/session/runs/09ef65f20941a20d25701f95380624906f925eefdd80064fdfa28c8920ae0b5c/native.log (sha256 723bfe1743bbf31b...) L1300 bind, L1486 wake, L1509 appear, L5275 dead, L5399 receipt; scored by output/claude-orch/p2-w3-53/king_score.py; docs/PIKMIN2_KING_OWN.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 53 -> chappy "
                         "(experimental/pikmin2_chappy_content)",
        },
    },
    {
        "source_id": 67,
        "enum_name": "LeafChappy",
        "family": "chappy",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst-chappy-67r2b (owner ruling 2026-09-25: power mode admits): campaign bind, Kuma-chase attack fight, P2_CHAPPY_DEAD on its own generator, corpse carried, Onion receipt onion:p2:67:3",
            "log": "C:/cop/botcamp-inst-chappy-67r2b-67-LeafChappy/session/runs/a2f57b648a5c82aac00abace5994aac254cc6e41d206b72c6339c56cde1ea7d7/native.log (sha256 df677b77fdb4b3c0...) L1536 bind, L2624 dead, L3946 receipt; output/claude-orch/evidence/botcamp-inst-chappy-67r2b.md; output/claude-orch/review/rev2-chappy.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 67 -> chappy "
                         "(experimental/pikmin2_chappy_content)",
        },
    },
    {
        "source_id": 76,
        "enum_name": "KumaKochappy",
        "family": "chappy",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst-chappy-76r2 (owner ruling 2026-09-25: power mode admits): campaign bind, dwarf-frame attack fight, P2_CHAPPY_DEAD on its own generator, corpse carried, Onion receipt onion:p2:76:3",
            "log": "C:/cop/botcamp-inst-chappy-76r2-76-KumaKochappy/session/runs/c5f6a83fa072e41d2970c84e85e2197e0e57ffb762066a30f5466da71d37f875/native.log (sha256 16ed59ee27b0389f...) L1514 bind, L2316 dead, L2963 receipt; output/claude-orch/evidence/botcamp-inst-chappy-76r2.md; output/claude-orch/review/rev2-chappy.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 76 -> chappy "
                         "(experimental/pikmin2_chappy_content)",
        },
    },
    {
        "source_id": 28,
        "enum_name": "ElecBug",
        "family": "elecbug",
        # Placement unit (owner ruling 2026-09-30): a slot given an Anode Beetle gets a
        # linked PAIR. Data, not code: randomizer/p2_units.py stages it for the native
        # generator hook (pc_port/pc_p2_species_unit.h); rows without "unit" mean 1.
        "unit": 2,
        "evidence": {
            "run": "Bot-driven power-mode campaign inst-bugs-10 (owner ruling 2026-09-25: power mode admits): campaign bind, NATURAL_PRESS flip, graduated HITs on own token, DEAD, corpse carried, Onion receipt onion:p2:28:3",
            "log": "C:/cop/botcamp-inst-bugs-10-28-ElecBug/session/runs/5bc3ed6eb0f934aae4db128c293e50cd8bb55af006bf8ca93b96bf72189a7665/native.log (sha256 d6b74d9abef0f6fc...) L1860 bind, L2043 dead, L2239 receipt; output/claude-orch/evidence/botcamp-inst-bugs-10.md; output/claude-orch/review/rev2-bugs.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 28 -> elecbug "
                         "(experimental/pikmin2_elecbug_content)",
        },
    },
    {
        "source_id": 94,
        "enum_name": "DangoMushi",
        "family": "dangomushi",
        "evidence": {
            "run": "Bot-driven power-mode campaign v2f in the impact_goolix boss arena (#897/#899; natural playable seed dango-arena-impact_goolix-impact-0, no rebind; TEST-ONLY PIKMIN_P2_TEST_START_DAY=11, since the arena goes live on day 9, so a normal campaign meets 94 there on day 9 or later): P2_BOSS_ARENA_BIRTH on the arena primary, bind, rain drawn (ROCK_DRAW), Turn-window DAMAGE_ACCEPTED only, DEAD from turn on its own generator 4019261003, carcass row 20/30/30, corpse drawn on the carried pellet (CORPSE_DRAW) and carried by 22, Onion receipt onion:p2:94:0",
            "log": "output/claude-orch/p2-port-94/runs/v2f-94/session/runs/ef11a6259feab977d2b324e7115cbbaf7da209c5c9cc9f35669a1579cc3610ac/native.log (sha256 0c3408dc1a1f83ba...) L704 arena birth, L1073 bind, L1643 dead, L1966 receipt; repeat v2h at power 2 (sha256 5f4d78f5d57e389b...) L1732 dead, L2050 receipt; native claude/p2-port-94-arena-v2 @ a4aa232a4, nectar.exe sha256 ecf8d6512f5d0f4a...",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 94 -> dangomushi "
                         "(experimental/pikmin2_dangomushi_content)",
        },
    },
    {
        "source_id": 68,
        "enum_name": "TamagoMushi",
        "family": "tamago",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst-bugs-12 (owner ruling 2026-09-25: power mode admits): campaign bind, ASTONISH receiver + TURN chain, DEAD + exactly-once HONEY on its own generator, receipt onion:p2:68:3",
            "log": "C:/cop/botcamp-inst-bugs-12-68-TamagoMushi/session/runs/7540e2703f9dbf8ed6ec4e57f689f89a69091df3370521b5a86e9b803d48020d/native.log (sha256 6969d5021da9c359...) L1765 bind, L2103 dead, L2178 receipt; output/claude-orch/evidence/botcamp-inst-bugs-12.md; output/claude-orch/review/rev2-bugs.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 68 -> tamago "
                         "(experimental/pikmin2_tamago_content)",
        },
    },
    {
        "source_id": 75,
        "enum_name": "Kabuto",
        "family": "kabuto",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst-frogs-6 (owner ruling 2026-09-25: power mode admits): campaign bind, stone-fire + flick fight, P2_KABUTO_DEAD on its own generator, corpse carried, Onion receipt onion:p2:75:3",
            "log": "C:/cop/botcamp-inst-frogs-6-75-Kabuto/session/runs/12e38cfb44bbf91e25b587007f49f46c02d413f237ffc82c56806cf8d110a5f4/native.log (sha256 1c4fcd69d4c39360...) L1002 bind, L2025 dead, L2144 receipt; output/claude-orch/review/rev2-frogs.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 75 -> kabuto "
                         "(experimental/pikmin2_kabuto_identity_install)",
        },
    },
    {
        "source_id": 63,
        "enum_name": "Jigumo",
        "family": "aquatic",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst-legs-63g (owner ruling 2026-09-25: power mode admits): campaign bind, BITE frame-13 + EAT kill chain, P2_JIGUMO_DEAD on its own generator, dead1 P2 corpse carried, Onion receipt onion:p2:63:3",
            "log": "C:/cop/botcamp-inst-legs-63g-63-Jigumo/session/runs/de11d3a39c06c3f956c6e23fa8332d22ed62bc24ba3f0da5594b5a8490cf81c8/native.log (sha256 1a63f2dcdb8ab0e1...) L1763 bind, L2060 dead, L4256 receipt; output/claude-orch/review/rev2-legs.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 63 -> aquatic "
                         "(experimental/pikmin2_aquatic_install)",
        },
    },
    {
        "source_id": 69,
        "enum_name": "BigFoot",
        "family": "long_legs",
        "evidence": {
            "run": "Owner ruling #1088 (2026-10-01): no carcass or Pikmin seed yield; earn the check on kill, with stable onion:p2 identity and legacy AP location name. Historical transport evidence below predates this ruling. Bot-driven power-mode campaign inst-legs-69b (owner ruling 2026-09-25: power mode admits): campaign bind, flick-shake fight, P2_LONG_LEGS_DEAD on its own generator, P2 corpse carried, Onion receipt onion:p2:69:3",
            "log": "No-carcass #1088: output/codex-1088-death-69-2/native.log (sha256 e5320bfd7091a5ba56898cc583a4c847f9a87402601fc4cb3100b38cbaccbbf4; native d703218cae578376338fd292aed8477949a661b4); power x30 combat, death clip/burst then host escape, no corpse, kill receipt onion:p2:69:1 new=1 on generator 4222852521. Historical: C:/cop/botcamp-inst-legs-69b-69-BigFoot/session/runs/d7683ffb7f6a225e090df66ee446cec0cffa9bc09a8c35ba0051a265354d5a3f/native.log (sha256 0fbcb5d984defcdf...) L1586 bind (own token 1945764764; DELIVERY_BIND L1581), L1751 dead, L1810 receipt; output/claude-orch/review/rev2-legs.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 69 -> long_legs "
                         "(experimental/pikmin2_long_legs_install)",
        },
    },
    {
        "source_id": 34,
        "enum_name": "SnakeCrow",
        "family": "snagret",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst2-worms-34b (owner ruling 2026-09-25: power mode admits): campaign bind, bite/swallow fight, P2_SNAKEJOINT_DEAD on its own generator, corpse carried, Onion receipt onion:p2:34:3",
            "log": "C:/cop/botcamp-inst2-worms-34b-34-SnakeCrow/session/runs/dc225b9c2546438ff9f915eb7026e36bddd7c3027fca1ca58554a28124a0481b/native.log (sha256 b0d739e34150821b...) L1757 bind, L2066 dead, L2239 receipt; DRAW L1935 P2_SNAKEJOINT_DRAW own token 1945764764; output/claude-orch/evidence/botcamp-inst2-worms-34b.md; output/claude-orch/review/rev2-worms.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 34 -> snagret "
                         "(experimental/pikmin2_snagret_install)",
        },
    },
    {
        "source_id": 70,
        "enum_name": "SnakeWhole",
        "family": "snagret",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst2-worms-70 (owner ruling 2026-09-25: power mode admits): campaign bind, Walk/Home + bite fight, P2_SNAKEJOINT_DEAD on its own generator, corpse carried, Onion receipt onion:p2:70:3",
            "log": "C:/cop/botcamp-inst2-worms-70-70-SnakeWhole/session/runs/1fd7bc0224c8b33d7d816579a49401c239b547d438c5a5c85fba89c21437d058/native.log (sha256 90fd5518feab2872...) L1675 bind, L2163 dead, L2464 receipt; DRAW L1856 P2_SNAKEJOINT_DRAW own token 1945764764; output/claude-orch/evidence/botcamp-inst2-worms-70.md; output/claude-orch/review/rev2-worms.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 70 -> snagret "
                         "(experimental/pikmin2_snagret_install)",
        },
    },
    {
        "source_id": 71,
        "enum_name": "UmiMushi",
        "family": "aquatic",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst2-worms-71b (owner ruling 2026-09-25: power mode admits): campaign bind, attack/bite/eat cycles with graduated damage, P2_UMIMUSHI_DEAD on its own generator, corpse carried, Onion receipt onion:p2:71:3",
            "log": "C:/cop/botcamp-inst2-worms-71b-71-UmiMushi/session/runs/ad8b6c0a57bc5ec65f8f372ba7a0e10c640ac3933a1bc6842f2f5779a2312b0f/native.log (sha256 c6a4a34f6a9149e4...) L1778 bind, L2109 dead, L2254 receipt; output/claude-orch/evidence/botcamp-inst2-worms-71b.md; output/claude-orch/review/rev2-worms.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 71 -> aquatic "
                         "(experimental/pikmin2_aquatic_install)",
        },
    },
    {
        "source_id": 101,
        "enum_name": "UmiMushiBlind",
        "family": "aquatic",
        "evidence": {
            "run": "Bot-driven power-mode campaign inst2-worms-101 (owner ruling 2026-09-25: power mode admits): campaign bind with Blind split params, walk/attack/eat cycles, P2_UMIMUSHI_DEAD on its own generator, corpse carried, Onion receipt onion:p2:101:3",
            "log": "C:/cop/botcamp-inst2-worms-101-101-UmiMushiBlind/session/runs/efd65a456bc5d6e2fee2f0750a74472a1f18b2932883255a83fd4202cab43735/native.log (sha256 2cd7b541d1d6c453...) L1680 bind, L2140 dead, L2365 receipt; output/claude-orch/evidence/botcamp-inst2-worms-101.md; output/claude-orch/review/rev2-worms.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 101 -> aquatic "
                         "(experimental/pikmin2_aquatic_install)",
        },
    },
    {
        "source_id": 25,
        "enum_name": "Wtank",
        "family": "tank",
        "evidence": {
            "run": "Bot-driven power-mode campaign frogs5-25 (owner ruling 2026-09-25: power mode admits): blue squad POWER=30, campaign bind, breath-cone fight, P2_TANK_DEAD on its own generator, corpse carried, Onion receipt onion:p2:25:3",
            "log": "C:/cop/botcamp-frogs5-25-Wtank/session/runs/6f7f48ec5786daf3784f517aaf00786f6a5423af2950f18996a010955372c3a3/native.log (sha256 ba67a715fb46fb56...) L1060 bind, L1702 dead, L1930 receipt; output/claude-orch/evidence/botcamp-frogs5.md; output/claude-orch/review/rev6-frogs5.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 25 -> tank "
                         "(experimental/pikmin2_tank_identity_install)",
        },
    },
    {
        "source_id": 15,
        "enum_name": "Armor",
        "family": "armor",
        "evidence": {
            "run": "Bot-driven power-mode campaign frogs5b-15 (owner ruling 2026-09-25: power mode admits): blue squad POWER=10, campaign bind, GoHome/flick/attack2 fight with two incremental DAMAGE lines, P2_ARMOR_DEAD on its own generator, corpse carried, Onion receipt onion:p2:15:3",
            "log": "C:/cop/botcamp-frogs5b-15-Armor/session/runs/5994608956e0b4ce8d562b1f1d61bbcda85947a2d5996f6216fe0123483bc759/native.log (sha256 889febb33ff5c33...) L996 bind, L1918 dead, L2401 receipt; product-content loop C:/cop/botcamp-admitprod-b15-15-Armor/session/runs/12176a0d9c26dd39cdb48d0bdeeb8b895151c17f51678e44cf787203e84f7991/native.log (sha256 24219d621ef8ea6c...) L1037 bind, L1775 dead, L2170 receipt; output/claude-orch/evidence/botcamp-frogs5.md; output/claude-orch/review/rev6-frogs5.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 15 -> armor "
                         "(ADAPTERS 'armor' via _adapt_ground_inverts)",
        },
    },
    {
        "source_id": 78,
        "enum_name": "MiniHoudai",
        "family": "minihoudai",
        "evidence": {
            "run": "Bot-driven power-mode campaign fx1 (owner ruling 2026-09-25: power mode admits; #888 section 4A, #892): red squad, campaign OWN bind of the source MiniHoudai FSM, 4 three-shell volleys with drawn shell effects, flick, 71 DAMAGE lines, P2_GROINK_DEAD on its own generator, corpse carried, Onion receipt onion:p2:78:3; owner eye-checked facing and shells",
            "log": "output/claude-orch/p2-groink-own/runs/fx1-78/session/runs/405a7edd3ba314b2f59c8d99c3633c583e0e545d4947efce9854d6c374e9510b/native.log (sha256 9fbb22ea6448eecb...) L1106 bind, L2295 dead, L2535 receipt; native claude/p2-groink-shell-fx 65f8d281f, exe sha256 af13c9254f784a07...; #888 issuecomment-5875447908",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 78 -> minihoudai "
                         "(stages p2-groink-parms/fixed-parms/bank and the minihoudai pose meshes)",
        },
    },
    {
        "source_id": 73,
        "enum_name": "BigTreasure",
        "family": "bigtreasure",
        "evidence": {
            "run": "Bot-driven power-mode campaign e7 (owner ruling 2026-09-25: power mode admits; #246, boss arena #899): natural playable seed bt-own-73-red-impact-0 places 73 in the impact_goolix boss arena; red squad, source BigTreasure FSM with retail collision parts, all four weapons knocked off by Pikmin on their own parts, body damage only after the last drop, P2_BIGTREASURE_DEAD on its own generator, carryable corpse (owner ruling 2026-09-29 #1) carried, Onion receipt onion:p2:73:0; repeated in e3-e6/e8, re-entry across days 11-15 in rc2",
            "log": "output/claude-orch/p2-bigtreasure-own/runs/e7-73/session/runs/370351d982abac8ba6a36d43d748b2cd2a3056da284557caf157bba4d2e98f5c/native.log (sha256 f9ceec6c30bee188...) L1367 bind, L2060 dead, L2139 receipt; native claude/p2-port-73-titan-v2 ad5124e12, exe sha256 2010385d86baaea7...; #246",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 73 -> bigtreasure "
                         "(stages the retail enemyparm/enemycoll, event table, pose bank and weapon meshes)",
        },
    },
    {
        "source_id": 32,
        "enum_name": "Demon",
        "family": "demon",
        "evidence": {
            "run": "Bot-driven power-mode campaign v2b (owner ruling 2026-09-25: power mode admits; #215): red squad, campaign OWN bind of the Demon profile of the Sarai FSM with retail parms, 4 captain grabs each dropped for 10 damage, flick, fall under Pikmin weight, 82 DAMAGE lines, P2_DEMON_DEAD on its own generator, type5 carcass carried, Onion receipt onion:p2:32:3",
            "log": "output/claude-orch/p2-demon-own/runs/v2b-32/session/runs/066dd7552325f90932b03f651dc88496a20f0e9bec57d788b4fa081d6a25170a/native.log (sha256 eb38e61bcca84a82...) L1578 bind, L2812 capture, L2876 drop, L3632 dead, L3926 receipt; native claude/p2-port-32-demon-v2 6e88fad0d, exe sha256 c329ed2d0a0e5209...",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 32 -> demon "
                         "(stages the demon-* parms/bank and the demon pose meshes)",
        },
    },
    {
        "source_id": 38,
        "enum_name": "PanModoki",
        "family": "breadbug",
        "evidence": {
            "run": "Bot-driven power-mode campaign runs z2, z3 and z6 (owner ruling 2026-09-25: power mode admits; #898 second review): red squad, campaign OWN bind of the source PanModoki FSM, never a Pikmin or captain target (0 attacks), grabs a carcass and hauls it home through Back, CarryEnd, Hide (refill, carcass spared) and Appear, dies to six thrown-Pikmin presses 1100->-100, OWN_DEAD on its own generator, corpse carried, Onion receipt onion:p2:38:3 in all three runs",
            "log": "output/claude-orch/p2-breadbug-own/runs/z2-38/session/runs/57cb91f00857a4b3be3874c89b5018a340ad2dc415c6d0b6be0b904766e8d39c/native.log (sha256 f89d2a6eb8691c51...) L1259 bind, L4732 dead, L4898 receipt; z3 L5526 receipt, z6 L6902 receipt; native claude/p2-port-38-breadbug-v2 91fe15a50, exe sha256 0248be824d662aea...; #898",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 38 -> breadbug "
                         "(stages p2-breadbug-parms/bank and the breadbug pose meshes)",
        },
    },
    {
        "source_id": 40,
        "enum_name": "OoPanModoki",
        "family": "giantbreadbug",
        "evidence": {
            "run": "Bot-driven power-mode campaign runs on the final exe (owner ruling 2026-09-25: power mode admits; #958), Purple opt-in staged through randomizer run --purple-bank/--purple-motion: y11 (final exe 971d2df5, the only run on it) = the owner FoH smoke seed itself (six Giants on the six FoH slots nearest the start, all P2_BREADBUG_OWN_BIND), bot kills the Giant on FoH slot hope_0-29_2659 (own generator 4222852521), staged FoH Violet handled a Purple (P2_VIOLET_WITNESS), 22 accepted 100-point presses, OWN_DEAD, corpse carried, onion:p2:40:1 receipt; y9 = real generated seed, Forest of Hope start, Giant on the FoH slot hope_0-29_2659 (own generator 4222852521, 720 units from the start), the staged FoH Violet handled a Purple (P2_VIOLET_WITNESS), 20 accepted 100-point presses 2000->0, OWN_DEAD, corpse carried, onion:p2:40:1 receipt; repeated pre-merge as y4 and at Distant Spring as y2 (generator 1945764764, onion:p2:40:3). Admitted on ordinary slots only; arena placement is NOT admitted. Arena runs r9 (navel_beady_long_legs) and r11 (spring_cannon_beetle), both on the pre-merge exe dc6a9f30 (not the final exe): the Giant binds in the arena, wanders and 20 presses kill it (killed=1), but nobody carried the corpse (carried=0, received=0), so there is no arena receipt; the carry stall was not diagnosed from the log (the bot's own planner logged no_path from the landing to those arenas in r5/r7, which is only a suspect). It has no boss-arena descriptor and is not seated in any arena. Negative y5 (banks staged, squad not Purple): non-Purple presses refused (PRESS_REJECTED x2), health stays 2000, 0 presses. Limits: the squad is made Purple by the test-only AUTOPLAY_PURPLE power switch, not through the Violet supply; the arena runs teleport the captain to the arena (#901); y7 killed the Giant by container suck plus 10 presses but the corpse jammed at (-192,2052) on the FoH plateau",
            "log": "output/claude-orch/p2-w3-variants-breadbug/runs/y11-40/session/runs/9aed7600eb5ba9a70f6cbeee5063d27094806708eca00a9dacb444534f4fb90e/native.log (sha256 49905baf875d4bf4...) L1449 bind, L1713 purple squad, L2761 first press, L3360 Violet witness, L6806 dead, L7088 receipt; y9-40 native.log (sha256 a0d4d7ba6c91c8aa...) L1806 bind, L3574 purple squad, L5800 first press, L7682 Violet witness, L10510 dead, L11973 receipt; y4-40 native.log (sha256 1147bb281607a7ff...) L1806 bind, L12534 dead, L12923 receipt; y2-40 (sha256 7c6b5c28049d33e3...) L1928 bind, L47676 dead, L51492 receipt; r9-40 (sha256 e2daca825dba2ef5...) L1485 bind, L2401 dead; r11-40 (sha256 2bd302d6f6fedcb0...) L1486 bind, L3614 dead; y5-40 (sha256 21d1163185d64b36...); y7-40 (sha256 b017f3277919b2f6...); native claude/p2-wave3-variants-breadbug 0e6369a80, exe sha256 971d2df549624a3d... (y11), ef6077c9067a55fa... (y9, y7), dc6a9f30c048619392d5... (y4, y2, y5, r9, r11); #958",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 40 -> giantbreadbug "
                         "(stages p2-giantbreadbug-parms/bank and the giantbreadbug pose meshes)",
        },
    },
    {
        "source_id": 41,
        "enum_name": "Fuefuki",
        "family": "fuefuki",
        "evidence": {
            "run": "Bot-driven power-mode campaign runs (owner ruling 2026-09-25: power mode admits; #245) on native f60b8a1e7 with the P1 Land/Walk target guard: campaign OWN bind of the source Fuefuki FSM on a P1 Chappy teki with its AI suppressed, whistle casts steal and release followers, a thrown Pikmin lands in the mCanStruggle window and flips it into Struggle, jump/stay/land cycle, P2_FUEFUKI_DEAD on its own generator, corpse carried, Onion receipt. Full chain on three maps: d7 Distant Spring (slot 1945764764, harness rebind, onion:p2:41:3), v1 Forest Navel on a NATURAL seed with no rebind (fue-nat-navel-g6, slot 873045719, onion:p2:41:2), f3 Forest of Hope (slot 2049888785, harness rebind, onion:p2:41:1). Correction: pre-guard run d4 (exe 97cf4d08) killed the beetle on a ledge ~76 u above home after a Land roll put it there; four carriers lifted the corpse but its route to the Onion stalled on a closed waypoint (P1 path-blocked message), carried=0. That failure is why the guard exists",
            "log": "output/claude-orch/p2-port-41/runs/d7-41/session/runs/a5c8ec4ee2a89d146c65e986b54dc461c7651a61d62d2ff1e0f805bce5369b2a/native.log (sha256 c918ca45765da57e...) receipt L3451; output/claude-orch/p2-port-41/runs/v1-41/session/runs/05a0e945002c161aed4f14092f458853fa0d8d8778182efcf5d2682f67f43da4/native.log (sha256 3e79931b1c859f47...) receipt L4678; output/claude-orch/p2-port-41/runs/f3-41/session/runs/c17d3b3ca790114e1e488b12f48731849f68bafb97f992de55b0de1736e94a80/native.log (sha256 8795a90bce819ead...) receipt L5583; native claude/p2-port-41-antenna-beetle-v2 f60b8a1e7, exe sha256 9cb65f685fb91b6c...; #245",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 41 -> fuefuki "
                         "(stages p2-fuefuki-parms/motion/bank and the fuefuki pose meshes)",
        },
    },
    {
        "source_id": 58,
        "enum_name": "BombSarai",
        "family": "bombsarai",
        "evidence": {
            "run": "Bot-driven campaign runs v1 (normal 20 squad) and v2p (power mode; owner ruling 2026-09-25: power mode admits) (#244): red squad, campaign OWN bind of the source BombSarai FSM with retail parms, hover, bomb Supply/BombMove/Release, lethal blast (v2p pikmin_lethal=81, field 100->19; v1 lethal 2, field 20->18), latch/Fall/Damage/TakeOff/Flick, natural death on its own generator, corpse carried, Onion receipt onion:p2:58:3",
            "log": "output/claude-orch/p2-bombsarai-own/runs/v2p-58/session/runs/a6264c6ad0f250aa0444a8922ddf8b866f1f573eb7fc0b40e0c045f615ca30f9/native.log (sha256 30384556062612033...) L1251 bind, L2144 blast, L2226 dead, L2538 receipt; v1 native.log sha256 fd7367f8612d6b9a... L2851 receipt; native claude/p2-port-58-bombsarai-v2 e54d87ff5, exe sha256 b15b6c0044c39d67...",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 58 -> bombsarai "
                         "(stages p2-bombsarai-parms/bomb-parms/own-bank and the Bomb meshes)",
        },
    },
    {
        "source_id": 57,
        "enum_name": "Kurage",
        "family": "kurage",
        "evidence": {
            "run": "Owner ruling #1088 (2026-10-01): no carcass or Pikmin seed yield; earn the check on kill, with stable onion:p2 identity and legacy AP location name. Historical transport evidence below predates this ruling. Bot-driven power-mode campaign run k6 (owner ruling 2026-09-25: power mode admits; wave 3 flyers, #960): red squad, campaign OWN bind of the source Kurage FSM with retail parms (life 2500, flight height 70) on a P1 Frog host with its AI suppressed; the hovering body is EB_Untargetable (CF_IsFlying mirror) so ground Pikmin leave it alone while thrown Pikmin latch onto the retail collision spheres (60 airborne latches), 13 FlyFlick shake-offs, suction of Pikmin, 151 monotone DAMAGE lines 2485 to 10, P2_KURAGE_OWN_DEAD on its own generator, corpse drawn as dead1 and carried, Onion receipt onion:p2:57:3; normal-squad run k7 shows the six-latch Fall, Land, grounded squad attack, GroundFlick and TakeOff before the natural kill; final-exe run f3 (power mode, exe sha256 1620698f169f0b82..., native 272f3807d) repeats the chain to the receipt onion:p2:57:3 and day-cycle run r5 keeps the Lesser alive across three stage loads",
            "log": "No-carcass #1088: output/codex-1088-death-57-2/native.log (sha256 8c3c3adc1345ab4158aa6050ec23d58cdfa2f23cf51f333dc91ab869f34071ba; native d703218cae578376338fd292aed8477949a661b4); power x30 combat, death clip/burst then host escape, no corpse, kill receipt onion:p2:57:1 new=1 on generator 4222852521. Historical: FINAL EXE (bin-b12, nectar.exe sha256 1620698f169f0b82cf5c9749424d5edea556fce30aa972f20afe97cf1aafc59a, native claude/p2-wave3-flyers 272f3807d): f3 output/claude-orch/p2-w3-flyers/runs/f3-57/session/runs/5a6ad2d410947cb8ad338bde02798df8dead912cedb39e5cdfb8460c22e5300e/native.log (sha256 117eb8ac47d65821...) L1320 bind, L11522 dead, L11739 corpse, L13487 receipt onion:p2:57:3 new=1; r5 day cycle output/claude-orch/p2-w3-flyers/runs/r5-72/session/runs/c0ea02ab04b2b16e4e2be1eca3351f2dba180409da1ec72115a9fd168ddb743a/native.log (sha256 3cb9842f89c2121a...) Lesser alive at both sunsets, rebound each day. FIRST-ADMISSION runs on an OLDER exe (k6 recorded only the gdbexe.cmd wrapper sha256 c3a7868b5c49..., so its exe is attributed to bin-b5, e929736321f3..., by timestamp; k7 is recorded on b5): output/claude-orch/p2-w3-flyers/runs/k6-57/session/runs/224c4a3aa5e9821ad910eeeb95f232a3fad7e86cb0ccf1b2b1de73ba619e47bb/native.log (sha256 a3ff30c09e624b62...) L1387 bind, L4276 first latch, L4417 FlyFlick, L8098 dead, L8209 escape, L9247 receipt; k7 (output/claude-orch/p2-w3-flyers/runs/k7-57/session/runs/a5c1d2bef108f347eb9a72a8dde49b9096a05be6e6e3cdf207b9963007697368/native.log sha256 2c8c498d9aad4...) L4760 Fall, L4868 Land, L4914 grounded latch, L7132 dead; native f599fe03a as first built",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 57 -> kurage "
                         "(stages p2-kurage-teki.txt and the kurage pose meshes)",
        },
    },
    {
        "source_id": 72,
        "enum_name": "OniKurage",
        "family": "onikurage",
        "evidence": {
            "run": "Owner ruling #1088 (2026-10-01): no carcass or Pikmin seed yield; earn the check on kill, with stable onion:p2 identity and legacy AP location name. Historical transport evidence below predates this ruling. Bot-driven power-mode campaign runs e1 and e2 (owner ruling 2026-09-25: power mode admits; wave 3 flyers, #960): red squad, campaign OWN bind of the Greater Kurage FSM with retail parms (life 4500, flight 75, territory 500, suck 20) and the retail collision tree; the hovering body is untargetable (CF_IsFlying mirror) while thrown Pikmin latch; the captain is sucked into the mouth slot, the body drops (Drop), lands, the whole squad attacks the grounded body (56 stuck), GroundFlick vomits the captain out with the fp24 damage, TakeOff, 17 latched Pikmin bring it down again (Fall), natural death on its own generator 1945764764, dead1 corpse carried, Onion receipt onion:p2:72:3 (captain suction observed on the earlier exe in e1; the final-exe runs e4 and e5 show Drop, Land, the grounded squad attack, death and the receipt); the normal-squad day cycle r5 keeps the live 72 across three stage loads",
            "log": "No-carcass #1088: output/codex-1088-death-72-2/native.log (sha256 5dc4b9e73ecf6e45ae2a4bc6e93f0609e22a428edf4c44118bf29d58b13e0654; native d703218cae578376338fd292aed8477949a661b4); power x30 combat, death clip/burst then host escape, no corpse, kill receipt onion:p2:72:1 new=1 on generator 2049888785. Historical: FINAL EXE (bin-b12, nectar.exe sha256 1620698f169f0b82cf5c9749424d5edea556fce30aa972f20afe97cf1aafc59a, native claude/p2-wave3-flyers 272f3807d): e4 output/claude-orch/p2-w3-flyers/runs/e4-72/session/runs/53c07bad63e6497e7c645e535c95c96ed998e6a1f15be153c369be2044de8f62/native.log (sha256 979cabe44367...) L4626 Drop, L4659 Land, L5072 dead, L5181 corpse, L6018 receipt onion:p2:72:3 new=1; e5 output/claude-orch/p2-w3-flyers/runs/e5-72/session/runs/5519bd34c0b87ca921c27c0aa99dd46c065c0b91e43d097257ed67e3d5f27669/native.log (sha256 fb34a858220a...) receipt L5909; r5 normal-squad day cycle output/claude-orch/p2-w3-flyers/runs/r5-72/session/runs/c0ea02ab04b2b16e4e2be1eca3351f2dba180409da1ec72115a9fd168ddb743a/native.log (sha256 3cb9842f89c2121a...) the 72 alive at L6634 and L13605 SUNSET, rebound at L1338, L7770, L14734. EARLIER exe b10 (3b5eef6ad9dd...): e1 output/claude-orch/p2-w3-flyers/runs/e1-72/session/runs/e2f2cb1bf7b8cc89a27386b517eeda002bb58620299f784149be3efcfb057967/native.log (sha256 8a49bb81feb1d7e8...) L4413 captain capture, L4495 Drop, L4709 captain release, L6020 receipt.",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 72 -> onikurage "
                         "(stages p2-kurage-teki.txt and the onikurage pose meshes)",
        },
    },
    {
        "source_id": 30,
        "enum_name": "Queen",
        "family": "queen",
        "evidence": {
            "run": "Bot-driven campaign runs a17 (power x30) and a16 (power x3), wave 3 (#256; owner ruling 2026-09-25: power mode admits): natural seed qa-impact-0, no rebind, queen_arena placed the Empress Bulblax in the impact_goolix boss arena (TEST-ONLY start day 11, the arena is live from day 9); a17: P2_BOSS_ARENA_BIRTH, source Queen FSM bind, natural kill, carcass carried by up to 32 Pikmin, Onion receipt onion:p2:30:0 on her own generator 4019261003; a16 (same exe): Born larvae, Wait->Damage->Flick->Rolling cycles, 21 rolling presses crushing Pikmin, 13 flicked off, health 5000->0",
            "log": "output/w3-30-run/runs/a17-30/session/runs/214baf1f7f068380494de690b4bceab1ede67dd7bb4566779acbca941f5fd83f/native.log (sha256 479d0b20603cf3580ee577686a901512...) L714 arena birth, L1671 bind, L1956 dead, L2035 receipt; a16 native.log sha256 4345ba04dde58e27...; native claude/p2-wave3-30-empress 6d0378bf8, exe sha256 fef86e9e6b672a66...",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 30 -> queen "
                         "(ADAPTERS 'queen' via _adapt_queen / pikmin2_queen_stage)",
        },
    },
    {
        "source_id": 31,
        "enum_name": "Baby",
        "family": "queen",
        "evidence": {
            "run": "Owner ruling #1088 (2026-10-01): no carcass or Pikmin seed yield; earn the check on kill, with stable onion:p2 identity and legacy AP location name. Historical transport evidence below predates this ruling. Bot-driven campaign runs on the existing Baby FSM (owner ruling 2026-10-01 queued larva; power-mode runs admit per the 2026-09-25 ruling): p4 (smoke package, power x3), n2 (normal squad) and nat2 (natural seed, committed placement, no smoke override, power x3): standalone P2_LARVA_OWN_BIND, captain bites and swallowPikmin kills, natural death, a carryable corpse carried to the Onion, receipt onion:p2:31:1 on the larva's own generator (nat2 4222852521; p4 and n2 also 1877315663)",
            "log": "No-carcass #1088: output/codex-1088-death-31-2/native.log (sha256 4106a1d36c572adfcfc4877342cc80fa01b73173c05fcd401d0af9527370e776; native d703218cae578376338fd292aed8477949a661b4); power x30 combat, death clip/burst then host escape, no corpse, kill receipt onion:p2:31:1 new=1 on generator 4222852521. Historical: output/larva-evidence/nat2/runs/00bd993b66d9f927e4c4f7b9bbd3ee83e5fd5feeee02db0f20ceadad68e18f82/native.log (sha256 b1e471019c9390a3...) L1287 bind, L1555 dead, L1569 carcass, L1612 receipt; output/larva-evidence/p4/runs/d7c9a6b0f689dc5faef77be04717000cc157e8949d2fec2a4788bfed9bf5def6/native.log (sha256 ce9aa9476cfa9948...) L1242 bind, L1470 bite, L1485 swallow, L1492 dead, L1536 and L1549 receipts; output/larva-evidence/n2/runs/44a03750a24c800a044d2481ee4dc4099eac11375225b2fd83eebe934c267ca6/native.log (sha256 c90f67ed89b322bb...) L1437 swallow, L1779 dead, L1863 receipt; native claude/p2-larva-31 cc2f51f5d (fork/main 7a9f7dcab), nectar.exe sha256 bfcd8bff980ad063fdac4d...d242",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 31 -> queen "
                         "(ADAPTERS 'queen' via _adapt_queen / pikmin2_queen_stage; Baby tree from extract_baby)",
        },
    },
    {
        "source_id": 26,
        "enum_name": "Catfish",
        "family": "aquatic",
        "evidence": {
            "run": "Bot-driven power-mode campaign runs j26 and l26 (owner ruling 2026-09-25: power mode admits; wave 3 mechanics, #964): red squad, campaign bind of the transcribed source Catfish FSM (KochappyBase wait/turn/walk/attack/flick/gohome/dead with the retail parms, life 200) on the Catfish's own generator token; walk, attackNavi, BITE frame 17 on both mouth slots, flick shake-offs, damage from the squad down to P2_CATFISH_DEAD, the dead corpse carried, Onion receipt onion:p2:26:3. Day-cycle run l26: a fresh Catfish binds each stage, alive at two sunsets, killed and delivered in the third stage (day 4). The kill runs used a land slot (start-area slot rebind); the water slots were only checked for binding (run w26, earlier exe)",
            "log": "output/claude-orch/p2-w3-mech/runs/j26-26/session/runs/688307161d692c6f2c0a95e37caaf16d687e2e64590e56458ef4523f77e3b9e2/native.log (sha256 a96d490796eac61f...) L3483 bind, L5129 dead, L5930 receipt; day cycle output/claude-orch/p2-w3-mech/runs/l26-26/session/runs/97c21760d66337b9f5905e6cc605cd7dbd700b12f3a75e4cc26048bf9b1a51ee/native.log (sha256 c752e0ce50c065a3...) sunsets L4608/L8941, dead L14106, receipt L15073; native claude/p2-wave3-mechanics 535a4da10 (exe built from 1959f6b5d), exe sha256 fe21fd5e99634438ca03fbc204bc86c45fbe58b4619e60825ba04f4960c6a03a, content output/p2-content-dense",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 26 -> aquatic "
                         "(experimental/pikmin2_aquatic_install)",
        },
    },
    {
        "source_id": 27,
        "enum_name": "Tadpole",
        "family": "aquatic",
        "evidence": {
            "run": "Bot-driven power-mode campaign runs j27 and l27 (owner ruling 2026-09-25: power mode admits; wave 3 mechanics, #964): red squad, campaign bind of the transcribed source Tadpole FSM (wait/move/amaze/escape/leap/dead, retail parms, life 200) on the Wogpole's own generator token; it hops away from the squad, takes damage, dies naturally, the dead corpse is carried and delivers Onion receipt onion:p2:27:3. Day-cycle run l27: a fresh Wogpole binds each stage, alive at two sunsets, killed and delivered in the third stage (day 4). Harmless in source (attack power 0): attacks_receivers is receiver-side only, no attack is claimed. The kill runs used a land slot (start-area slot rebind)",
            "log": "output/claude-orch/p2-w3-mech/runs/j27-27/session/runs/41692195c7e20f1886de67b09fae9d8f79ad53689af728ee6dc76972c29da45b/native.log (sha256 df33bd80e4390489...) L4836 bind, L6164 dead, L6959 receipt; day cycle output/claude-orch/p2-w3-mech/runs/l27-27/session/runs/e3d52f33017fe47f0041df84e7dc3cb18340ccb1adc874079bc018ced2d8ee99/native.log (sha256 670a965f0f64403e...) sunsets L5597/L10884, dead L17079, receipt L17894; native claude/p2-wave3-mechanics 535a4da10 (exe built from 1959f6b5d), exe sha256 fe21fd5e99634438ca03fbc204bc86c45fbe58b4619e60825ba04f4960c6a03a, content output/p2-content-dense",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 27 -> aquatic "
                         "(experimental/pikmin2_aquatic_install)",
        },
    },
    {
        "source_id": 84,
        "enum_name": "Hana",
        "family": "ground_inverts",
        "evidence": {
            "run": "Bot-driven power-mode day-cycle run k84 (owner ruling 2026-09-25: power mode admits; wave 3 mechanics, #964): red squad, campaign bind of the transcribed source Hana FSM (ChappyBase sleep/emerge/walk/attack/eat/flick/gohome/dead, retail parms, life 2500) on the Chrysanthemum's own generator token; buried Sleep gate at each bind (no atari, invulnerable), alive at two sunsets, then in the third stage (day 4) emerge, BITE frame 18 and EAT, gohome, flick when Pikmin are stuck to it (from Walk; a flick from GoHome was not exercised by any run and is covered by the unit test p2_hana_residual_policy_test), natural death, the dead corpse carried, Onion receipt onion:p2:84:3",
            "log": "output/claude-orch/p2-w3-mech/runs/k84-84/session/runs/81e0e34451f2eb2c5b8c056f29dcd38b56da99102814caf91ffb5733dcc304e1/native.log (sha256 bf2546c26f19d6cb...) sleep binds L3464/L8101/L12611, sunsets L4812/L9355, BITE L14170, flick L15295, dead L17304, receipt L18679; native claude/p2-wave3-mechanics 535a4da10 (exe built from 1959f6b5d), exe sha256 fe21fd5e99634438ca03fbc204bc86c45fbe58b4619e60825ba04f4960c6a03a, content output/p2-content-dense",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 84 -> ground_inverts "
                         "(experimental/pikmin2_ground_inverts_install)",
        },
    },
    {
        "source_id": 93,
        "enum_name": "BombOtakara",
        "family": "dweevil",
        "evidence": {
            "run": "Bot-driven power-mode campaign runs r93, j93 and k93 (owner ruling 2026-09-25: power mode admits; wave 3 mechanics, #964): campaign bind of the transcribed source Otakara Dweevil FSM carrying a Bomb (BombOtakara pursues its target, the stimulateBomb 1.5 s fuse detonates the Bomb through the shared blast primitive, damage also detonates it); once the Bomb is not alive it dies with it by the source rule (OtakaraBase.cpp:93-108, P2_BOMBOTAKARA_PAYLOAD_DEAD), then the dead corpse is carried and delivers Onion receipt onion:p2:93:3 on its own generator token. r93 (blue): the blast hit a Pikmin (pikmin_hits=1). Day-cycle run k93: a fresh Dweevil binds each stage, one alive at the day-3 sunset, killed and delivered in the third stage (day 4). Earlier runs c93/e93, which showed the Dweevil surviving the blast, are superseded. Run f93 on seed s3 (a Dweevil on a grub-cohort pack slot, earlier exe) proves the pack fix",
            "log": "output/claude-orch/p2-w3-mech/runs/r93-93/session/runs/e6772ecac2f7225efcc8ff56bc6bc63256e7c481f8c857ee850f7f7877ead920/native.log (sha256 339324a413d51f8b...) L5130 FUSE, L5132 BLAST pikmin_hits=1, L5134 PAYLOAD_DEAD, L6249 receipt; j93 output/claude-orch/p2-w3-mech/runs/j93-93/session/runs/030e0f752619d95e3c3ccc665cb422b8f24b5dac0a7507afc6aaac14859109c1/native.log (sha256 ae2a8144815b1575...) receipt L5692; day cycle output/claude-orch/p2-w3-mech/runs/k93-93/session/runs/4c95ae0ff87d2dd63f18732c2b8fd49a979cb0aea63fad6012b8a85fc1c3b0ab/native.log (sha256 cdacfda090a1bfd1...) sunsets L4472/L8616, dead L13040, receipt L14160; earlier exe 6421207b h93 sha256 1778de329be329be... L3730 BLAST pikmin_hits=1, i93 sha256 c66f6efb69434bb6... L10927 pikmin_hits=32; native claude/p2-wave3-mechanics 535a4da10 (exe built from 1959f6b5d), exe sha256 fe21fd5e99634438ca03fbc204bc86c45fbe58b4619e60825ba04f4960c6a03a, content output/p2-content-dense",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 93 -> dweevil "
                         "(p2-dweevil-actors.txt)",
        },
    },
    {
        "source_id": 66,
        "enum_name": "Houdai",
        "family": "long_legs",
        "evidence": {
            "run": "Owner ruling #1088 (2026-10-01): no carcass or Pikmin seed yield; earn the check on kill, with stable onion:p2 identity and legacy AP location name. Historical transport evidence below predates this ruling. Bot-driven power-mode campaign c2 (#1012; owner ruling 2026-09-25: power mode admits): own-brain bind (P2HoudaiFsm, disc parms) with the sampled clip rig, IK legs, retail collision tree, Stay->Land->Wait->Walk->Dead on its own generator 1945764764, natural kill, P2 corpse carried, Onion receipt onion:p2:66:3; no-multiplier run b2 (same exe): rises, walks, laser sight sweep, 87 shells",
            "log": "No-carcass #1088: output/codex-1088-death-66-2/native.log (sha256 bda13f508e336d0d1c33ac4807d0e3926ce1cfca9b91a78300e99fa946c4180c; native d703218cae578376338fd292aed8477949a661b4); power x30 combat, death clip/burst then host escape, no corpse, kill receipt onion:p2:66:1 new=1 on generator 4222852521. Historical: output/claude-orch/p2-66-own/runs/c2/session/runs/0a737916a5c704ec2cd5ea489d43d5dd3a0ecfd63b9030830219a0187af8d44b/native.log (sha256 9efc43f3e7e35dd2...) L1199 own bind, L1200 delivery bind, L1464 dead, L1575 receipt, L1576 AUTOPLAY_RESULT 1/1/1/1; b2 native.log sha256 ffa4415dd704a644...; native claude/p2-66-man-at-legs 0f84fcc37, exe sha256 7c2f13033f9eba48...; docs/PIKMIN2_HOUDAI_PORT.md",
            "installer": "experimental/pikmin2_family_install.py "
                         "IDENTITY_FAMILY 66 -> long_legs "
                         "(experimental/pikmin2_long_legs_install; rig via pikmin2_houdai_rig)",
        },
    },
)


# Admitted P2 species the current launcher and native campaign path can actually run:
# derived from P2_PLAYABLE_POOL so the table above is the single source of truth.
# Roster admission must equal this set (#888, tests/test_p2_pool_roster_sync.py).
PLAYABLE_P2_SPECIES = tuple(row["source_id"] for row in P2_PLAYABLE_POOL)

# Pool species whose seed is only winnable when the session carries the opt-in
# Purple campaign (Violet supply, randomizer/purple_campaign.py). This is a
# runtime constraint, not an owner whitelist: source id -> citation. Generation
# binds such a species only for ``p2_purple_campaign=True`` (CLI
# ``--p2-purple-campaign``), which records ``p2_purple_campaign`` in the
# manifest (no native capability: the native hello echoes the capability list, and
# the Purple banks are already an explicit run-time opt-in); ``randomizer run`` then
# refuses to launch that seed without ``--purple-bank``/``--purple-motion``.
# The mechanism is generic and currently EMPTY. 40 Giant Breadbug was listed here
# (#958) on the claim that only Purple presses hurt it; the owner's red-only kill
# (2026-09-30) and the source disproved that. P2's damage paths for OoPanModoki:
#   - latched attacks do nothing (PanModokiBase::Obj::damageCallBack,
#     panModoki.cpp:450-456, bitter-gated);
#   - non-Purple presses/hipdrops are refused (OoPanModoki::pressCallBack
#     panModoki.cpp:1738-1744; hipdropCallBack 521-524);
#   - bombs hurt it (EnemyBase::bombCallBack, enemyBase.cpp:2908-2912);
#   - an Onion suck of the pellet it grabbed, carried by ANY colour, does
#     suckDamage 1000 of 2000 health, every time (pelletState.cpp:541-549 ->
#     panModoki.cpp:1381-1392 -> panModokiState.cpp:453-481). It is not one-off.
P2_REQUIRES_PURPLE = {}


def generate(seed, mode="solo", slot="Player1", *, expanded=False, starting_area="forest", starting_color="red", all_areas=False, enemy_shuffle=False, collection_checks=False, starting_flarlic=None, randomize_color_stats=False, progressive_color_stats=False, permanent_checks=False, legacy_checks=False, per_spawn_enemies=False, group_spawn_enemies=False, miniboss_enemies=False, campaign_enemies=False, initial_stat_bounds=None, stat_upgrade_counts=None, random_start_areas=None, bomb_rock_weight=0, goal_mode="repairs", combined_captain=False, bomb_trap_weight=0, progg_trap_weight=0, prerelease_trap_weight=0, death_link=False, death_link_pikmin=10, p2_enemies=False, p2_placement=None, p2_species=None, p2_density=None, p2_proxy_tier=None, progressive_maturity=False, progressive_day_length=0, day_length_step=25, whistle_pluck_item=False, p2_purple_campaign=False, p2_checks=False, p2_second_captain=False):
    from .benefits import DAY_LENGTH_LIMIT
    if type(progressive_maturity) is not bool: raise ValueError("invalid progressive_maturity")
    if type(whistle_pluck_item) is not bool: raise ValueError("invalid whistle_pluck_item")
    if type(progressive_day_length) is not int or not 0 <= progressive_day_length <= DAY_LENGTH_LIMIT: raise ValueError(f"progressive_day_length must be 0..{DAY_LENGTH_LIMIT}")
    if type(day_length_step) is not int or not 10 <= day_length_step <= 100 or day_length_step % 5: raise ValueError("day_length_step must be 10..100 in steps of 5")
    if progressive_day_length:
        if legacy_checks: raise ValueError("progressive day length requires modern checks")
        collection_checks = True
    if type(bomb_rock_weight) is not int or not 0 <= bomb_rock_weight <= 10: raise ValueError("bomb_rock_weight must be 0..10")
    if type(bomb_trap_weight) is not int or not 0 <= bomb_trap_weight <= 10: raise ValueError("bomb_trap_weight must be 0..10")
    if type(progg_trap_weight) is not int or not 0 <= progg_trap_weight <= 10: raise ValueError("progg_trap_weight must be 0..10")
    if type(prerelease_trap_weight) is not int or not 0 <= prerelease_trap_weight <= 10: raise ValueError("prerelease_trap_weight must be 0..10")
    if type(death_link) is not bool: raise ValueError("invalid death_link")
    if type(death_link_pikmin) is not int or not 1 <= death_link_pikmin <= 100: raise ValueError("death_link_pikmin must be 1..100")
    if death_link:
        if legacy_checks: raise ValueError("death link requires modern checks")
        collection_checks = True
    if bomb_rock_weight or bomb_trap_weight or progg_trap_weight or prerelease_trap_weight:
        if legacy_checks: raise ValueError("bomb deliveries require modern checks")
        collection_checks = True
    from .stats import validate_roll_bounds, validate_upgrade_limits
    if initial_stat_bounds is not None: validate_roll_bounds(initial_stat_bounds)
    if stat_upgrade_counts is not None: validate_upgrade_limits(stat_upgrade_counts)
    area_names = ('impact', 'forest', 'navel', 'spring')
    if random_start_areas is not None:
        if not isinstance(random_start_areas, (list, tuple, set, frozenset)) or not random_start_areas or any(a not in area_names for a in random_start_areas):
            raise ValueError('random_start_areas must be a nonempty subset of impact, forest, navel, spring')
    if group_spawn_enemies or miniboss_enemies: per_spawn_enemies = True
    if per_spawn_enemies:
        if legacy_checks: raise ValueError('per-spawn enemies require modern checks')
        collection_checks = True
        enemy_shuffle = False
    if campaign_enemies:
        if legacy_checks: raise ValueError("campaign enemies require modern checks")
        per_spawn_enemies = group_spawn_enemies = enemy_shuffle = False
        collection_checks = miniboss_enemies = True
    if type(combined_captain) is not bool: raise ValueError("invalid combined_captain")
    if combined_captain: collection_checks = True
    if type(p2_enemies) is not bool: raise ValueError("invalid p2_enemies")
    if type(p2_checks) is not bool or (p2_checks and not p2_enemies): raise ValueError("p2_checks requires P2 enemies")
    if p2_checks: collection_checks = True
    if p2_proxy_tier is not None and p2_proxy_tier not in ("proven", "declared"):
        raise ValueError("p2_proxy_tier must be 'proven' or 'declared'")
    if type(p2_second_captain) is not bool: raise ValueError("invalid p2_second_captain")
    if p2_second_captain and not p2_enemies: raise ValueError("p2_second_captain requires p2_enemies")
    if type(p2_purple_campaign) is not bool: raise ValueError("invalid p2_purple_campaign")
    if p2_purple_campaign and not p2_enemies: raise ValueError("p2_purple_campaign requires p2_enemies")
    p2_species_explicit = p2_species is not None and p2_species not in ("playable", "full")
    if p2_species is not None and not p2_enemies: raise ValueError("p2_species requires p2_enemies")
    if p2_density is not None and not p2_enemies: raise ValueError("p2_density requires p2_enemies")
    if p2_proxy_tier is not None and not p2_enemies: raise ValueError("p2_proxy_tier requires p2_enemies")
    if p2_species == "playable": p2_species = PLAYABLE_P2_SPECIES
    if p2_species == "full":
        if p2_proxy_tier is None:
            raise ValueError("p2_species 'full' requires p2_proxy_tier")
        from .p2_proxy import tier_ids as _tier_ids
        p2_species = tuple(PLAYABLE_P2_SPECIES) + tuple(_tier_ids(p2_proxy_tier))
    if p2_species is not None and (not isinstance(p2_species, (list, tuple, set, frozenset)) or not p2_species
                                   or any(type(i) is not int for i in p2_species)):
        raise ValueError("p2_species must be 'playable', 'full' or a nonempty list of admitted source ids")
    if p2_species is not None and p2_proxy_tier is not None:
        from .p2_proxy import tier_ids as _tier_ids
        allowed_proxy = set(_tier_ids(p2_proxy_tier))
        declared_proxy = set(_tier_ids("declared"))
        for source_id in p2_species:
            if source_id in declared_proxy and source_id not in allowed_proxy:
                raise ValueError(
                    f"p2_species proxy id {source_id} is not in the {p2_proxy_tier!r} tier")
    if p2_proxy_tier is not None and p2_species is not None:
        from .p2_proxy import tier_ids as _tier_ids
        declared_proxy = set(_tier_ids("declared"))
        if any(source_id in declared_proxy for source_id in p2_species):
            if p2_density is not None:
                from experimental.pikmin2_seed_bridge import DENSITY_SAMPLED
                if p2_density != DENSITY_SAMPLED:
                    raise ValueError(
                        f"p2_proxy_tier forces the {DENSITY_SAMPLED} policy, not {p2_density!r}")
    if p2_enemies and not p2_purple_campaign:
        # Purple-only species need the opt-in Purple campaign (P2_REQUIRES_PURPLE).
        # A named list that asks for one is an error; the broader selections
        # ("playable", "full", default) simply leave it out.
        asked = sorted(set(P2_REQUIRES_PURPLE) & set(p2_species or ()))
        if asked and p2_species_explicit:
            raise ValueError(f"p2_species {asked} need the opt-in Purple campaign (--p2-purple-campaign): "
                             + "; ".join(P2_REQUIRES_PURPLE[i] for i in asked))
        if asked:
            p2_species = tuple(i for i in p2_species if i not in P2_REQUIRES_PURPLE)
        elif p2_species is None:
            from experimental.pikmin2_enemy_roster import load_and_validate as _roster
            from experimental.pikmin2_seed_bridge import admitted_ids as _admitted
            _ids = [i for i in _admitted(_roster()) if i not in P2_REQUIRES_PURPLE]
            if len(_ids) != len(_admitted(_roster())): p2_species = tuple(_ids)
    if p2_placement is not None and type(p2_placement) is not dict:
        raise ValueError("p2_placement must be a placement document mapping")
    if p2_enemies:
        if legacy_checks: raise ValueError("P2 enemies require modern checks")
        combined_enemies = bool(enemy_shuffle or per_spawn_enemies or campaign_enemies)
        # New combinations require one authoritative final check/source catalog.
        if combined_enemies:
            p2_checks = True
        collection_checks = True
    if goal_mode not in ("repairs", "emperor_bulblax"): raise ValueError("invalid goal_mode")
    if goal_mode == "emperor_bulblax": collection_checks = True
    if progressive_color_stats: permanent_checks = True  # 36 upgrades need the larger check pool.
    collection_checks = collection_checks or progressive_color_stats or permanent_checks
    result = dict(schema=1, game=GAME, seed=str(seed), slot=slot, mode=mode,
                  profile="foh-day2", catalog="vanilla-sites-v1", rng="sha256-counter-v1",
                  placement="identity-v1", assignments=dict(PART_IDS),
                  locations=dict(LOCATION_IDS), goal=REPAIR_COUNT, day_policy="repeat-day29-v1",
                  capabilities=list(CAPABILITIES))
    if starting_flarlic is not None:
        if type(starting_flarlic) is not int or not 1 <= starting_flarlic <= 10:
            raise ValueError("starting_flarlic must be an integer from 1 to 10")
        expanded = True
    if expanded:
        result.update(schema=2, catalog="gameplay-checks-v2", locations=dict(ALL_LOCATION_IDS),
                      capabilities=CAPABILITIES + EXPANDED_CAPABILITIES)
    if starting_area != "forest":
        if starting_area not in ("random", "navel", "impact", "spring", "trial"):
            raise ValueError("unsupported starting area")
        selected = ("foh-day2", "navel-day2")[SeedRandom(str(seed) + "/start/" + slot).below(2)] if starting_area == "random" else "navel-day2"
        result.update(schema=3, profile=selected, catalog="gameplay-checks-v3", locations=dict(ALL_LOCATION_IDS),
                      capabilities=["identity-placement-v1", "random-start-v1", "repair-goal-v1", "repeat-day29-v1"] + EXPANDED_CAPABILITIES)
    if starting_color != 'red':
        if starting_color not in ('yellow', 'blue', 'random'):
            raise ValueError('unsupported starting color')
        color = ('red', 'yellow', 'blue')[SeedRandom(str(seed) + '/color/' + slot).below(3)] if starting_color == 'random' else starting_color
        result.update(schema=4, starting_color=color, catalog='gameplay-checks-v4', locations=dict(ALL_LOCATION_IDS),
                      capabilities=['identity-placement-v1', 'random-start-v1', 'repair-goal-v1', 'repeat-day29-v1'] + EXPANDED_CAPABILITIES + ['starting-color-v1'])
    if all_areas or enemy_shuffle or collection_checks or randomize_color_stats or starting_area in ('random', 'impact', 'spring', 'trial'):
        eligible = tuple(p for p in START_AREAS if p != 'trial-day2' and (random_start_areas is None or ('forest' if p == 'foh-day2' else p.removesuffix('-day2')) in random_start_areas))
        profile = eligible[SeedRandom(str(seed) + '/all-areas-v2/' + slot).below(len(eligible))] if starting_area == 'random' else ('foh-day2' if starting_area == 'forest' else starting_area + '-day2')
        result.update(schema=5, profile=profile, starting_color=result.get('starting_color', 'red'),
                      catalog='gameplay-checks-v5', assignments=dict(ALL_PART_IDS), locations=dict(ALL_AREA_LOCATION_IDS),
                      capabilities=['identity-placement-v1', 'random-start-v1', 'repair-goal-v1', 'repeat-day29-v1'] + EXPANDED_CAPABILITIES + ['starting-color-v1', 'all-areas-v1'])
    if enemy_shuffle:
        result.update(schema=6, catalog='gameplay-checks-v6', enemy_shuffle='families-v1',
                      enemy_mask=1 + SeedRandom(str(seed) + '/enemies/' + slot).below(7),
                      capabilities=result['capabilities'] + ['enemy-families-v1'])
    if collection_checks:
        result.update(schema=7, catalog='gameplay-checks-v7', locations=dict(COLLECTION_LOCATION_IDS),
                      enemy_shuffle=result.get('enemy_shuffle', 'none'), enemy_mask=result.get('enemy_mask', 0))
        result['capabilities'] = [c for c in result['capabilities'] if c not in ('population-v1', 'bestiary-v1', 'enemy-families-v1')] + ['enemy-families-v1', 'total-population-v1', 'corpse-delivery-v1']
    if permanent_checks:
        from .catalog import PERMANENT_LOCATION_IDS
        result.update(schema=8, catalog='gameplay-checks-v8', locations=dict(PERMANENT_LOCATION_IDS))
        result['capabilities'] += ['permanent-checks-v1', 'check-set-v1']
    if collection_checks and not legacy_checks:
        result.update(schema=9, catalog='gameplay-checks-v9', permanent_checks=bool(permanent_checks), no_exploration=True, color_population=True, compact_population=True, no_sticks=True,
                      locations={n: MODERN_LOCATION_IDS[n] for n in modern_names(permanent_checks, True, True, True, True)})
        result['capabilities'] = [c for c in result['capabilities'] if c not in ('permanent-checks-v1', 'check-set-v1')]
        result['capabilities'] += (['permanent-checks-v1'] if permanent_checks else []) + ['check-set-v1', 'bestiary-v2', 'no-exploration-v1', 'color-population-v1', 'compact-population-v1']
    if starting_flarlic is not None:
        result["starting_flarlic"] = starting_flarlic
        result["capabilities"].append("starting-flarlic-v1")
    if randomize_color_stats:
        from .stats import roll_profiles
        result["color_stats"] = roll_profiles(SeedRandom(str(seed) + "/color-stats-v3/" + slot), initial_stat_bounds)
        result["capabilities"].append("color-stats-v3")
    if progressive_color_stats:
        result['progressive_color_stats'] = True
        result['capabilities'].append('progressive-color-stats-v2')
        if stat_upgrade_counts is not None:
            result['stat_upgrade_counts'] = dict(stat_upgrade_counts)
    if result['schema'] == 9:
        from .enemies import resolve_layout
        result['enemy_layout'] = resolve_layout(result['enemy_mask'])
        result['benefit_items'] = True
        result['repair_pool_count'] = 30
        result['capabilities'].append('benefit-items-v1')
        if combined_captain:
            result['combined_captain'] = True
            result['capabilities'].append('combined-captain-v1')
        if bomb_rock_weight:
            result['bomb_rock_weight'] = bomb_rock_weight
            result['capabilities'].append('bomb-delivery-v1')
        if bomb_trap_weight:
            result['bomb_trap_weight'] = bomb_trap_weight
            result['capabilities'].append('bomb-ambush-v1')
        if progg_trap_weight:
            result['progg_trap_weight'] = progg_trap_weight
            result['capabilities'].append('progg-ambush-v1')
        if prerelease_trap_weight:
            result['prerelease_trap_weight'] = prerelease_trap_weight
            result['capabilities'].append('prerelease-trap-v1')
        if progressive_maturity:
            result['progressive_maturity'] = True
            result['capabilities'].append('progressive-maturity-v1')
        if progressive_day_length:
            result['progressive_day_length'] = progressive_day_length
            result['day_length_step'] = day_length_step
            result['capabilities'].append('progressive-day-length-v1')
        if whistle_pluck_item:
            result['whistle_pluck_item'] = True
            result['capabilities'].append('whistle-pluck-item-v1')
        if per_spawn_enemies:
            from .enemy_slots import resolve_spawn_layout, spawn_sources
            result['spawn_layout'] = resolve_spawn_layout(result['seed'], slot, miniboss_enemies)
            result['enemy_layout'] = spawn_sources(result['spawn_layout'])
            result['enemy_shuffle'] = 'adult-slots-v1'
            result['capabilities'].append('enemy-slots-v1')
    if group_spawn_enemies:
        from .enemy_slots import resolve_group_layout, spawn_sources
        result["group_layout"] = resolve_group_layout(result["seed"], slot)
        result["enemy_layout"] = spawn_sources(result["spawn_layout"], result["group_layout"])
        result["capabilities"].append("enemy-groups-v1")
    if campaign_enemies:
        from .campaign_enemies import resolve_campaign, campaign_sources
        result['campaign_layout'] = resolve_campaign(result['seed'], slot)
        result['enemy_layout'] = campaign_sources(result['campaign_layout'])
        result['enemy_shuffle'] = 'campaign-v1'
        result['capabilities'].append('enemy-campaign-v1')
    if miniboss_enemies:
        result['miniboss_enemies'] = True
        result['capabilities'].append('miniboss-slots-v1')
    if goal_mode == "emperor_bulblax":
        result["goal_mode"] = goal_mode
        result["capabilities"].append("emperor-goal-v1")
    if death_link:
        # One unit sets both the outgoing threshold and incoming casualties.
        result["death_link"] = True
        result["death_link_pikmin"] = death_link_pikmin
        result["capabilities"].append("death-link-v1")
    if p2_enemies:
        # Opt-in experimental bridge: the admitted cohort comes from lane 02, the
        # ordered binding targets from lane 04. Fail closed while nothing is
        # admitted. Kept behind a lazy import so ordinary seeds never load the
        # experimental roster.
        from experimental.pikmin2_enemy_roster import load_and_validate
        # Product path: legal targets come only from the lane 04 placement contract.
        # Explicit-cohort binding stays a diagnostic bridge API, not a seed option.
        from experimental.pikmin2_seed_bridge import resolve_placement_layout, validate_density
        # Fail closed on an unknown density token before any layout work; the
        # default None stays the unchanged legacy all-target fill.
        validate_density(p2_density)
        if result['schema'] != 9:
            raise ValueError("P2 enemies require the modern schema-9 catalog")
        if p2_placement is None:
            # Admitted enemies are eligible for placement behind the p2_enemies
            # option; the committed accepted-placement document supplies the legal
            # targets and resolve_placement_layout still fails closed.
            p2_placement = _default_admitted_placement()
        proxy_rows = None
        proxy_document = None
        if p2_proxy_tier is not None:
            from .p2_proxy import load_rows as _load_proxy_rows, tier_ids as _tier_ids
            tier_set = set(_tier_ids(p2_proxy_tier))
            wanted_proxy = set()
            if p2_species is not None:
                declared_proxy = set(_tier_ids("declared"))
                wanted_proxy = {source_id for source_id in set(p2_species)
                                if source_id in declared_proxy}
            rows_by_id = {row["source_id"]: row for row in _load_proxy_rows()}
            proxy_rows = [rows_by_id[source_id] for source_id in sorted(wanted_proxy)
                          if source_id in tier_set and source_id in rows_by_id]
            if proxy_rows:
                proxy_document = _default_proxy_placement()
        result['p2_layout'] = resolve_placement_layout(result['seed'], slot, p2_placement, load_and_validate(),
                                                       species=None if p2_species is None else sorted(set(p2_species)),
                                                       density=p2_density,
                                                       proxy_rows=proxy_rows,
                                                       proxy_document=proxy_document)
        combined_enemies = bool(result.get('enemy_mask') or 'spawn_layout' in result or 'campaign_layout' in result)
        if combined_enemies:
            result['enemy_composition'] = 'p1-then-p2-v1'
            result['capabilities'].append('combined-enemies-v1')
        result['capabilities'].append('p2-enemy-bridge-v1')
        if p2_purple_campaign:
            result['p2_purple_campaign'] = True
        if p2_proxy_tier is not None:
            result['p2_proxy_tier'] = p2_proxy_tier
            result['capabilities'].append('p2-proxy-tier-v1')
    if p2_checks:
        from .enemy_catalog import resolve, location_ids, CAPABILITY
        result['enemy_catalog'] = resolve(result, p2_placement, load_and_validate(),
                                         proxy_ids=[r['source_id'] for r in proxy_rows or []])
        result['locations'] = location_ids(result)
        result['capabilities'].append(CAPABILITY)
    if p2_second_captain:
        result['p2_second_captain'] = True
        result['capabilities'].append('p2-second-captain-v1')
    validate(result)
    return result


def validate(m):
    expected = {"schema", "game", "seed", "slot", "mode", "profile", "catalog", "rng", "placement",
                "assignments", "locations", "goal", "day_policy", "capabilities"}
    if type(m) is dict and m.get('schema', 0) in (4, 5, 6, 7, 8, 9):
        expected.add('starting_color')
    if type(m) is dict and m.get('schema') in (6, 7, 8, 9):
        expected.update(('enemy_shuffle', 'enemy_mask'))
    if type(m) is dict and m.get('schema') == 9:
        expected.add('permanent_checks')
        if 'compact_population' in m:
            expected.add('compact_population')
            if m['compact_population'] is not True or not m.get('color_population'): raise ValueError('invalid compact_population')
        if 'benefit_items' in m:
            expected.add('benefit_items')
            if m['benefit_items'] is not True or not m.get('color_population'): raise ValueError('invalid benefit_items')
        if 'color_population' in m:
            expected.add('color_population')
            if m['color_population'] is not True or not m.get('no_exploration'): raise ValueError('invalid color_population')
        if 'no_exploration' in m:
            expected.add('no_exploration')
            if m['no_exploration'] is not True: raise ValueError('invalid no_exploration')
        if type(m.get('permanent_checks')) is not bool: raise ValueError('invalid permanent_checks')
    if type(m) is dict and 'miniboss_enemies' in m:
        expected.add('miniboss_enemies')
        if m['miniboss_enemies'] is not True or not ('spawn_layout' in m or 'campaign_layout' in m): raise ValueError('invalid miniboss_enemies')
    if type(m) is dict and 'campaign_layout' in m:
        from .campaign_enemies import resolve_campaign
        expected.add('campaign_layout')
        if m.get('schema') != 9 or m.get('enemy_mask') != 0 or not m.get('miniboss_enemies') or 'spawn_layout' in m or 'group_layout' in m:
            raise ValueError('invalid campaign enemy mode')
        if canonical(m['campaign_layout']) != canonical(resolve_campaign(m.get('seed',''),m.get('slot',''))):
            raise ValueError('invalid campaign enemy layout')
    if type(m) is dict and 'spawn_layout' in m:
        expected.add('spawn_layout')
        from .enemy_slots import resolve_spawn_layout
        if m.get('schema') != 9 or m.get('enemy_mask') != 0 or 'enemy_layout' not in m:
            raise ValueError('per-spawn layout requires modern zero-mask seed')
        if canonical(m['spawn_layout']) != canonical(resolve_spawn_layout(m.get('seed', ''), m.get('slot', ''), m.get('miniboss_enemies',False))):
            raise ValueError('invalid per-spawn layout or source catalog')
    if type(m) is dict and 'group_layout' in m:
        expected.add('group_layout')
        from .enemy_slots import resolve_group_layout
        if 'spawn_layout' not in m or canonical(m['group_layout']) != canonical(resolve_group_layout(m.get('seed',''),m.get('slot',''))):
            raise ValueError('invalid grouped enemy layout')
    if type(m) is dict and 'enemy_layout' in m:
        expected.add('enemy_layout')
        from .enemies import resolve_layout, sources_for
        from .catalog import BESTIARY_TARGETS
        if m.get('schema') != 9 or type(m.get('enemy_mask')) is not int or not 0 <= m['enemy_mask'] <= 7:
            raise ValueError('enemy layout requires schema 9 and a valid seed mask')
        from .enemy_slots import spawn_sources
        from .campaign_enemies import campaign_sources
        expected_sources = campaign_sources(m['campaign_layout']) if 'campaign_layout' in m else spawn_sources(m['spawn_layout'], m.get('group_layout')) if 'spawn_layout' in m else resolve_layout(m['enemy_mask'])
        if canonical(m['enemy_layout']) != canonical(expected_sources):
            raise ValueError('enemy layout disagrees with seeded permutation/source catalog')
        if any(not sources_for(m['enemy_layout'], species) for species, _ in BESTIARY_TARGETS.values()):
            raise ValueError('bestiary species has no source in enemy layout')
    if type(m) is dict and "starting_flarlic" in m:
        expected.add("starting_flarlic")
        if type(m["starting_flarlic"]) is not int or not 1 <= m["starting_flarlic"] <= 10 or m.get("schema", 0) < 2:
            raise ValueError("invalid starting_flarlic")
    if type(m) is dict and "color_stats" in m:
        from .stats import validate_profiles
        expected.add("color_stats")
        validate_profiles(m["color_stats"], wide="color-stats-v2" in m.get("capabilities", []), balanced="color-stats-v3" in m.get("capabilities", []))
        if type(m.get("schema")) is not int or m["schema"] < 5:
            raise ValueError("color stats require the all-area catalog")
    if type(m) is dict and 'progressive_color_stats' in m:
        expected.add('progressive_color_stats')
        if m['progressive_color_stats'] is not True or m.get('schema') not in (7, 8, 9):
            raise ValueError('invalid progressive color stats mode')
    if type(m) is dict and 'bomb_rock_weight' in m:
        expected.add('bomb_rock_weight')
        if type(m['bomb_rock_weight']) is not int or not 1 <= m['bomb_rock_weight'] <= 10 or not m.get('benefit_items'):
            raise ValueError('invalid bomb delivery weight')
    if type(m) is dict and 'bomb_trap_weight' in m:
        expected.add('bomb_trap_weight')
        if type(m['bomb_trap_weight']) is not int or not 1 <= m['bomb_trap_weight'] <= 10 or not m.get('benefit_items'):
            raise ValueError('invalid bomb_trap_weight')
    if type(m) is dict and 'progg_trap_weight' in m:
        expected.add('progg_trap_weight')
        if type(m['progg_trap_weight']) is not int or not 1 <= m['progg_trap_weight'] <= 10 or not m.get('benefit_items'):
            raise ValueError('invalid progg_trap_weight')
    if type(m) is dict and 'prerelease_trap_weight' in m:
        expected.add('prerelease_trap_weight')
        if type(m['prerelease_trap_weight']) is not int or not 1 <= m['prerelease_trap_weight'] <= 10 or not m.get('benefit_items'):
            raise ValueError('invalid prerelease_trap_weight')
    if type(m) is dict and 'progressive_maturity' in m:
        expected.add('progressive_maturity')
        if m['progressive_maturity'] is not True or not m.get('benefit_items'): raise ValueError('invalid progressive_maturity')
    if type(m) is dict and 'whistle_pluck_item' in m:
        expected.add('whistle_pluck_item')
        if m['whistle_pluck_item'] is not True or not m.get('benefit_items'): raise ValueError('invalid whistle_pluck_item')
    if type(m) is dict and ('progressive_day_length' in m or 'day_length_step' in m):
        from .benefits import DAY_LENGTH_LIMIT
        expected.update(('progressive_day_length', 'day_length_step'))
        count, step = m.get('progressive_day_length'), m.get('day_length_step')
        if type(count) is not int or not 1 <= count <= DAY_LENGTH_LIMIT or type(step) is not int or not 10 <= step <= 100 or step % 5 or not m.get('benefit_items'):
            raise ValueError('invalid progressive day length')
    if type(m) is dict and 'combined_captain' in m:
        expected.add('combined_captain')
        if m['combined_captain'] is not True or not m.get('benefit_items'): raise ValueError('invalid combined_captain')
    if type(m) is dict and 'goal_mode' in m:
        expected.add('goal_mode')
        if m.get('schema') != 9 or m['goal_mode'] != 'emperor_bulblax': raise ValueError('invalid goal_mode')
    if type(m) is dict and ('death_link' in m or 'death_link_pikmin' in m):
        expected.update(('death_link', 'death_link_pikmin'))
        if m.get('schema') != 9 or m.get('death_link') is not True or type(m.get('death_link_pikmin')) is not int \
                or not 1 <= m['death_link_pikmin'] <= 100:
            raise ValueError('invalid death_link')
    if type(m) is dict and 'no_sticks' in m:
        expected.add('no_sticks')
        if m.get('schema') != 9 or m['no_sticks'] is not True:
            raise ValueError('invalid no_sticks')
    if type(m) is dict and 'repair_pool_count' in m:
        expected.add('repair_pool_count')
        if type(m['repair_pool_count']) is not int or m['repair_pool_count'] != 30 or not m.get('benefit_items'):
            raise ValueError('invalid repair pool count')
    if type(m) is dict and 'stat_upgrade_counts' in m:
        from .stats import validate_upgrade_limits
        expected.add('stat_upgrade_counts')
        validate_upgrade_limits(m['stat_upgrade_counts'])
        if not m.get('progressive_color_stats') or 'progressive-color-stats-v2' not in m.get('capabilities', []):
            raise ValueError('custom upgrade counts require progressive stats v2')
    if type(m) is dict and 'p2_proxy_tier' in m:
        expected.add('p2_proxy_tier')
        if m.get('schema') != 9 or m['p2_proxy_tier'] not in ('proven', 'declared'):
            raise ValueError('invalid p2_proxy_tier')
        if 'p2_layout' not in m:
            raise ValueError('p2_proxy_tier requires a p2_layout')
    if type(m) is dict and 'p2_second_captain' in m:
        expected.add('p2_second_captain')
        if m['p2_second_captain'] is not True or 'p2_layout' not in m:
            raise ValueError('invalid p2_second_captain')
    if type(m) is dict and 'p2_purple_campaign' in m:
        expected.add('p2_purple_campaign')
        if m['p2_purple_campaign'] is not True or 'p2_layout' not in m:
            raise ValueError('invalid p2_purple_campaign')
    if type(m) is dict and 'enemy_composition' in m:
        expected.add('enemy_composition')
        if (m['enemy_composition'] != 'p1-then-p2-v1' or m.get('schema') != 9
                or 'p2_layout' not in m or 'enemy_catalog' not in m
                or not (m.get('enemy_shuffle') == 'families-v1'
                        or 'spawn_layout' in m or 'campaign_layout' in m)):
            raise ValueError('invalid combined enemy composition')
    if type(m) is dict and 'p2_layout' in m:
        expected.add('p2_layout')
        from experimental.pikmin2_enemy_roster import load_and_validate
        from experimental.pikmin2_seed_bridge import (SeedBridgeError, admitted_ids,
                                                      validate_layout as validate_p2_layout)
        combined = m.get('enemy_composition') == 'p1-then-p2-v1'
        if m.get('schema') != 9:
            raise ValueError('p2_layout requires schema 9')
        if not combined and (m.get('enemy_mask') != 0
                or any(key in m for key in ('spawn_layout', 'group_layout', 'campaign_layout'))):
            raise ValueError('mixed enemy layouts require versioned enemy composition')
        if 'p2-enemy-bridge-v1' not in m.get('capabilities', []):
            raise ValueError('p2_layout requires the p2-enemy-bridge-v1 capability')
        try:
            roster = load_and_validate()
            # Product path: a loaded seed must still satisfy the *current* admission set.
            # With an opt-in proxy tier the admitted set is extended by that tier's ids.
            admitted = admitted_ids(roster)
            if m.get('p2_proxy_tier') is not None:
                from .p2_proxy import tier_ids as _tier_ids
                admitted = sorted(set(admitted) | set(_tier_ids(m['p2_proxy_tier'])))
            # Roster wave (#871, rfix): the roster admits every pool species,
            # so an admitted identity validates through the roster admission
            # set above, never through the installer table. The union below
            # is kept only for evidence staging of installed-but-unadmitted
            # identities (lane runs whose campaign evidence is still in
            # flight: 1,26,27,45,58,66,84,93,97, e.g. 26/27/84/93/66/97).
            # It is scoped to installed AND non-pool AND unadmitted
            # (_identity_ids - admitted - pool), so a pool species that
            # loses roster admission is excluded and fails closed here
            # instead of being masked by its installer row (the old
            # A | (I - A) == A | I scoping was a no-op). A validate() pass
            # is not admission: P2_PLAYABLE_POOL remains the single source
            # of truth.
            try:
                from experimental.pikmin2_family_install import IDENTITY_FAMILY as _IDENTITY
                _identity_ids = {k for k, v in _IDENTITY.items()
                                 if type(k) is int and v != 'proxy'}
                _pool_ids = {row["source_id"] for row in P2_PLAYABLE_POOL}
                _staging_only = _identity_ids - set(admitted) - _pool_ids
                admitted = sorted(set(admitted) | _staging_only)
            except Exception:
                pass
            validate_p2_layout(m['p2_layout'], roster, admitted=admitted)
            needy = sorted({b.get('source_id') for b in m['p2_layout'].get('bindings', [])} & set(P2_REQUIRES_PURPLE))
            if needy and not m.get('p2_purple_campaign'):
                raise SeedBridgeError(f"source ids {needy} need the opt-in Purple campaign "
                                      "(generate with --p2-purple-campaign): "
                                      + "; ".join(P2_REQUIRES_PURPLE[i] for i in needy))
        except SeedBridgeError as exc:
            raise ValueError(f'invalid p2_layout: {exc}')
    if type(m) is dict and 'enemy_catalog' in m:
        expected.add('enemy_catalog')
        if m.get('schema') != 9 or 'p2_layout' not in m:
            raise ValueError('resolved enemy catalog requires P2 schema 9')
        from .enemy_catalog import validate as validate_catalog, resolve
        validate_catalog(m['enemy_catalog'], m)
        proxy_ids = []
        if m.get('p2_proxy_tier'):
            from .p2_proxy import tier_ids
            proxy_ids = tier_ids(m['p2_proxy_tier'])
        if m['enemy_catalog'] != resolve(m, _default_admitted_placement(), roster, proxy_ids=proxy_ids):
            raise ValueError('resolved enemy catalog differs from actual seed bindings')
    if type(m) is not dict or set(m) != expected:
        raise ValueError("manifest fields do not match schema 1")
    if type(m["schema"]) is not int or m["schema"] not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        raise ValueError("unsupported manifest schema")
    expanded = m["schema"] >= 2
    fixed = dict(schema=m["schema"], game=GAME, profile="foh-day2", catalog="vanilla-sites-v1",
                 rng="sha256-counter-v1", placement="identity-v1", goal=REPAIR_COUNT,
                 day_policy="repeat-day29-v1", capabilities=CAPABILITIES)
    if expanded:
        fixed.update(catalog="gameplay-checks-v2", capabilities=CAPABILITIES + EXPANDED_CAPABILITIES)
    if m['schema'] >= 3:
        if m['profile'] not in (START_AREAS if m['schema'] >= 5 else ('foh-day2', 'navel-day2')):
            raise ValueError('unsupported start profile')
        fixed.update(profile=m['profile'], catalog='gameplay-checks-v3',
                     capabilities=['identity-placement-v1', 'random-start-v1', 'repair-goal-v1', 'repeat-day29-v1'] + EXPANDED_CAPABILITIES)
    if m['schema'] >= 4:
        if m['starting_color'] not in ('red', 'yellow', 'blue'):
            raise ValueError('unsupported starting color')
        fixed.update(catalog='gameplay-checks-v4', capabilities=fixed['capabilities'] + ['starting-color-v1'])
    if m['schema'] >= 5:
        fixed.update(catalog='gameplay-checks-v5', capabilities=fixed['capabilities'] + ['all-areas-v1'])
    if m['schema'] >= 6:
        if type(m['enemy_mask']) is not int or not (0 if m['schema'] >= 7 else 1) <= m['enemy_mask'] <= 7:
            raise ValueError('unsupported enemy permutation')
        fixed.update(catalog='gameplay-checks-v6', enemy_shuffle='families-v1', capabilities=fixed['capabilities'] + ['enemy-families-v1'])
    if m['schema'] >= 7:
        fixed.update(catalog='gameplay-checks-v7', enemy_shuffle='campaign-v1' if 'campaign_layout' in m else 'adult-slots-v1' if 'spawn_layout' in m else 'families-v1' if m['enemy_mask'] else 'none',
                     capabilities=[c for c in fixed['capabilities'] if c not in ('population-v1', 'bestiary-v1')] + ['total-population-v1', 'corpse-delivery-v1'])
    if m['schema'] == 8:
        fixed.update(catalog='gameplay-checks-v8', capabilities=fixed['capabilities'] + ['permanent-checks-v1', 'check-set-v1'])
    if m['schema'] == 9:
        fixed.update(catalog='gameplay-checks-v9', capabilities=fixed['capabilities']
            + (['permanent-checks-v1'] if m['permanent_checks'] else []) + ['check-set-v1', 'bestiary-v2', 'no-exploration-v1' if m.get('no_exploration') else 'landing-only-v1'])
    if m.get('color_population'):
        fixed['capabilities'] += ['color-population-v1']
    if m.get('compact_population'):
        fixed['capabilities'] += ['compact-population-v1']
    if "starting_flarlic" in m:
        fixed["capabilities"] = fixed["capabilities"] + ["starting-flarlic-v1"]
    if "color_stats" in m:
        fixed["capabilities"] = fixed["capabilities"] + ["color-stats-v3" if "color-stats-v3" in m["capabilities"] else "color-stats-v2" if "color-stats-v2" in m["capabilities"] else "color-stats-v1"]
    if m.get('progressive_color_stats'):
        fixed['capabilities'] += ['progressive-color-stats-v2' if 'progressive-color-stats-v2' in m['capabilities'] else 'progressive-color-stats-v1']
    if m.get('benefit_items'):
        fixed['capabilities'] += ['benefit-items-v1']
        if m.get('combined_captain'): fixed['capabilities'] += ['combined-captain-v1']
        if m.get('bomb_rock_weight'): fixed['capabilities'] += ['bomb-delivery-v1']
        if m.get('bomb_trap_weight'): fixed['capabilities'] += ['bomb-ambush-v1']
        if m.get('progg_trap_weight'): fixed['capabilities'] += ['progg-ambush-v1']
        if m.get('prerelease_trap_weight'): fixed['capabilities'] += ['prerelease-trap-v1']
        if m.get('progressive_maturity'): fixed['capabilities'] += ['progressive-maturity-v1']
        if m.get('progressive_day_length'): fixed['capabilities'] += ['progressive-day-length-v1']
        if m.get('whistle_pluck_item'): fixed['capabilities'] += ['whistle-pluck-item-v1']
    if 'spawn_layout' in m:
        fixed['capabilities'] += ['enemy-slots-v1']
    if 'group_layout' in m:
        fixed['capabilities'] += ['enemy-groups-v1']
    if 'campaign_layout' in m:
        fixed['capabilities'] += ['enemy-campaign-v1']
    if m.get('miniboss_enemies'):
        fixed['capabilities'] += ['miniboss-slots-v1']
    if m.get("goal_mode") == "emperor_bulblax": fixed["capabilities"].append("emperor-goal-v1")
    if m.get("death_link"): fixed["capabilities"].append("death-link-v1")
    if m.get('enemy_composition'): fixed['capabilities'].append('combined-enemies-v1')
    if m.get('p2_layout'): fixed['capabilities'].append('p2-enemy-bridge-v1')
    if m.get('p2_proxy_tier'): fixed['capabilities'].append('p2-proxy-tier-v1')
    if m.get('enemy_catalog'): fixed['capabilities'].append('resolved-enemy-checks-v1')
    if m.get('p2_second_captain'): fixed['capabilities'].append('p2-second-captain-v1')
    for key, value in fixed.items():
        if type(m[key]) is not type(value) or m[key] != value:
            raise ValueError(f"unsupported {key}: {m[key]!r}")
    for key in ("seed", "slot"):
        if type(m[key]) is not str or not 1 <= len(m[key]) <= 128 or any(ord(c) < 32 for c in m[key]):
            raise ValueError(f"invalid {key}")
    if m["mode"] not in ("solo", "ap"):
        raise ValueError("mode must be solo or ap")
    from .enemy_catalog import location_ids as resolved_location_ids
    expected_locations = resolved_location_ids(m) if "enemy_catalog" in m else {n: MODERN_LOCATION_IDS[n] for n in modern_names(m["permanent_checks"], m.get("no_exploration", False), m.get("color_population", False), m.get("compact_population", False), m.get("no_sticks", False))} if m["schema"] == 9 else PERMANENT_LOCATION_IDS if m['schema'] >= 8 else COLLECTION_LOCATION_IDS if m['schema'] >= 7 else ALL_AREA_LOCATION_IDS if m['schema'] >= 5 else ALL_LOCATION_IDS if expanded else LOCATION_IDS
    for key, value in (("assignments", ALL_PART_IDS if m["schema"] >= 5 else PART_IDS), ("locations", expected_locations)):
        if type(m[key]) is not dict or m[key] != value or any(type(v) is not int for v in m[key].values()):
            raise ValueError(f"unsupported {key}; relocation is not implemented")


def solo_rewards(manifest):
    validate(manifest)
    rng = SeedRandom(manifest["seed"])
    rewards, inventory = {}, set()
    # Constructive progression fill: place each unlock at an already reachable
    # unfilled check, then advance the simulated inventory. Requirements are
    # deliberately the inherited conservative rules, pending route audit.
    names = active_names(manifest)
    expanded = manifest["schema"] == 2
    order = rng.shuffle(progression_pool(manifest))
    if manifest.get('progressive_color_stats'):
        from .stats import UPGRADE_ITEMS
        order.sort(key=lambda item: item in UPGRADE_ITEMS and UPGRADE_ITEMS[item][1] != 'carry')
    def place(remaining, owned, placed):
        if not remaining:
            return placed
        available = [n for n in names if n not in placed and can_reach_manifest(n, owned, manifest)]
        if not available:
            return None
        location = available[rng.below(len(available))]
        for item in dict.fromkeys(remaining):
            next_items = list(remaining); next_items.remove(item)
            next_owned = Counter(owned); next_owned[item] += 1
            result = place(next_items, next_owned, {**placed, location: item})
            if result is not None:
                return result
        return None
    rewards = place(order, Counter(), {})
    if rewards is None:
        raise ValueError("cannot place progression without a self-lock")
    remaining = Counter(item_pool(manifest)) - Counter(rewards.values())
    filler = rng.shuffle(list(remaining.elements())) if manifest.get('benefit_items') else [REPAIR] * sum(remaining.values())
    rewards.update(zip((n for n in names if n not in rewards), filler))
    if Counter(rewards.values()) != Counter(item_pool(manifest)):
        raise ValueError("item pool does not match location count")
    return rewards


def spheres(rewards, manifest=None):
    expanded = len(rewards) > len(NAMES)
    names = tuple(rewards)
    inventory, remaining, result = Counter(), set(names), []
    while remaining:
        reachable = [n for n in names if n in remaining and (can_reach_manifest(n, inventory, manifest) if manifest else can_reach(n, inventory, expanded))]
        if not reachable:
            raise ValueError("unreachable checks: " + ", ".join(sorted(remaining)))
        result.append(reachable)
        inventory.update(rewards[n] for n in reachable)
        remaining.difference_update(reachable)
    return result
