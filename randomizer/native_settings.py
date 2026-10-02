"""Select one player-owned native config independently of seed/run directories."""
import hashlib
import ntpath
import os
from pathlib import Path
import secrets
import warnings

FILENAME = "pikmin_settings.conf"
MAX_BYTES = 1024 * 1024


def _absolute(value):
    if not value or any(ord(c) < 32 or c == '"' for c in value):
        raise ValueError("PIKMIN_SETTINGS_PATH must be an absolute file path")
    if os.name == "nt":
        drive, tail = ntpath.splitdrive(value)
        if value.startswith(("\\\\?\\", "\\\\.\\")) or not drive or not tail.startswith(("/", "\\")):
            raise ValueError("PIKMIN_SETTINGS_PATH must be drive-rooted or UNC")
    elif not os.path.isabs(value):
        raise ValueError("PIKMIN_SETTINGS_PATH must be absolute")
    return Path(value)


def _plain_directory(path):
    return path.is_dir() and not path.is_symlink() and not path.is_junction()


def _read(path):
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise ValueError(f"Settings migration requires a regular file: {path}")
    before = path.stat()
    if before.st_size > MAX_BYTES:
        raise ValueError(f"Settings file exceeds migration limit: {path}")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    after = path.stat()
    if len(data) > MAX_BYTES or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError(f"Settings changed during migration: {path}")
    return data


def _legacy_files(app, session):
    # Enumerate only the two known layout levels; never recursively follow links.
    sessions = {Path(session).absolute()}
    parent = app / "sessions"
    if _plain_directory(parent):
        sessions.update(p for p in parent.iterdir() if _plain_directory(p))
    result = []
    for folder in sorted(sessions, key=str):
        runs = folder / "runs"
        if not _plain_directory(folder) or not _plain_directory(runs):
            continue
        for run in sorted(runs.iterdir(), key=str):
            if _plain_directory(run) and (run / FILENAME).exists():
                result.append(run / FILENAME)
    return result


def bind_settings(env, session_directory, run_directory=None):
    """Mutate only the child environment; migration never overwrites any file.

    Conflicting historical files require an explicit player choice. A valid
    existing stable file wins without inspecting unrelated historical runs.
    Private fixture overrides are authoritative and receive no migration.
    """
    override = env.get("PIKMIN_SETTINGS_PATH")
    if override:
        path = _absolute(override)
        env["PIKMIN_SETTINGS_PATH"] = str(path)
        return {"path": str(path), "status": "explicit", "sources": []}
    if env.get("PIKMIN_RANDOMIZER_TEST_BACKGROUND") == "1":
        if run_directory is None:
            raise ValueError("Background fixture requires its private run directory")
        path = Path(run_directory).absolute() / FILENAME
        env["PIKMIN_SETTINGS_PATH"] = str(path)
        return {"path": str(path), "status": "private-test", "sources": []}
    app = Path(env.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "PikminRandomizer"
    app = app.absolute()
    app.mkdir(parents=True, exist_ok=True)
    target = app / FILENAME
    if target.exists() or target.is_symlink():
        _read(target)
        env["PIKMIN_SETTINGS_PATH"] = str(target)
        return {"path": str(target), "status": "existing", "sources": []}
    sources = _legacy_files(app, session_directory)
    values = [(p, _read(p)) for p in sources]
    if len({data for _, data in values}) > 1:
        env["PIKMIN_SETTINGS_PATH"] = str(target)
        return {"path": str(target), "status": "legacy-choice-needed",
                "sources": [str(p) for p, _ in values],
                "warning": "Previous runs have different in-game settings. Starting with defaults; your old files are unchanged. To keep an old set, close the game and copy the preferred sessions/<seed>/runs/<token>/pikmin_settings.conf to " + str(target) + ". Otherwise change preferences in F1, then close the settings menu to save them for future launches."}
    status = "new"
    if values:
        tmp = app / (".settings-migrate-" + secrets.token_hex(16))
        owned_temp = False
        try:
            with tmp.open("xb") as stream:
                owned_temp = True
                if stream.write(values[0][1]) != len(values[0][1]):
                    raise OSError("Short write while migrating native settings")
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(tmp, target)  # Exclusive publication: another launch's file wins.
                status = "migrated"
            except FileExistsError:
                _read(target)
                status = "existing"
        finally:
            try:
                if owned_temp:
                    tmp.unlink(missing_ok=True)
            except OSError as exc:
                warnings.warn(f"Could not remove owned settings migration temporary {tmp}: {exc}")
    env["PIKMIN_SETTINGS_PATH"] = str(target)
    return {"path": str(target), "status": status,
            "sources": [str(p) for p, _ in values],
            "migrated_sha256": hashlib.sha256(values[0][1]).hexdigest() if status == "migrated" else None}
