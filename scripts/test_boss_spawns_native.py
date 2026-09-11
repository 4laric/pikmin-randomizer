"""Boot each area and verify the vanilla Spider restriction with real generators."""
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.test_native_startup import main
p=argparse.ArgumentParser()
for n in ('exe','assets','output'): p.add_argument('--'+n, type=Path, required=True)
p.add_argument('--areas', nargs='+', default=['forest','navel','spring','impact','trial'])
a=p.parse_args()
for area in a.areas:
    out=a.output / area
    main(a.exe,a.assets,out,starting_area=area,seed='boss-spawns-'+area,starting_color='red',all_areas=True,enemy_shuffle=True,collection_checks=True,starting_flarlic=1,permanent_checks=True)
    logs=list(out.glob('runs/*/native.log')); assert len(logs)==1
    data=logs[0].read_text(encoding='utf-8',errors='replace')
    rows=[(int(t),int(ok)) for t,ok in re.findall(r'BOSS_SPAWN type=(\d+) success=(\d+)',data)]
    # Native Candypops legitimately skip birth when their Onion is locked.
    assert rows and all(ok or t == 5 for t,ok in rows), (area,rows)
    assert sum(t==0 for t,_ in rows)==(1 if area=='navel' else 0), (area,rows)
    print('PASS boss births',area,rows,flush=True)
