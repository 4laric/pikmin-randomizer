"""Generated-session launcher/cache content staging (lane 05, #442).

Family extractors are absent, so these tests use synthetic source blobs and a
synthetic retail asset root to prove the launcher installs content before a
native process starts, validates it against the seed's P2 identities, connects it
to the native asset-lookup tree, reuses a shared cache across sessions, and fails
safely on missing/wrong/corrupt content.
"""
import hashlib
from pathlib import Path

import pytest

import randomizer.runner as runner
from experimental.pikmin2_staging import (
    StagingError,
    build_manifest,
    dump_manifest,
    stage_session_content,
)
from randomizer.seed import generate


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make_manifest(root, count=2, identities=(79, 30)):
    source = root / "source"
    source.mkdir(parents=True, exist_ok=True)
    entries = []
    for index in range(count):
        name = f"asset{index}.bin"
        data = f"payload-{index}".encode()
        (source / name).write_bytes(data)
        entries.append(dict(id=f"asset{index}", kind="model", source=f"source/{name}",
                            destination=f"tree/{name}", sha256=sha(data)))
    manifest_path = root / "content-manifest.json"
    dump_manifest(build_manifest(3, entries, notes="synthetic", identities=identities), manifest_path)
    return manifest_path, source


def make_retail(root):
    retail = root / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)
    (retail / "dataDir" / "stages" / "base.bin").write_bytes(b"retail")
    return retail


def test_fresh_session_stages_content(tmp_path):
    manifest_path, source = make_manifest(tmp_path)
    receipt = stage_session_content(manifest_path, tmp_path / "sess")
    assert receipt["cached"] is False
    assert (tmp_path / "sess" / "content" / "tree" / "asset0.bin").read_bytes() == b"payload-0"
    assert all(entry["status"] in ("staged", "cached") for entry in receipt["entries"])


def test_content_must_cover_required_identities(tmp_path):
    manifest_path, source = make_manifest(tmp_path)
    receipt = stage_session_content(manifest_path, tmp_path / "sess", required_identities=[30, 79])
    assert receipt["identities"] == ["30", "79"]
    with pytest.raises(StagingError):
        stage_session_content(manifest_path, tmp_path / "sess2", required_identities=[79, 15])
    undeclared, _ = make_manifest(tmp_path / "undeclared", identities=None)
    with pytest.raises(StagingError):
        stage_session_content(undeclared, tmp_path / "sess3", required_identities=[79])


def test_asset_overlay_connects_native_lookup(tmp_path):
    manifest_path, source = make_manifest(tmp_path)
    retail = make_retail(tmp_path)
    receipt = stage_session_content(manifest_path, tmp_path / "run" / "assets",
                                    required_identities=[79, 30], retail_assets=retail)
    assert receipt["mode"] == "asset-overlay" and receipt["identities"] == ["30", "79"]
    assets = tmp_path / "run" / "assets"
    assert (assets / "tree" / "asset0.bin").read_bytes() == b"payload-0"
    # Untouched retail content stays reachable through the private overlay tree.
    assert (assets / "dataDir" / "stages" / "base.bin").read_bytes() == b"retail"
    assert (assets.parent / "assets-content-receipt.json").is_file()


def test_cached_launch_reuses_source_free_cache(tmp_path):
    manifest_path, source = make_manifest(tmp_path)
    cache = tmp_path / "cache"
    stage_session_content(manifest_path, tmp_path / "sess-a", cache_dir=cache)
    # Remove the sources: a cache hit must not need them again.
    for path in source.iterdir():
        path.unlink()
    receipt = stage_session_content(manifest_path, tmp_path / "sess-b", cache_dir=cache)
    assert receipt["cached"] is True
    assert (tmp_path / "sess-b" / "content" / "tree" / "asset1.bin").read_bytes() == b"payload-1"


def test_missing_source_fails_before_session_content(tmp_path):
    manifest_path, source = make_manifest(tmp_path)
    (source / "asset0.bin").unlink()
    with pytest.raises(StagingError):
        stage_session_content(manifest_path, tmp_path / "sess")
    assert not (tmp_path / "sess" / "content").exists()


def test_wrong_source_hash_fails(tmp_path):
    manifest_path, source = make_manifest(tmp_path)
    (source / "asset0.bin").write_bytes(b"tampered")
    with pytest.raises(StagingError):
        stage_session_content(manifest_path, tmp_path / "sess")


def test_corrupt_cache_fails_closed(tmp_path):
    manifest_path, source = make_manifest(tmp_path)
    cache = tmp_path / "cache"
    stage_session_content(manifest_path, tmp_path / "sess-a", cache_dir=cache)
    cached_file = next(cache.rglob("asset0.bin"))
    cached_file.write_bytes(b"corrupt")
    with pytest.raises(StagingError):
        stage_session_content(manifest_path, tmp_path / "sess-b", cache_dir=cache)


def test_launch_stages_content_into_asset_tree(tmp_path, monkeypatch):
    manifest_path, source = make_manifest(tmp_path)
    retail = make_retail(tmp_path)
    launch = generate("seed-a")

    called = []
    async def fake_serve(*args, **kwargs):
        called.append(True)

    monkeypatch.setattr(runner, "serve", fake_serve)
    runner.launch(launch, tmp_path / "sess", assets=retail, content_manifest=manifest_path)
    assert called == [True]
    staged = list((tmp_path / "sess" / "runs").glob("*/assets/tree/asset0.bin"))
    assert len(staged) == 1 and staged[0].read_bytes() == b"payload-0"
    assert (staged[0].parents[1] / "dataDir" / "stages" / "base.bin").read_bytes() == b"retail"


def test_launch_does_not_start_on_staging_failure(tmp_path, monkeypatch):
    manifest_path, source = make_manifest(tmp_path)
    retail = make_retail(tmp_path)
    (source / "asset0.bin").unlink()
    launch = generate("seed-a")

    called = []
    async def fake_serve(*args, **kwargs):
        called.append(True)

    monkeypatch.setattr(runner, "serve", fake_serve)
    with pytest.raises(StagingError):
        runner.launch(launch, tmp_path / "sess", assets=retail, content_manifest=manifest_path)
    assert called == []
