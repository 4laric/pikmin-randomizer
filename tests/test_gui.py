"""Launcher window smoke: builds the widgets, renders a seed card and validates Play preconditions without launching."""
import importlib.util
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "launcher"))
try:
    import tkinter
except ImportError:  # pragma: no cover
    tkinter = None


def load_gui():
    spec = importlib.util.spec_from_file_location("gui", ROOT / "launcher" / "gui.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def root(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    if tkinter is None:
        pytest.skip("tkinter unavailable")
    try:
        window = tkinter.Tk()
    except tkinter.TclError as exc:
        pytest.skip(f"no display: {exc}")
    window.withdraw()
    yield window
    window.destroy()


def test_window_builds_and_shows_seed_card(root, tmp_path):
    import json
    from randomizer.seed import generate
    gui = load_gui()
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps(generate("gui-test", "ap", death_link=True, starting_area="navel", starting_color="blue")), encoding="utf-8")
    app = gui.LauncherApp(root, str(seed), "example.org:38281")
    root.update()
    assert app.manifest["slot"] == "Player1"
    texts = [app.card.itemcget(item, "text") for item in app.card.find_all() if app.card.type(item) == "text"]
    assert any("Forest Navel" in t and "blue Pikmin" in t and "DeathLink ×10" in t for t in texts)
    assert app.ap.winfo_manager() == "pack"  # AP panel is shown for AP seeds.
    assert app.server_var.get() == "example.org:38281"
    app.source_var.set(str(tmp_path / "Pikmin.iso"))
    root.update()
    assert "does not exist" in app.source_status.cget("text")
    (tmp_path / "Pikmin.iso").write_bytes(b"GPIE01")
    app.refresh_source_status()
    assert "first Play extracts" in app.source_status.cget("text")


def test_play_reports_missing_inputs_without_launching(root, tmp_path, monkeypatch):
    gui = load_gui()
    app = gui.LauncherApp(root)
    started = []
    monkeypatch.setattr(app, "run", lambda *a: started.append(a))
    app.play()
    log = app.log.get("1.0", "end")
    assert "Choose a seed file first" in log and not started
    app.seed_var.set(str(tmp_path / "nope.json"))
    app.play()
    assert "Choose a seed file first" in app.log.get("1.0", "end")
    assert app.play_button.instate(["!disabled"])

def test_new_solo_button_creates_and_selects_run(root, monkeypatch):
    gui = load_gui()
    app = gui.LauncherApp(root)
    monkeypatch.setattr("tkinter.simpledialog.askstring", lambda *a, **kw: "")
    app.new_solo_button.invoke()
    root.update()
    assert app.manifest["mode"] == "solo"
    assert Path(app.seed_var.get()).is_file()
    assert app.play_button.cget("text") == "Play solo"
    assert not app.ap.winfo_manager()
    assert gui.launcher.load_config()["seed"] == app.seed_var.get()


def test_invalid_seed_hides_ap_connection(root, tmp_path):
    import json
    from randomizer.seed import generate
    gui = load_gui()
    seed = tmp_path / "ap.json"
    seed.write_text(json.dumps(generate("ap", "ap")))
    app = gui.LauncherApp(root, str(seed))
    assert app.play_button.cget("text") == "Connect & play"
    bad = tmp_path / "bad.json"
    bad.write_text("broken")
    app.set_seed(bad)
    root.update()
    assert not app.ap.winfo_manager()
    assert app.manifest is None

def test_installed_setup_is_collapsed_and_can_be_changed(root, tmp_path):
    gui = load_gui()
    assets = tmp_path / "assets"
    (assets / "dataDir" / "stages").mkdir(parents=True)
    gui.launcher.save_config({"assets": str(assets), "image": str(tmp_path / "missing.iso")})
    app = gui.LauncherApp(root)
    root.update()
    assert app.source_var.get() == str(assets)
    assert app.installed_row.winfo_manager() == "grid"
    assert not app.source_status.winfo_manager()
    app.change_setup()
    root.update()
    assert app.source_status.winfo_manager() == "grid"
    assert not app.installed_row.winfo_manager()

def test_reconnect_sends_credentials_only_through_pipe(root):
    import io
    import json
    from types import SimpleNamespace
    gui = load_gui()
    app = gui.LauncherApp(root)
    pipe = io.StringIO()
    app.process = SimpleNamespace(stdin=pipe, poll=lambda: None)
    app.server_var.set("localhost:38281")
    app.password_var.set("private password")
    app.reconnect()
    assert json.loads(pipe.getvalue()) == {"server": "localhost:38281", "password": "private password"}
    assert "private password" not in gui.launcher.config_path().read_text()
    assert "private password" not in app.log.get("1.0", "end")
