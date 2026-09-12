from itertools import combinations
from randomizer.obstacles import OBSTACLES


def test_save_rounding_cannot_alias_another_structure():
    for (name, a), (other, b) in combinations(OBSTACLES.items(), 2):
        if a[:2] == b[:2]:
            assert abs(a[2]-b[2]) > 2 or abs(a[3]-b[3]) > 2, (name, other)


def test_navel_bomb_walls_are_catalogued():
    walls = [row for name,row in OBSTACLES.items() if 'Forest Navel' in name and row[1] in (24,25)]
    assert len(walls) == 5
