"""Stage and supervise the explicit original RGB trajectory fixture for60seconds."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

SOURCE_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE_ROOT))
from scripts.stage_pikmin2_full_surface import prepare
from scripts.run_pikmin2_fixture import launch
WORKSPACE=SOURCE_ROOT.parent.parent if SOURCE_ROOT.parent.name=='output' else SOURCE_ROOT
IDENTITY='c8598f04bb884ab396d126b8dfbed6a6ce78d2f6afc92e7b366a5e5c11ccc8d5'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,required=True)
    parser.add_argument('--expected-exe-sha256',required=True)
    parser.add_argument('--assets',type=Path,default=Path(os.environ.get('APPDATA',Path.home()))/'PikminRandomizer/game-data/assets')
    parser.add_argument('--bundle',type=Path,default=WORKSPACE/'output/p2-level-imports/tutorial-09')
    parser.add_argument('--captain-down',action='store_true')
    args=parser.parse_args()
    exe=args.exe.resolve(strict=True)
    if hashlib.sha256(exe.read_bytes()).hexdigest()!=args.expected_exe_sha256.lower():
        parser.error('Executable differs from the supplied reviewed fixture hash')
    output=WORKSPACE/'output/p2-yellow-1263'/('check-'+uuid.uuid4().hex)
    run=prepare(args.assets.resolve(),args.bundle.resolve(),IDENTITY,output)
    for key in list(os.environ):
        if key.upper().startswith(('PIKMIN_','P2_','BBFT_','NECTAR_')):
            del os.environ[key]
    config=run/'private-config';config.mkdir()
    save=run/'private-save';save.mkdir()
    os.environ.update(PIKMIN_SETTINGS_PATH=str(config/'pikmin-settings.ini'),NECTAR_SAVE_DIR=str(save))
    marker='P2_FIXTURE_CAPTAIN_DOWN' if args.captain_down else 'PASS ORIGINAL_YELLOW_THROW'
    if args.captain_down:os.environ['P2_YELLOW_FORCE_CAPTAIN_DOWN']='1'
    print('Explicitly staged19Red/1Yellow body; ordinary controller throw, not original acquisition/campaign/save proof.')
    print('Fresh evidence:',run,flush=True)
    result=launch(exe,run,['--experimental-pikmin2-surface','tutorial'],[marker],timeout=60,
                  canonical_root=WORKSPACE,development_launch=os.name!='nt')
    print(json.dumps(result,indent=2))
    if args.captain_down:
        text=(run/'native.log').read_text(encoding='utf-8',errors='replace') if (run/'native.log').exists() else ''
        expected=result.get('exit_code')==86 and marker in text and 'PASS ' not in text
        (run/'negative-assessment.json').write_text(json.dumps({'expected_stop':expected},indent=2)+'\n')
        return 0 if expected else 1
    return 0 if result.get('passed') else 1


if __name__=='__main__':
    raise SystemExit(main())
