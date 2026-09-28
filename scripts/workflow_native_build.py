"""Build an already configured private native tree with canonical lease/evidence."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from workflow.registry import Registry
from workflow.native_build import execute

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--request',type=Path,required=True)
    a=p.parse_args()
    reg=Registry(a.root/'output/workflow/registry.sqlite3',a.root)
    result=execute(reg,**json.loads(a.request.read_text(encoding='utf-8-sig')))
    print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
