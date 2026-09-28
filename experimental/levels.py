"""Distinct destination identity, separate from reused native area IDs."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Level:
    key: str
    name: str
    area_id: int
    stage_file: str
    layout: str

AREAS = (("impact", "The Impact Site", "practice"),
         ("forest", "The Forest of Hope", "stage1"),
         ("navel", "The Forest Navel", "stage2"),
         ("spring", "The Distant Spring", "stage3"),
         ("trial", "The Final Trial", "last"))
LEVELS = tuple(Level(f"{layout}:{key}", name + (" — Challenge" if layout == "challenge" else ""),
                     index, f"stages/{'chal'+str(index) if layout == 'challenge' else source}.ini", layout)
               for layout in ("campaign", "challenge")
               for index, (key, name, source) in enumerate(AREAS))
BY_KEY = {level.key: level for level in LEVELS}
