"""Durable offline checkpoint identity; launch/run tokens are never save identities."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile

IDENTITY_FILE = "midday_identity.json"
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_HEX32 = re.compile(r"[0-9a-f]{32}\Z")


@dataclass(frozen=True)
class CheckpointBinding:
    campaign_id: str
    seed: str
    session_digest: str
    directory: Path


def _read(path: Path, expected_seed: str) -> str:
    # Bound reads and exact schema. Never repair or replace ambiguous old bytes.
    with path.open("rb") as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError("mid-day campaign identity is too large; refusing to reset it")
    try:
        def unique_fields(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate identity field")
                result[key] = value
            return result
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_fields)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("invalid mid-day campaign identity; refusing to reset it") from exc
    if (type(data) is not dict or set(data) != {"schema", "mode", "seed", "campaign"}
            or type(data["schema"]) is not int or data["schema"] != 1
            or data["mode"] != "solo" or data["seed"] != expected_seed
            or type(data["campaign"]) is not str or not _HEX32.fullmatch(data["campaign"])):
        raise ValueError("mid-day campaign identity/version/seed mismatch; refusing to reset it")
    return data["campaign"]


def _sync_directory(directory: Path) -> None:
    if os.name == "nt":
        return  # File fsync is available; POSIX directory descriptors are not.
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def bind_checkpoint_session(session) -> CheckpointBinding:
    """Create once or validate a campaign-local identity without altering Session.

    Atomic hard-link publication refuses overwrite, including concurrent creators.
    Unknown/corrupt identities fail closed. AP is intentionally refused until its
    full native grant/outbox ledger participates in the same checkpoint transaction.
    """
    if session.manifest.get("mode") != "solo":
        raise ValueError("mid-day checkpoint binding currently supports offline solo campaigns")
    seed = session.fingerprint
    if type(seed) is not str or not _HEX64.fullmatch(seed):
        raise ValueError("invalid checkpoint seed fingerprint")
    directory = Path(session.directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    identity = directory / IDENTITY_FILE
    try:
        campaign = _read(identity, seed)
    except FileNotFoundError:
        record = {"schema": 1, "mode": "solo", "seed": seed, "campaign": secrets.token_hex(16)}
        # Only our unique pending path may be cleaned. Never delete a foreign
        # pending file or an existing identity, even when publication fails.
        descriptor, pending_name = tempfile.mkstemp(prefix=".midday-identity-", suffix=".pending", dir=directory)
        pending = Path(pending_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write((json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(pending, identity)  # Same directory; no overwrite race.
            except FileExistsError:
                pass  # The winning complete identity must validate below.
            _sync_directory(directory)
            campaign = _read(identity, seed)
        finally:
            pending.unlink(missing_ok=True)
    # No absolute path or random per-launch token contributes to either digest.
    encoded = b"pikipelago-midday-session-v1\0" + bytes.fromhex(seed) + bytes.fromhex(campaign)
    digest = hashlib.sha256(encoded).hexdigest()
    return CheckpointBinding(campaign, seed, digest, directory / "midday")
