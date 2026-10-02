import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("p2_launcher", ROOT / "launcher/launcher.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
P2 = {"p2_layout": {"bindings": [{"source_id": 2}]}}


def test_p1_ignores_saved_p2_content():
    assert launcher.resolve_p2_content({}, {"p2_content": "missing"}) == (None, None)


def test_missing_and_ambiguous_inputs_refused(tmp_path):
    with pytest.raises(launcher.LaunchError, match="needs prepared content"):
        launcher.resolve_p2_content(P2, {})
    with pytest.raises(launcher.LaunchError, match="does not exist"):
        launcher.resolve_p2_content(P2, {}, tmp_path / "missing")
    with pytest.raises(launcher.LaunchError, match="either"):
        launcher.resolve_p2_content(P2, {}, tmp_path, tmp_path / "manifest.json")


@pytest.mark.parametrize("kind", ["p2_content", "content_manifest"])
def test_paths_with_spaces_forwarded_without_shell(tmp_path, kind):
    content = tmp_path / "my content folder"
    content.mkdir()
    manifest = tmp_path / "my manifest.json"
    manifest.write_text("{}")
    value = content if kind == "p2_content" else manifest
    folder, document = launcher.resolve_p2_content(P2, {}, **{kind: value})
    command = launcher.build_command("seed.json", "session", "native.exe", "assets",
                                     p2_content=folder, content_manifest=document)
    flag = "--p2-content" if folder else "--content-manifest"
    assert command[command.index(flag) + 1] == str(value.resolve())
    assert launcher.resolve_p2_content(P2, {"p2_content" if folder else "p2_content_manifest": str(value)}) == (folder, document)


def test_gui_keeps_flag_values_out_of_seed_argument(monkeypatch):
    import sys
    monkeypatch.syspath_prepend(str(ROOT / "launcher"))
    spec = importlib.util.spec_from_file_location("p2_gui", ROOT / "launcher/gui.py")
    gui = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gui)
    monkeypatch.setattr(sys, "platform", "linux")
    import tkinter
    monkeypatch.setattr(tkinter, "Tk", lambda: object())
    observed = []
    def app(*args, **kwargs):
        observed.append(args)
        raise RuntimeError("constructor observed")
    monkeypatch.setattr(gui, "LauncherApp", app)
    with pytest.raises(RuntimeError, match="constructor observed"):
        gui.main(["--p2-content", "content folder", "seed.json", "--server", "host:1"])
    assert observed[0][1:] == ("seed.json", "host:1", "content folder", None)
