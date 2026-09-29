"""Roster rfix (#871): bare --p2-enemies fails clean, playable path works.

38 admitted identities exceed the 35-slot committed target set, so
``randomizer generate --p2-enemies`` without ``--p2-species`` fails closed in
the bridge. The CLI must report that as a clean actionable error (exit 2),
never an uncaught traceback. Fails on the pre-fix ``__main__`` (the
SeedBridgeError propagates instead of SystemExit).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run_main(monkeypatch, capsys, argv):
    from randomizer import __main__ as cli

    monkeypatch.setattr(sys, "argv", argv)
    try:
        cli.main()
    except SystemExit as exc:
        out = capsys.readouterr()
        return exc.code, out
    return 0, capsys.readouterr()


def test_bare_p2_enemies_succeeds(monkeypatch, capsys, tmp_path):
    # #888: roster admission equals the pool, so the bare flag no longer
    # fails closed on admitted-but-unplaceable identities.
    out_file = tmp_path / "seed.json"
    code, out = run_main(
        monkeypatch, capsys,
        ["randomizer", "generate", "--seed", "x", "--p2-enemies",
         "--output", str(out_file)])
    assert code == 0
    assert "Traceback" not in out.err
    assert out_file.exists()


def test_playable_product_path_succeeds(monkeypatch, capsys, tmp_path):
    out_file = tmp_path / "seed.json"
    code, _ = run_main(
        monkeypatch, capsys,
        ["randomizer", "generate", "--seed", "rfix-check", "--p2-enemies",
         "--p2-species", "playable", "--output", str(out_file)])
    assert code == 0
    manifest = json.loads(out_file.read_text(encoding="utf-8"))
    # 35 ordinary slots plus the Crawbster's one boss-arena binding (#899).
    assert len(manifest["p2_layout"]["bindings"]) == 36
    assert [row["source_id"] for row in manifest["p2_layout"]["boss_arenas"]["placed"]] == [94]
