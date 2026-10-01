import hashlib
import json
from pathlib import Path
import struct

import pytest

from experimental.pikmin2_purple_flight_arena import stage
from scripts.preview_pikmin2_room import records


def test_missing_presentation_does_not_create_arena(tmp_path):
    with pytest.raises(FileNotFoundError):
        stage(tmp_path / 'assets', tmp_path / 'converted', tmp_path / 'missing', tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_local_fresh_arena_preserves_source_and_has_live_squad(tmp_path):
    assets = Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets')
    converted = Path('output/pikmin2-room105')
    presentation = Path('output/p2-purple-direct393/run-adult-02')
    if not all(path.exists() for path in (assets, converted, presentation)):
        pytest.skip('Requires private user-owned presentation assets')
    source_gen = assets / 'dataDir/stages/chal0/default.gen'
    before = hashlib.sha256(source_gen.read_bytes()).hexdigest()
    run = stage(assets, converted, presentation, tmp_path / 'arenas')
    assert hashlib.sha256(source_gen.read_bytes()).hexdigest() == before
    rows = records(run / 'assets/dataDir/stages/chal0/default.gen')
    assert len([row for row in rows if row[72:76] == b'ikip']) == 20
    enemy = next(row for row in rows if row[72:76] == b'iket')
    assert enemy[80] == 4
    assert struct.unpack_from('<I', enemy, 8)[0] == 385875968
    assert (run / 'p2-purple-flight.txt').read_bytes() == b'P2_PURPLE_FLIGHT_1\n'
    report = json.loads((run / 'purple-flight-arena.json').read_text())
    assert report['starting_red_records'] == 20
    assert report['birth_area_override']['fixture_radius'] == 0
