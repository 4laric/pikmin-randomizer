"""Assert real logged native spawns match the all-family-swap test seed."""
from pathlib import Path
import re
import sys

def audit(directory, required):
    logs = list(Path(directory).glob('runs/*/native.log'))
    assert len(logs) == 1, logs
    rows = [tuple(map(int, m)) for m in re.findall(r'ENEMY_SPAWN original=(\d+) actual=(\d+) protected=(\d+)', logs[0].read_text(errors='replace'))]
    assert rows
    mapping = {3: 31, 31: 3, 4: 32, 32: 4, 18: 19, 19: 18}
    for original, actual, protected in rows:
        assert actual == (original if protected else mapping.get(original, original)), (original, actual, protected)
    assert required <= set(rows), required - set(rows)
    print(f'PASS {directory}: {len(rows)} native births; {sum(a != b for a,b,_ in rows)} replacements; protected spawns retained')

audit(sys.argv[1], {(3,31,0), (4,32,0), (18,19,0), (19,18,0), (3,3,1), (17,17,0)})
audit(sys.argv[2], {(32,4,0)})
