"""Package original standalone Python code only; no native or game assets."""
from pathlib import Path
import argparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def build(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("__init__.py", "archipelago.json"):
            archive.write(ROOT / "apworld/pikmin_randomizer" / name, "pikmin_randomizer/" + name)
        archive.writestr("pikmin_randomizer/core/__init__.py", "")
        for name in ("catalog.py", "seed.py", "stats.py", "obstacles.py", "enemies.py", "benefits.py", "enemy_slots.py", "spawn_data.py", "campaign_data.py", "campaign_enemies.py"):
            archive.write(ROOT / "randomizer" / name, "pikmin_randomizer/core/" + name)
    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT / "output/pikmin_randomizer.apworld")
    print(build(parser.parse_args().output))
