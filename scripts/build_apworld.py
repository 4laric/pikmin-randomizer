"""Package original standalone Python code only; no native or game assets."""
from pathlib import Path
import argparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def build(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("__init__.py", "options.py", "archipelago.json"):
            archive.write(ROOT / "apworld/pikmin_randomizer" / name, "pikmin_randomizer/" + name)
        archive.writestr("pikmin_randomizer/core/__init__.py", "")
        for name in ("catalog.py", "seed.py", "stats.py", "obstacles.py", "enemies.py", "benefits.py", "enemy_slots.py", "spawn_data.py", "campaign_data.py", "campaign_enemies.py", "p2_placement.py", "p2_placement_catalog.py"):
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
    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT / "output/pikmin_randomizer.apworld")
    print(build(parser.parse_args().output))
