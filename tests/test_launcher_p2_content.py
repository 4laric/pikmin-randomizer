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
    assert launcher.resolve_p2_content({}, {"p2_content_manifest": "saved missing"},
                                       "explicit missing", "explicit missing manifest") == (None, None)


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
    from types import SimpleNamespace
    monkeypatch.setitem(sys.modules, "tkinter", SimpleNamespace(Tk=lambda: object()))
    observed = []
    def app(*args, **kwargs):
        observed.append(args)
        raise RuntimeError("constructor observed")
    monkeypatch.setattr(gui, "LauncherApp", app)
    with pytest.raises(RuntimeError, match="constructor observed"):
        gui.main(["--p2-content", "content folder", "seed.json", "--server", "host:1"])
    assert observed[0][1:] == ("seed.json", "host:1", "content folder", None)


@pytest.mark.parametrize("explicit,saved", [
    ("folder", "manifest"), ("manifest", "folder"),
    ("both", "folder"), (None, "both"), (None, "manifest"),
])
def test_actual_gui_constructor_resolves_explicit_and_saved_choices(tmp_path, monkeypatch, explicit, saved):
    from types import SimpleNamespace
    import sys
    monkeypatch.syspath_prepend(str(ROOT / "launcher"))
    spec = importlib.util.spec_from_file_location("p2_gui_switch", ROOT / "launcher/gui.py")
    gui = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gui)
    folder = tmp_path / "prepared folder"
    folder.mkdir()
    document = tmp_path / "content manifest.json"
    document.write_text("{}")
    config = {}
    if saved in ("folder", "both"):
        config["p2_content"] = str(folder)
    if saved in ("manifest", "both"):
        config["p2_content_manifest"] = str(document)
    monkeypatch.setattr(gui.launcher, "load_config", lambda: config)
    # Keep the real constructor and selection/resolver; only UI surfaces are doubles.
    class Variable:
        def __init__(self): self.value = ""
        def set(self, value): self.value = value
        def get(self): return self.value
    def build(app):
        for name in ("source_var", "server_var", "p2_content_var", "p2_manifest_var"):
            setattr(app, name, Variable())
    monkeypatch.setattr(gui.LauncherApp, "build", build)
    monkeypatch.setattr(gui.LauncherApp, "style", lambda app: None)
    monkeypatch.setattr(gui.LauncherApp, "refresh_source_status", lambda app: None)
    monkeypatch.setattr(gui.LauncherApp, "set_seed", lambda app, path: None)
    monkeypatch.setitem(sys.modules, "tkinter", SimpleNamespace(ttk=object()))
    root = SimpleNamespace(**{name: lambda *args, **kwargs: None
                              for name in ("title", "configure", "minsize", "geometry", "after")})
    explicit_folder = str(folder) if explicit in ("folder", "both") else None
    explicit_manifest = str(document) if explicit in ("manifest", "both") else None
    app = gui.LauncherApp(root, p2_content=explicit_folder, content_manifest=explicit_manifest)
    values = app.p2_content_var.get(), app.p2_manifest_var.get()
    if explicit == "both":
        assert values == (str(folder), str(document))
        with pytest.raises(gui.launcher.LaunchError, match="either"):
            gui.launcher.resolve_p2_content(P2, {}, *values)
    elif explicit == "manifest" or (explicit is None and saved == "manifest"):
        assert values == ("", str(document))
        assert gui.launcher.resolve_p2_content(P2, {}, *values) == (None, str(document))
    else:
        assert values == (str(folder), "")
        assert gui.launcher.resolve_p2_content(P2, {}, *values) == (str(folder), None)
    assert gui.launcher.resolve_p2_content({}, {}, *values) == (None, None)
