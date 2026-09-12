import importlib.util
import json
import zipfile
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_release", REPO / "scripts" / "package_release.py")
package_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_release)


@pytest.fixture
def fake_build(tmp_path):
    build = tmp_path / "build"
    build.mkdir()
    exe = build / "nectar.exe"
    exe.write_bytes(b"MZ fake production build")
    (build / "SDL2.dll").write_bytes(b"sdl")
    (build / "libwinpthread-1.dll").write_bytes(b"pthread")
    return exe


def test_package_contents(fake_build, tmp_path):
    seed = tmp_path / "seed.json"
    seed.write_text('{"mode": "solo"}')
    zip_path, sums, manifest = package_release.package("0.0.1-test", fake_build, seed=seed, output_dir=tmp_path / "out")
    assert zip_path.name == "pikrando-0.0.1-test-windows-x64.zip" and zip_path.is_file()
    assert sums.read_text().split() == [package_release.sha256(zip_path), zip_path.name]
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        inner = json.loads(archive.read("release-manifest.json"))
        assert archive.read("VERSION") == b"0.0.1-test\n"
    for expected in ("bin/nectar.exe", "bin/SDL2.dll", "bin/libwinpthread-1.dll", "randomizer/runner.py",
                     "randomizer/__init__.py", "launcher/launcher.py", "launcher/gui.py", "launcher/discimage.py", "launcher/rvz.py", "Play.cmd", "examples/Player1.yaml",
                     "README.md", "LICENSES/LICENSE.MD", "LICENSES/LEGAL.md", "seeds/seed.json"):
        assert expected in names
    assert not any("__pycache__" in n or n.startswith("runtime/") for n in names)
    assert manifest == inner
    assert manifest["version"] == "0.0.1-test" and manifest["python_runtime"] == "system"
    assert manifest["exe_sha256"] == package_release.sha256(fake_build)
    assert len(manifest["git_commit"]) == 40
    listed = {f["path"] for f in manifest["files"]}
    assert "bin/nectar.exe" in listed and names - listed == {"release-manifest.json"}


def test_rejects_test_hook_build(fake_build, tmp_path):
    fake_build.write_bytes(b"MZ PIKMIN_RANDOMIZER_TEST_SCRIPT")
    with pytest.raises(package_release.PackageError, match="test-hooks build must not be packaged"):
        package_release.package("0.0.1", fake_build, output_dir=tmp_path / "out")


def test_rejects_missing_dll(fake_build, tmp_path):
    (fake_build.parent / "SDL2.dll").unlink()
    with pytest.raises(package_release.PackageError, match="SDL2.dll"):
        package_release.package("0.0.1", fake_build, output_dir=tmp_path / "out")


def test_audit_rejects_personal_paths_and_logs(tmp_path):
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "native.log").write_text("x")
    (tmp_path / "note.txt").write_text("see C:\\Users\\someone")
    with pytest.raises(package_release.PackageError) as info:
        package_release.audit(tmp_path)
    assert "native.log" in str(info.value) and "note.txt" in str(info.value)
