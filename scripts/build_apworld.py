"""Package original standalone Python code only; no native or game assets."""
from pathlib import Path
import argparse
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

def build(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("__init__.py", "options.py", "archipelago.json"):
            archive.write(ROOT / "apworld/pikmin_randomizer" / name, "pikmin_randomizer/" + name)
        archive.writestr("pikmin_randomizer/core/__init__.py", "")
        for name in ("catalog.py", "seed.py", "stats.py", "obstacles.py", "enemies.py", "benefits.py", "enemy_slots.py", "spawn_data.py", "campaign_data.py", "campaign_enemies.py", "p2_placement.py", "p2_placement_catalog.py", "enemy_catalog.py"):
            source = (ROOT / "randomizer" / name).read_text(encoding="utf-8")
            source = source.replace("from experimental.", "from ..experimental.")
            archive.writestr("pikmin_randomizer/core/" + name, source)
        # Keep experimental imports private to the world. No checkout or globally
        # installed `randomizer`/`experimental` package is needed by the AP server.
        archive.writestr("pikmin_randomizer/experimental/__init__.py", "")
        for name in ("pikmin2_enemy_roster.py", "pikmin2_seed_bridge.py"):
            source = (ROOT / "experimental" / name).read_text(encoding="utf-8")
            source = source.replace("from experimental.", "from .")
            source = source.replace("from randomizer.", "from ..core.")
            source = source.replace("from randomizer import", "from ..core import")
            if name == "pikmin2_enemy_roster.py":
                # Traversable resources work both inside the .apworld zip and
                # when AP extracts it. Bundled evidence is a pinned snapshot.
                source = source.replace("from pathlib import Path", "from pathlib import Path\nfrom importlib.resources import files")
                source = source.replace('REPO_ROOT / "docs" / "PIKMIN2_ENEMY_ROSTER.json"',
                                        'files(__package__).joinpath("data/PIKMIN2_ENEMY_ROSTER.json")')
                source = source.replace('REPO_ROOT / "docs" / "PIKMIN2_ENEMY_ROSTER_EVIDENCE.json"',
                                        'files(__package__).joinpath("data/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json")')
            archive.writestr("pikmin_randomizer/experimental/" + name, source)
        for name in ("PIKMIN2_ENEMY_ROSTER.json", "PIKMIN2_ENEMY_ROSTER_EVIDENCE.json"):
            archive.write(ROOT / "docs" / name, "pikmin_randomizer/experimental/data/" + name)
        archive.write(ROOT / "docs/PIKMIN2_ADMITTED_PLACEMENT.json",
                      "pikmin_randomizer/core/data/PIKMIN2_ADMITTED_PLACEMENT.json")
        # The proxy tier's stage-A sibling is loaded fail-closed whenever a tier is
        # requested, so the `full` pool needs it inside the package too.
        archive.write(ROOT / "docs/PIKMIN2_PROXY_PLACEMENT.json",
                      "pikmin_randomizer/core/data/PIKMIN2_PROXY_PLACEMENT.json")
        # The `full` enemy pool (P2EnemyPool option_full) resolves through
        # randomizer/p2_proxy at generation time, so the package must carry
        # the declarations and the roster snapshot they validate against --
        # otherwise p2_species='full' crashes inside the AP server with
        # ModuleNotFoundError. Rows are validated here: a bad declaration
        # fails the release build instead of shipping a broken pool.
        from randomizer.p2_proxy import load_rows as _load_proxy_rows
        proxy_rows = _load_proxy_rows()
        if not proxy_rows:
            raise ValueError("proxy declaration set is empty; refusing to package")
        proxy_source = (ROOT / "randomizer" / "p2_proxy" / "__init__.py").read_text(encoding="utf-8")
        proxy_source = proxy_source.replace("from experimental.", "from ..experimental.")
        proxy_source = proxy_source.replace("from pathlib import Path", "from pathlib import Path\nfrom importlib.resources import files")
        # Traversable resources work both inside the .apworld zip and when AP
        # extracts it; Path.glob/sorted without a key do not.
        proxy_source = proxy_source.replace(
            'REPO_ROOT = Path(__file__).resolve().parents[2]\nROSTER_PATH = REPO_ROOT / "docs" / "PIKMIN2_ENEMY_ROSTER.json"',
            'ROSTER_PATH = files(__package__).joinpath("data/PIKMIN2_ENEMY_ROSTER.json")')
        proxy_source = proxy_source.replace(
            "directory = Path(directory) if directory is not None else Path(__file__).parent",
            "directory = Path(directory) if directory is not None else files(__package__)")
        proxy_source = proxy_source.replace(
            "for path in sorted(directory.glob(\"*.json\")):",
            "for path in sorted(directory.glob(\"*.json\"), key=lambda item: item.name):")
        for marker in ("REPO_ROOT", "Path(__file__).parent",
                       'sorted(directory.glob("*.json")):'):
            if marker in proxy_source:
                raise ValueError(f"p2_proxy packaging rewrite missed: {marker}")
        archive.writestr("pikmin_randomizer/core/p2_proxy/__init__.py", proxy_source)
        for row in proxy_rows:
            name = f"{row['source_id']}_{row['enum_name']}.json"
            archive.write(ROOT / "randomizer" / "p2_proxy" / name,
                          "pikmin_randomizer/core/p2_proxy/" + name)
        archive.write(ROOT / "docs/PIKMIN2_ENEMY_ROSTER.json",
                      "pikmin_randomizer/core/p2_proxy/data/PIKMIN2_ENEMY_ROSTER.json")
    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT / "output/pikmin_randomizer.apworld")
    print(build(parser.parse_args().output))
