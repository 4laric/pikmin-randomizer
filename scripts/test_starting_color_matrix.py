"""Hidden native startup matrix; does not establish full breeding/route acceptance."""
import argparse
from pathlib import Path
from test_native_startup import main
from randomizer.seed import generate


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('exe', 'assets', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    for area in ('impact', 'spring', 'trial', 'forest', 'navel'):
        for color in ('red', 'yellow', 'blue'):
            seed = next(str(i) for i in range(100) if generate(str(i), starting_color='random')['starting_color'] == color)
            print(f'Testing {area}/{color}', flush=True)
            main(a.exe, a.assets, (a.output / f'{area}-{color}').resolve(), True, area, seed, 'random', True)
