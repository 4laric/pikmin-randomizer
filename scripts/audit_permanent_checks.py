"""Compare all-area hidden startup observations with the immutable obstacle catalog."""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.obstacles import OBSTACLES

rows = set()
for arg in sys.argv[1:]:
    for log in Path(arg).glob('runs/*/native.log'):
        rows.update(tuple(map(int, row)) for row in re.findall(
            r'OBSTACLE_INSTANCE stage=(\d+) kind=(\d+) x=(-?\d+) z=(-?\d+) complete=\d+',
            log.read_text(errors='replace')))
assert rows == set(OBSTACLES.values()), {'missing': set(OBSTACLES.values())-rows, 'unknown': rows-set(OBSTACLES.values())}
print(f'PASS: all {len(rows)} mapped permanent structures observed across five areas')
