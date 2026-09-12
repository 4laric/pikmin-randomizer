import importlib.util
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "launcher" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


discimage = load("discimage")
launcher = load("launcher")


def test_image_detection_and_progress():
    assert discimage.is_disc_image("Pikmin.ISO") and discimage.is_disc_image(Path("x") / "game.gcm")
    assert discimage.is_disc_image("Pikmin.rvz") and discimage.needs_conversion("Pikmin.RVZ") and not discimage.needs_conversion("Pikmin.iso")
    assert not discimage.is_disc_image("Pikmin.gcz") and not discimage.is_disc_image("") and not discimage.is_disc_image(None)
    assert discimage.progress_percent("[42%] dataDir/stages/x") == 42
    assert discimage.progress_percent("Checking the image...") is None


def fake_extractor(tmp_path, script):
    """A .cmd standing in for nectar-launcher.exe; %2 is the --rom value, %4 the --install-dir."""
    exe = tmp_path / "nectar-launcher.cmd"
    exe.write_text("@echo off\r\n" + script + "\r\n", encoding="ascii")
    return exe


def test_extract_reuses_complete_extraction_and_reports_failure(tmp_path):
    image = tmp_path / "Pikmin.iso"; image.write_bytes(b"GPIE01")
    root = tmp_path / "game-data"
    good = fake_extractor(tmp_path, 'mkdir "%4\\assets\\dataDir\\stages" & echo marker> "%4\\assets\\.pikmin-assets" & echo [50%%] dataDir\\a & echo [100%%] done')
    lines = []
    assets = discimage.extract_image(image, good, root, launcher.assets_problem, lines.append)
    assert Path(assets) == root / "assets" and (root / "assets" / ".pikmin-assets").is_file()
    assert any(discimage.progress_percent(l) == 50 for l in lines)
    # A complete extraction is reused without running the extractor again.
    bad = fake_extractor(tmp_path, "echo should not run & exit /b 9")
    assert discimage.extract_image(image, bad, root, launcher.assets_problem) == assets
    # Failure preserves the actual diagnostic without blaming the disc format.
    with pytest.raises(discimage.ExtractError) as info:
        discimage.extract_image(image, bad, tmp_path / "fresh", launcher.assets_problem)
    assert "exit 9" in str(info.value) and "should not run" in str(info.value)
    assert "The image must be" not in str(info.value)
    with pytest.raises(discimage.ExtractError):
        discimage.extract_image(tmp_path / "missing.iso", good, root, launcher.assets_problem)
    with pytest.raises(discimage.ExtractError):
        discimage.extract_image(tmp_path / "Pikmin.rvz", good, root, launcher.assets_problem)


def test_launcher_resolves_image_override(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    image = tmp_path / "Pikmin.gcm"; image.write_bytes(b"GPIE01")
    calls = []
    def fake_extract(path, install_root=None, on_line=None, root=None):
        calls.append(str(path))
        return str(tmp_path / "assets")
    monkeypatch.setattr(launcher, "extract_image", fake_extract)
    config = {}
    assert launcher.resolve_assets(config, str(image)) == str(tmp_path / "assets")
    assert calls == [str(image)] and config["image"] == str(image.resolve())
    assert launcher.load_config()["assets"] == str(tmp_path / "assets")
    assert launcher.game_data_dir() == tmp_path / "appdata" / "PikminRandomizer" / "game-data"

def test_interrupted_decode_is_not_reused(tmp_path, monkeypatch):
    old = tmp_path / "Pikmin.converted.iso"
    old.write_bytes(b"incomplete")
    monkeypatch.setattr(discimage.rvz, "describe", lambda image: {})
    paths = []
    def convert(image, path, progress):
        paths.append(path)
        path.write_bytes(b"complete")
    monkeypatch.setattr(discimage.rvz, "convert_to_iso", convert)
    result = discimage.convert_image(tmp_path / "Pikmin.rvz", tmp_path)
    assert result != old and result.read_bytes() == b"complete"
    assert old.read_bytes() == b"incomplete"
    def failed(image, path, progress):
        paths.append(path)
        path.write_bytes(b"partial")
        raise discimage.rvz.RvzError("decode failed")
    monkeypatch.setattr(discimage.rvz, "convert_to_iso", failed)
    with pytest.raises(discimage.ExtractError, match="decode failed"):
        discimage.convert_image(tmp_path / "Pikmin.rvz", tmp_path)
    assert not paths[-1].exists()
    assert result.exists()  # Only the failed attempt's own file is removed.
