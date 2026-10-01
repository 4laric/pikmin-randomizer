"""Netplay client mirror (M4 lane C, issue #885).

The native netplay client writes ``mirror-events.txt`` in its run directory;
this module is the exact line grammar for that file, the idempotent ingest
into ``mirror.json``, and the host-side export helper. ``mirror.json`` uses
the same schema as ``session.json`` (see ``randomizer/session.py``) so the
overlay and tracker read it unchanged.

Line grammar (ASCII only, each line 1..256 bytes, ``\\n`` terminated)::

    FRAME <frame> RECEIVED <index> <item_id>
    FRAME <frame> CHECKED <location>
    FRAME <frame> DEATHS <total>
    FRAME <frame> DEATHLINK <total>
    FRAME <frame> EMPEROR
    FRAME <frame> SAVE_RESULT <gen> <digest>
    FRAME <frame> SAVE_FAIL <gen>

``<frame>`` is the netplay frame (0..4294967295, canonical digits, no leading
zeros). ``RECEIVED`` carries the 0-based AP receive index (the same index
``Session.receive`` uses) plus the Archipelago item id from the manifest pool.
``CHECKED`` carries the exact location name (which may contain spaces).
``DEATHS``/``DEATHLINK`` carry absolute session-cumulative monotonic totals of
ordinary Pikmin deaths / received DeathLinks (matching what host
``session.json`` accumulates across days and reconnects, not the per-run
``deaths.txt`` count). ``EMPEROR`` carries no argument. ``SAVE_RESULT``
carries the campaign checkpoint generation (1..18446744073709551615,
canonical digits) and the lowercase hex SHA-256 of the checkpoint file;
``SAVE_FAIL`` records a failed day-end save for the same generation.

Frames are non-decreasing along the stream; a frame lower than the last
applied frame is rejected. The native writer must emit ``RECEIVED`` lines in
index order without gaps; ingest applies index ``len(received)`` and treats a
lower index with a matching item as a no-op duplicate, rejecting gaps and
conflicts. All other tags are naturally idempotent (set membership, monotonic
totals, flags). The runner persists the ingest cursor (byte offset, last
frame, prefix hash, checkpoint) so a relaunch of the same peer token resumes;
each ``runs/<token>/`` directory is stable per peer token derived from the
host bootstrap ``SESSION`` line. A malformed stream is fatal to the run
(matching host semantics): the offending poll raises and applies nothing.

The parser is strict: bounded lengths, single-space separators, ASCII
printable characters only (no ``\\r`` or other controls; lines are split on
``\\n`` only), canonical numbers, and any unknown tag or out-of-range value
raises ``ValueError``.

Native file layout note: a native client launched from ``runs/<token>/``
derives ``campaignDirectory = <run>/../../campaign`` and ``saveRoot =
campaign/card`` (``pc_randomizer.cpp``), so real ``*.sav`` checkpoints live at
``session/netplay/<fingerprint>/campaign/``. The ``runs/<token>/card/``
directory here holds only the ``SAVE_RESULT.txt`` pointer copy for debugging.

Debug ``state.txt`` note: the runner renders a host-format ``state.txt`` in
the run directory for log comparison only. The native netplay client must
ignore it in client mode and consume the net state stream instead; it is
always rendered ``ready=1`` because the local-file link is live by
construction.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from .catalog import (
    ITEM_IDS,
    active_names,
    item_pool,
)
from .seed import fingerprint, solo_rewards
from .session import (
    atomic_write,
    initial_session_data,
    render_session_state,
    validate_session_data,
)

MIRROR_DIRNAME = "netplay"
MIRROR_FILENAME = "mirror.json"
EVENTS_FILENAME = "mirror-events.txt"
HELLO_FILENAME = "hello.txt"
STATE_FILENAME = "state.txt"
BOOTSTRAP_FILENAME = "bootstrap.txt"
CARD_DIRNAME = "card"
INGEST_FILENAME = ".mirror-ingest.json"
SAVE_RESULT_FILENAME = "SAVE_RESULT.txt"

MAX_LINE_LEN = 256
MAX_FRAME = 2 ** 32 - 1
MAX_ITEM_ID = 2 ** 31 - 1
MAX_RECEIVE_INDEX = 10_000_000
MAX_TOTAL = 1_000_000
MAX_DEATHLINK_TOTAL = (1 << 32) - 1
MAX_GEN = 2 ** 64 - 1
DIGEST_LEN = 64

_TAGS = ("RECEIVED", "CHECKED", "DEATHS", "DEATHLINK", "EMPEROR", "SAVE_RESULT", "SAVE_FAIL")


def _fail(reason):
    raise ValueError("invalid mirror event: " + reason)


def _uint(text, what, limit):
    if not text or len(text) > 10 or not text.isdigit():
        _fail(f"bad {what}")
    if len(text) > 1 and text[0] == "0":
        _fail(f"non-canonical {what}")
    value = int(text)
    if value > limit:
        _fail(f"{what} out of range")
    return value


def _gen(text):
    if not text or len(text) > 20 or not text.isdigit():
        _fail("bad checkpoint generation")
    if len(text) > 1 and text[0] == "0":
        _fail("non-canonical checkpoint generation")
    value = int(text)
    if value < 1 or value > MAX_GEN:
        _fail("checkpoint generation out of range")
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
        return (frame, tag, (_uint(rest[0], "total", MAX_DEATHLINK_TOTAL if tag == "DEATHLINK" else MAX_TOTAL),))
    if tag == "RECEIVED":
        if len(rest) != 2:
            _fail("RECEIVED takes two arguments")
        return (frame, tag, (_uint(rest[0], "index", MAX_RECEIVE_INDEX),
                             _uint(rest[1], "item id", MAX_ITEM_ID)))
    if tag == "SAVE_RESULT":
        if len(rest) != 2:
            _fail("bad checkpoint generation")
        gen = _gen(rest[0])
        if not _is_hex(rest[1], DIGEST_LEN):
            _fail("bad checkpoint digest")
        return (frame, tag, (gen, rest[1]))
    if len(rest) != 1:
        _fail("bad checkpoint generation")
    return (frame, tag, (_gen(rest[0]),))


def is_thelynk(manifest):
    return type(manifest) is dict and "Options" in manifest and "Seed" in manifest and "Slot" in manifest


def mirror_fingerprint(manifest):
    if is_thelynk(manifest):
        from .thelynk import session_fingerprint
        return session_fingerprint(manifest)
    return fingerprint(manifest)


def mirror_dir_for(session_dir, manifest_or_fingerprint):
    fingerprint_value = (manifest_or_fingerprint if type(manifest_or_fingerprint) is str
                         else mirror_fingerprint(manifest_or_fingerprint))
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
    if is_thelynk(manifest):
        from .thelynk import render_session_state as render_thelynk
        return render_thelynk(data, token, ready)
    return render_session_state(manifest, active_names(manifest),
                                mirror_inventory(manifest, data), data, token, ready)


def initial_mirror_data(manifest):
    if is_thelynk(manifest):
        from .thelynk import initial_session_data as initial_thelynk
        return initial_thelynk(manifest)
    return initial_session_data(manifest)


def validate_mirror_data(manifest, data):
    """Session-schema validation for ``mirror.json`` (same rules as Session)."""
    try:
        if is_thelynk(manifest):
            from .thelynk import validate_session_data as validate_thelynk
            validate_thelynk(manifest, data)
        else:
            validate_session_data(manifest, data)
    except ValueError as exc:
        raise ValueError("mirror data does not match the session schema: " + str(exc))
    return True


class MirrorStore:
    """Idempotent ``mirror.json`` ingest for one netplay client run."""

    def __init__(self, manifest, mirror_path):
        self.manifest = manifest
        self.path = Path(mirror_path)
        if is_thelynk(manifest):
            from .thelynk import enabled_locations, SUPPORTED_ITEMS
            self.locations = enabled_locations(manifest["Options"])
            self.names = list(self.locations)
            self.allowed_items = SUPPORTED_ITEMS
        else:
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
            index, item = args
            if item not in self.allowed_items:
                raise ValueError("unknown item in mirror stream")
            have = data["received"]
            if index < len(have):
                if have[index] != item:
                    raise ValueError("mirror item stream conflicts with persisted receipts")
                return False
            if index > len(have):
                raise ValueError("mirror item stream gap; native must emit RECEIVED in index order")
            if is_thelynk(self.manifest):
                from .thelynk import PART_ITEMS
                if len(have) >= len(self.names) or (item in PART_ITEMS.values() and item in have):
                    raise ValueError("invalid TheLynk receipt count or duplicate unique part")
            have.append(item)
            return True
        if tag == "CHECKED":
            (name,) = args
            if name not in self.names:
                raise ValueError("unknown location in mirror stream: " + str(name))
            if is_thelynk(self.manifest):
                name = self.locations[name]  # original external TheLynk numeric journal identity
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
    for path in (root / "campaign").glob("*.sav"):
        if path.is_file() and len(path.stem) == 20 and path.stem.isdigit():
            found.append(path)
    return found


def export_client_bundle(manifest, session_dir, peer_token, host_run_token=None):
    """Describe what a netplay client needs; reads the host session, writes nothing.

    Returns a JSON-serializable dict with the peer-specific bootstrap text
    (``SESSION`` re-stamped, every other byte identical), the manifest
    fingerprint, and the latest campaign checkpoint path, generation and
    SHA-256 (or ``None`` when the host has no checkpoint yet).

    The host runner calls this before the session starts and hands
    ``bootstrap_text`` (plus the checkpoint out of band) to each peer. It
    writes nothing into the host session.
    """
    if type(peer_token) is not str or not 8 <= len(peer_token) <= 128 or not _is_hex(peer_token, len(peer_token)):
        raise ValueError("invalid peer token")
    runs = Path(session_dir) / "runs"
    if host_run_token is not None:
        if (type(host_run_token) is not str or not 8 <= len(host_run_token) <= 128
                or not _is_hex(host_run_token, len(host_run_token))):
            raise ValueError("invalid host run token")
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
    return dict(fingerprint=mirror_fingerprint(manifest), peer_token=peer_token,
                host_run_token=bootstrap_path.parent.name, bootstrap_text=stamped,
                checkpoint_path=checkpoint_path, checkpoint_gen=checkpoint_gen,
                checkpoint_hash=checkpoint_hash, session_snapshot=snapshot)
