"""Pose density measurement and the dense-cache policy (#970)."""
import json

from scripts import p2_content_density as density


def _clip(root, enum, stem, count, sub=""):
    d = root / enum / sub if sub else root / enum
    d.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (d / f"{stem}_{i:02d}.mod").write_bytes(b"x")


def test_content_density_counts_poses_per_clip(tmp_path):
    _clip(tmp_path, "Kabuto", "cannon_Bomb_hit_loop", 24, "Bomb")
    _clip(tmp_path, "Kabuto", "cannon_Bomb_fly", 12, "Bomb")
    _clip(tmp_path, "Kurage", "kurage_idle", 1)
    (tmp_path / "Kabuto" / "enemy.mod").write_bytes(b"x")  # not a pose
    rows = density.content_density(tmp_path)
    assert rows["Kabuto"] == {"clips": 2, "min": 12, "median": 18, "max": 24, "total": 36}
    assert rows["Kurage"]["max"] == 1
    assert "| Kabuto | 2 | 12 | 18 | 24 | 36 |" in density.markdown_table(rows)


def test_entry_density_from_marker_or_root(tmp_path):
    (tmp_path / "A").mkdir()
    (tmp_path / "B").mkdir()
    assert not density.entry_is_dense(tmp_path, "A")
    density.write_entry_marker(tmp_path / "A", 12)
    assert not density.entry_is_dense(tmp_path, "A")
    density.write_entry_marker(tmp_path / "A", 24)
    assert density.entry_is_dense(tmp_path, "A")
    (tmp_path / "prepared.json").write_text(json.dumps({"pose_limit": 24, "extracted_enums": ["B"]}))
    assert density.entry_is_dense(tmp_path, "B") and density.root_pose_limit(tmp_path) == 24
