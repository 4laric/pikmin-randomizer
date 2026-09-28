"""Create an isolated Snow Bulborb / Pod preview using existing engineering layout."""
import argparse
import struct
import subprocess
from pathlib import Path
from scripts.preview_pikmin2_emergence import prepare
from scripts.preview_pikmin2_room import records
from experimental.pikmin2_enemy import install

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','imported','treasure','pod','snow','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--exe',type=Path)
    args=parser.parse_args()
    run=prepare(args.assets.resolve(),args.imported.resolve(),args.treasure.resolve(),args.output.resolve(),pod=args.pod.resolve())
    entries=records(run/'assets/dataDir/stages/chal0/default.gen')
    # Native Generator::readID loads these ID bytes little-endian on PC.
    ids=[struct.unpack_from('<I',entry,8)[0] for entry in entries if entry[72:76]==b'iket']
    install(args.snow.resolve(),run,ids)
    print(run,flush=True)
    if args.exe:
        with (run/'native.log').open('w') as log:
            result=subprocess.run([str(args.exe.resolve()),'--experimental-pikmin2-room'],cwd=run,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise SystemExit(f'Native exit {result.returncode}: {run / "native.log"}')
