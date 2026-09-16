"""Isolated Snow lifecycle fixture instrumentation and evidence validation."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import re


OBSERVER = r'''
        static unsigned snowGenerator=0;
        // Private fixture only: move the captain near the enemy for camera and
        // native attack observation before the inherited Pikmin combat test.
        if(enemy && phase==3 && ticks==1) {
            require(enemy->mGenerator!=nullptr,"missing live Snow generator");
            snowGenerator=enemy->mGenerator->_70;
            Vector3f position=enemy->mSRT.t-Vector3f(70,0,30);
            position.y=mapMgr->getMinY(position.x,position.z,true);
            n->resetPosition(position);
            std::puts("P2_SNOW_LIFECYCLE_SETUP captain_reposition=1 health_override=0 animation_override=0");
        }
        if(enemy && phase>=3) {
            static bool attack=false,death=false,carried=false;
            const int motion=phase<=5?enemy->mTekiAnimator->getCurrentMotionIndex():-1;
            const float counter=phase<=5?enemy->mTekiAnimator->getCounter():0;
            if(!attack && motion==TekiMotion::Attack && counter>2) {
                capture("snow-attack.ppm");attack=true;
                std::printf("P2_SNOW_LIFECYCLE stage=attack motion=%d frame=%.3f\n",motion,counter);
            }
            if(!death && motion==TekiMotion::Dead && counter>2) {
                capture("snow-death.ppm");death=true;
                std::printf("P2_SNOW_LIFECYCLE stage=death motion=%d frame=%.3f\n",motion,counter);
            }
            if(corpse && phase==6 && corpseDistance>5 && !carried) {
                capture("snow-carried.ppm");carried=true;
                std::printf("P2_SNOW_LIFECYCLE stage=carried distance=%.3f state=%d\n",corpseDistance,corpse->getState());
            }
        }
'''


def instrument(source):
    anchor='        if(phase==0) {'
    if source.count(anchor)!=1 or 'P2_SNOW_LIFECYCLE_SETUP' in source:
        raise ValueError('Unexpected or already-instrumented room fixture')
    source=source.replace(anchor,OBSERVER+'\n'+anchor)
    delivery='require(corpseReachedGoal && corpseDistance>(assembled?1000:100),'
    if source.count(delivery)!=1:
        raise ValueError('Missing native corpse delivery assertion')
    replay='''const int credited=pc_p2_preview_pokos();
                // The native pellet has cleared its view after delivery. Replay
                // the persisted identity through the economy, not a dead actor.
                P2Economy replay;replay.load("p2-economy.txt");
                const std::string identity="corpse:"+std::to_string(snowGenerator);
                require(!replay.credit(identity,2) && replay.total()==credited,"duplicate receipt changed persistent economy");
                require(pc_p2_preview_pokos()==credited && playerState->getCurrParts()==repairs,"duplicate corpse credit/repairs changed");
                std::printf("P2_SNOW_LIFECYCLE stage=duplicate_credit pokos=%d repairs=%d\\n",credited,repairs);
                '''
    return '#include "pc_p2_economy.h"\n#include "Generator.h"\n'+source.replace(delivery,replay+delivery)


def prepare(assets, converted, pod, snow, output):
    """One Snow, 20 native Pikmin and source Citrus/Pod in the concrete test room."""
    from scripts.preview_pikmin2_room import prepare as room, records
    from experimental.pikmin2_enemy import install
    run=room(assets,converted,output)
    private=run/'assets/dataDir/courses/pikmin2room'
    for name in ('pod.mod','treasure.mod'):
        (private/name).write_bytes((pod/name).read_bytes())
    (run/'p2-pod.txt').write_bytes((pod/'p2-pod.txt').read_bytes())
    ids=[struct.unpack_from('<I',entry,8)[0] for entry in records(run/'assets/dataDir/stages/chal0/default.gen') if entry[72:76]==b'iket']
    if len(ids)!=1:raise ValueError('Expected one native Snow scaffold actor')
    install(snow,run,ids)
    return run


def evidence(log, exit_code, ledger=None, executable_sha256=None, expected_sha256=None):
    required={
        'live_draw':'P2_SNOW_DRAW corpse=0',
        'attack':'P2_SNOW_LIFECYCLE stage=attack',
        'death':'P2_SNOW_LIFECYCLE stage=death',
        'corpse_draw':'P2_SNOW_DRAW corpse=1',
        'carried':'P2_SNOW_LIFECYCLE stage=carried',
        'combat':'P2_FIXTURE_COMBAT_PASS',
        'native_delivery':'PASS p2 room: actors, ground, controller movement, native carry delivery, unchanged repairs, native combat kill, far corpse transport and delivery',
    }
    found={name:marker in log for name,marker in required.items()}
    found['duplicate_credit']=bool(re.search(r'P2_SNOW_LIFECYCLE stage=duplicate_credit pokos=182\s+repairs=\d+\b',log))
    receipts={}
    ledger_valid=False
    if ledger:
        lines=ledger.splitlines()
        try:
            if lines.pop(0)!='P2_ECONOMY_1':raise ValueError()
            for line in lines:
                identity,value=line.split()
                if identity in receipts:raise ValueError()
                receipts[identity]=int(value)
            ledger_valid=(receipts.get('treasure:dia_a_red')==180 and len(receipts)==2 and
                          sum(value for identity,value in receipts.items() if identity.startswith('corpse:'))==2)
        except (ValueError,IndexError):ledger_valid=False
    found['ledger_exact']=ledger_valid
    found['binary_identity']=bool(expected_sha256 and re.fullmatch('[0-9a-f]{64}',expected_sha256) and executable_sha256==expected_sha256)
    return {'schema':1,'exit_code':exit_code,'stages':found,
            'passed':exit_code==0 and all(found.values()),
            'missing':[name for name,ok in found.items() if not ok],
            'scope':'P1 combat and carrying with Snow visuals; fixture assigns actions and repositions captain. No P2 FSM parity claim.'}


def run_test(assets,converted,pod,snow,exe,output,seconds=180):
    from experimental.pikmin2_animation_profile import capture_command
    expected=hashlib.sha256(exe.read_bytes()).hexdigest()
    output.mkdir(parents=True,exist_ok=False)
    run=prepare(assets,converted,pod,snow,output/'prepared')
    (output/'run.txt').write_text(str(run))
    metadata=capture_command([str(exe.resolve()),'--experimental-pikmin2-room'],run,output/'capture',seconds)
    ledger=run/'p2-economy.txt'
    result=evidence((output/'capture/native.log').read_text(errors='replace'),metadata['exit_code'],
                    ledger.read_text() if ledger.exists() else None,metadata['executable_sha256'],expected)
    result['expected_executable_sha256']=expected
    result['run']=str(run)
    (output/'evidence.json').write_text(json.dumps(result,indent=2))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='mode',required=True)
    patch=commands.add_parser('instrument')
    patch.add_argument('--native',type=Path,required=True)
    patch.add_argument('--output',type=Path,required=True)
    run=commands.add_parser('run')
    for name in ('assets','converted','pod','snow','exe','output'):
        run.add_argument('--'+name,type=Path,required=True)
    run.add_argument('--seconds',type=float,default=180)
    args=parser.parse_args()
    if args.mode=='run':
        result=run_test(*(getattr(args,key).resolve() for key in ('assets','converted','pod','snow','exe','output')),args.seconds)
        print(json.dumps(result,indent=2))
        if not result['passed']:raise SystemExit(1)
        return
    args.output.mkdir(parents=True,exist_ok=False)
    source=args.native/'tools/preview_p2_room.cpp'
    for path in (args.native/'tools').glob('preview_p2_*.inc'):
        (args.output/path.name).write_bytes(path.read_bytes())
    (args.output/source.name).write_text(instrument(source.read_text()))
    (args.output/'source.json').write_text(json.dumps({'source':str(source.resolve()),
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()},indent=2))
    print(args.output/source.name)


if __name__=='__main__':main()
