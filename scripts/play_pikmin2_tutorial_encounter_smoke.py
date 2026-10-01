"""User-operated original tutorial Red/Onion smoke; no automatic gameplay."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.run_pikmin2_tutorial_encounter import main

if __name__ == "__main__":
    if any(word == "--mode" or word.startswith("--mode=") for word in sys.argv[1:]):
        raise SystemExit("Use run_pikmin2_tutorial_encounter.py for explicit automated modes")
    raise SystemExit(main(["--mode", "human", *sys.argv[1:]]))
