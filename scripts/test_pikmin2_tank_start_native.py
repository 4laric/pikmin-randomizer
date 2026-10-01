"""Run the private one-Start queue case or identical no-edge control."""
import argparse,json,os
from pathlib import Path
from scripts.test_pikmin2_tank_gx_native import run
from experimental.pikmin2_tank_start_diagnostic import analyze_start

def run_case(args):
    previous=os.environ.pop('TANK_DIAG_START',None)
    if args.case=='start':os.environ['TANK_DIAG_START']='1'
    try:report=run(args)
    finally:
        os.environ.pop('TANK_DIAG_START',None)
        if previous is not None:os.environ['TANK_DIAG_START']=previous
    text=(Path(report['directory'])/'host.log').read_text(errors='replace')
    report['case']=args.case;report['start_evidence']=analyze_start(text,args.case=='start')
    (args.output/'start-result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('assets','profile','exe','output'):p.add_argument('--'+key,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--case',choices=('start','control'),required=True);p.add_argument('--timeout',type=int,default=120);args=p.parse_args();args.mode='absent'
    if not 1<=args.timeout<=120:p.error('timeout must be 1..120')
    run_case(args)
