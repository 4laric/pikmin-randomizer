"""Netplay client mirror (M4 lane C, issue #885).

The native netplay client writes ``mirror-events.txt`` in its run directory;
this module is the exact line grammar for that file, the idempotent ingest
into ``mirror.json``, and the host-side export helper. ``mirror.json`` uses
the same schema as ``session.json`` (see ``randomizer/session.py``) so the
overlay and tracker read it unchanged.

Line grammar (ASCII only, each line 1..256 bytes, ``\\n`` terminated)::

    FRAME <frame> RECEIVED <item_id>
    FRAME <frame> CHECKED <location>
    FRAME <frame> DEATHS <total>
    FRAME <frame> DEATHLINK <total>
    FRAME <frame> EMPEROR
    FRAME <frame> SAVE_RESULT <gen> <digest>
    FRAME <frame> SAVE_FAIL <gen>

``<frame>`` is the netplay frame (0..4294967295). ``RECEIVED`` carries an
Archipelago item id from the manifest pool. ``CHECKED`` carries the exact
location name (which may contain spaces). ``DEATHS``/``DEATHLINK`` carry
absolute monotonic totals of ordinary Pikmin deaths / received DeathLinks.
``EMPEROR`` carries no argument. ``SAVE_RESULT`` carries the campaign
checkpoint generation and the lowercase hex SHA-256 of the checkpoint file;
``SAVE_FAIL`` records a failed day-end save for the same generation.

The parser is strict: bounded lengths, single-space separators, ASCII
printable characters only, and any unknown tag or out-of-range value raises
``ValueError``. Ingest is idempotent: exact-duplicate lines are no-ops, and
the underlying state updates (set membership, monotonic totals, flags) are
no-ops when replayed.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from .benefits import benefit_state
from .catalog import (
    FLARLIC,
    FOREST_ACCESS,
    IMPACT_ACCESS,
    ITEM_IDS,
    RED,
    REPAIR,
    UNLOCKS,
    active_names,
    item_pool,
)
from .seed import fingerprint, solo_rewards
from .session import Session, atomic_write
from .stats import upgrade_counts

MIRROR_DIRNAME = "netplay"
MIRROR_FILENAME = "mirror.json"
EVENTS_FILENAME = "mirror-events.txt"
STATE_FILENAME = "state.txt"
BOOTSTRAP_FILENAME = "bootstrap.txt"
CARD_DIRNAME = "card"
INGEST_FILENAME = ".mirror-ingest.json"
SAVE_RESULT_FILENAME = "SAVE_RESULT.txt"

MAX_LINE_LEN = 256
MAX_FRAME = 2 ** 32 - 1
MAX_ITEM_ID = 2 ** 31 - 1
MAX_TOTAL = 1_000_000
MAX_GEN_DIGITS = 20
DIGEST_LEN = 64

_TAGS = ("RECEIVED", "CHECKED", "DEATHS", "DEATHLINK", "EMPEROR", "SAVE_RESULT", "SAVE_FAIL")


def _fail(reason):
    raise ValueError("invalid mirror event: " + reason)


def _uint(text, what, limit):
    if not text or len(text) > 10 or not text.isdigit():
        _fail(f"bad {what}")
    value = int(text)
    if value > limit:
        _fail(f"{what} out of range")
    return value


def _is_hex(text, size):
    return len(text) == size and all(c in "0123456789abcdef" for c in text)


def parse_mirror_line(line):
    """Parse one grammar line; return ``(frame, tag, args)`` or raise."""
    if type(line) is not str or not line or len(line) > MAX_LINE_LEN:
        _fail("bad length")
    if any(ord(c) < 0x20 or ord(c) > 0x7E for c in line):
        _fail("non-printable ASCII")
    parts = line.split(" ")
    if any(p == "" for p in parts) or len(parts) < 3:
        _fail("bad separators")
    if parts[0] != "FRAME":
        _fail("missing FRAME prefix")
    frame = _uint(parts[1], "frame", MAX_FRAME)
    tag = parts[2]
    if tag not in _TAGS:
        _fail("unknown tag " + tag)
    rest = parts[3:]
    if tag == "EMPEROR":
        if rest:
            _fail("EMPEROR takes no argument")
        return (frame, tag, ())
    if tag == "CHECKED":
        name = " ".join(rest)
        if not rest or not 1 <= len(name) <= 128:
            _fail("bad location")
        return (frame, tag, (name,))
    if tag in ("DEATHS", "DEATHLINK"):
        if len(rest) != 1:
            _fail(tag + " takes one argument")
        return (frame, tag, (_uint(rest[0], "total", MAX_TOTAL),))
    if tag == "RECEIVED":
        if len(rest) != 1:
            _fail("RECEIVED takes one argument")
        return (frame, tag, (_uint(rest[0], "item id", MAX_ITEM_ID),))
    if tag == "SAVE_RESULT":
        if len(rest) != 2 or not rest[0] or len(rest[0]) > MAX_GEN_DIGITS or not rest[0].isdigit():
            _fail("bad checkpoint generation")
        if not _is_hex(rest[1], DIGEST_LEN):
            _fail("bad checkpoint digest")
        return (frame, tag, (int(rest[0]), rest[1]))
    if len(rest) != 1 or not rest[0] or len(rest[0]) > MAX_GEN_DIGITS or not rest[0].isdigit():
        _fail("bad checkpoint generation")
    return (frame, tag, (int(rest[0]),))


def mirror_dir_for(session_dir, manifest_or_fingerprint):
    fingerprint_value = (manifest_or_fingerprint if type(manifest_or_fingerprint) is str
                         else fingerprint(manifest_or_fingerprint))
    return Path(session_dir) / MIRROR_DIRNAME / fingerprint_value


def run_dir_for(mirror_dir, token):
    if type(token) is not str or not 8 <= len(token) <= 128 or not _is_hex(token, len(token)):
        raise ValueError("invalid netplay run token")
    return Path(mirror_dir) / "runs" / token


def restamp_bootstrap_for_peer(bootstrap_text, peer_token):
    """Return host bootstrap text with the SESSION line re-stamped for a peer."""
    if type(bootstrap_text) is not str or type(peer_token) is not str:
        raise ValueError("invalid bootstrap re-stamp")
    if not 8 <= len(peer_token) <= 128 or not _is_hex(peer_token, len(peer_token)):
        raise ValueError("invalid peer token")
    lines = bootstrap_text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    stamped = [f"SESSION {peer_token}" if line.startswith("SESSION ") else line for line in lines]
    if sum(line.startswith("SESSION ") for line in stamped) != 1:
        raise ValueError("bootstrap has no single SESSION line")
    if stamped == lines:
        raise ValueError("bootstrap SESSION line unchanged")
    return "\n".join(stamped) + "\n"


def mirror_inventory(manifest, data):
    if manifest["mode"] == "solo":
        rewards = solo_rewards(manifest)
        return Counter(rewards[n] for n in data["checked"])
    names = {v: k for k, v in ITEM_IDS.items()}
    return Counter(names[i] for i in data["received"])


def render_mirror_state(manifest, data, token, ready):
    """Debug ``state.txt`` rendering for a mirror; same format as the host."""
    inventory = mirror_inventory(manifest, data)
    unlocks = sum(1 << i for i, name in enumerate(UNLOCKS) if inventory[name])
    if manifest["schema"] >= 3 and inventory[FOREST_ACCESS]:
        unlocks |= 32
    if manifest["schema"] >= 4 and inventory[RED]:
        unlocks |= 64
    if manifest["schema"] >= 5 and inventory[IMPACT_ACCESS]:
        unlocks |= 128
    checks = sum(1 << i for i, name in enumerate(active_names(manifest)) if name in data["checked"])
    if manifest["schema"] >= 8:
        indices = [str(i) for i, n in enumerate(active_names(manifest)) if n in data["checked"]]
        checks = "CHECKS " + str(len(indices)) + (" " + " ".join(indices) if indices else "")
    emperor = (" EMPEROR " + str(int(data["emperor_defeated"]))) if manifest.get("goal_mode") == "emperor_bulblax" else ""
    death_link = (" DEATHLINK " + str(data["death_links_received"])) if manifest.get("death_link") else ""
    repairs = min(inventory[REPAIR], manifest["goal"])
    if manifest["schema"] >= 2:
        flarlic = min(10 - manifest.get("starting_flarlic", 2), inventory[FLARLIC])
        return (f"PIKMIN_STATE {manifest['schema']} {token} {int(ready)} {repairs} {unlocks} {flarlic} "
                f"{checks}{upgrade_counts(manifest, inventory)}{benefit_state(manifest, inventory)}"
                f"{emperor}{death_link} END\n")
    return f"PIKMIN_STATE 1 {token} {int(ready)} {repairs} {unlocks} {checks} END\n"


def initial_mirror_data(manifest):
    data = dict(schema=1, fingerprint=fingerprint(manifest), checked=[], received=[], ap_identity=None)
    if manifest.get("goal_mode") == "emperor_bulblax":
        data["emperor_defeated"] = False
    if manifest.get("death_link"):
        data["pikmin_deaths"] = 0
        data["death_links_received"] = 0
    return data


def validate_mirror_data(manifest, data):
    """Session-schema validation for ``mirror.json`` (same rules as Session)."""
    probe = Session.__new__(Session)
    probe.manifest = manifest
    probe.fingerprint = fingerprint(manifest)
    probe.names = active_names(manifest)
    probe.allowed_items = {ITEM_IDS[n] for n in item_pool(manifest)}
    expected = initial_mirror_data(manifest)
    if type(data) is not dict or set(data) != set(expected):
        raise ValueError("mirror data does not match the session schema")
    if (type(data["schema"]) is not int or data["schema"] != 1
            or data["fingerprint"] != probe.fingerprint):
        raise ValueError("invalid mirror identity")
    if (type(data["checked"]) is not list
            or any(type(n) is not str or n not in probe.names for n in data["checked"])
            or len(data["checked"]) != len(set(data["checked"]))):
        raise ValueError("invalid mirror checks")
    if (type(data["received"]) is not list
            or any(type(i) is not int or i not in probe.allowed_items for i in data["received"])):
        raise ValueError("invalid mirror received items")
    identity = data["ap_identity"]
    if identity is not None and (type(identity) is not list or len(identity) != 3
            or type(identity[0]) is not str or any(type(v) is not int for v in identity[1:])):
        raise ValueError("invalid mirror AP identity")
    if manifest["mode"] == "solo" and (data["received"] or identity is not None):
        raise ValueError("solo mirror contains AP state")
    if "emperor_defeated" in data and type(data["emperor_defeated"]) is not bool:
        raise ValueError("invalid mirror emperor state")
    for key in ("pikmin_deaths", "death_links_received"):
        if key in data and (type(data[key]) is not int or data[key] < 0):
            raise ValueError("invalid mirror death link state")
    return True


class MirrorStore:
    """Idempotent ``mirror.json`` ingest for one netplay client run."""

    def __init__(self, manifest, mirror_path):
        self.manifest = manifest
        self.path = Path(mirror_path)
        self.names = active_names(manifest)
        self.allowed_items = {ITEM_IDS[n] for n in item_pool(manifest)}
        if self.path.exists():
            validate_mirror_data(manifest, json.loads(self.path.read_text(encoding="utf-8")))
        else:
            atomic_write(self.path, json.dumps(initial_mirror_data(manifest), indent=2) + "\n")

    def load(self):
        data = json.loads(self.path.read_text(encoding="utf-8"))
        validate_mirror_data(self.manifest, data)
        return data

    def save(self, data):
        validate_mirror_data(self.manifest, data)
        atomic_write(self.path, json.dumps(data, indent=2) + "\n")

    def apply(self, data, event):
        """Apply a parsed event; return True when it changed ``data``."""
        frame, tag, args = event
        if tag == "RECEIVED":
            (item,) = args
            if item not in self.allowed_items:
                raise ValueError("unknown item in mirror stream")
            data["received"].append(item)
            return True
        if tag == "CHECKED":
            (name,) = args
            if name not in self.names:
                raise ValueError("unknown location in mirror stream: " + str(name))
            if name in data["checked"]:
                return False
            data["checked"].append(name)
            return True
        if tag == "DEATHS":
            (total,) = args
            if not self.manifest.get("death_link"):
                raise ValueError("death link disabled for this seed")
            if total < data["pikmin_deaths"]:
                raise ValueError("mirror death total retracted")
            if total == data["pikmin_deaths"]:
                return False
            data["pikmin_deaths"] = total
            return True
        if tag == "DEATHLINK":
            (total,) = args
            if not self.manifest.get("death_link"):
                raise ValueError("death link disabled for this seed")
            if total < data["death_links_received"]:
                raise ValueError("mirror death link total retracted")
            if total == data["death_links_received"]:
                return False
            data["death_links_received"] = total
            return True
        if tag == "EMPEROR":
            if self.manifest.get("goal_mode") != "emperor_bulblax":
                raise ValueError("emperor goal disabled for this seed")
            if data["emperor_defeated"]:
                return False
            data["emperor_defeated"] = True
            return True
        # SAVE_RESULT / SAVE_FAIL carry the card-level checkpoint, which lives
        # beside mirror.json (see MirrorRun); the session view is unchanged.
        return False


def _checkpoint_candidates(session_dir):
    root = Path(session_dir)
    found = []
    for path in list((root / "campaign").glob("*.sav")) + list(root.glob("runs/*/campaign/*.sav")):
        if path.is_file() and path.stem.isdigit() and 1 <= len(path.stem) <= MAX_GEN_DIGITS:
            found.append(path)
    return found


def export_client_bundle(manifest, session_dir, peer_token, host_run_token=None):
    """Describe what a netplay client needs; reads the host session, writes nothing.

    Returns a JSON-serializable dict with the peer-specific bootstrap text
    (``SESSION`` re-stamped, every other byte identical), the manifest
    fingerprint, and the latest campaign checkpoint path, generation and
    SHA-256 (or ``None`` when the host has no checkpoint yet).
    """
    if not 8 <= len(peer_token) <= 128 or not _is_hex(peer_token, len(peer_token)):
        raise ValueError("invalid peer token")
    runs = Path(session_dir) / "runs"
    if host_run_token is not None:
        bootstrap_path = runs / host_run_token / BOOTSTRAP_FILENAME
        if not bootstrap_path.is_file():
            raise ValueError("unknown host run token")
    else:
        bootstraps = sorted(runs.glob("*/" + BOOTSTRAP_FILENAME),
                            key=lambda p: p.stat().st_mtime_ns)
        if not bootstraps:
            raise ValueError("host has no native run yet")
        bootstrap_path = bootstraps[-1]
    bootstrap_text = bootstrap_path.read_text(encoding="ascii")
    stamped = restamp_bootstrap_for_peer(bootstrap_text, peer_token)
    checkpoint_path = checkpoint_gen = checkpoint_hash = None
    candidates = _checkpoint_candidates(session_dir)
    if candidates:
        latest = max(candidates, key=lambda p: (int(p.stem), p.stat().st_mtime_ns))
        checkpoint_path = str(latest.resolve())
        checkpoint_gen = int(latest.stem)
        digest = hashlib.sha256()
        with latest.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        checkpoint_hash = digest.hexdigest()
    session_path = Path(session_dir) / "session.json"
    snapshot = None
    if session_path.is_file():
        snapshot = json.loads(session_path.read_text(encoding="utf-8"))
    return dict(fingerprint=fingerprint(manifest), peer_token=peer_token,
                host_run_token=bootstrap_path.parent.name, bootstrap_text=stamped,
                checkpoint_path=checkpoint_path, checkpoint_gen=checkpoint_gen,
                checkpoint_hash=checkpoint_hash, session_snapshot=snapshot)
