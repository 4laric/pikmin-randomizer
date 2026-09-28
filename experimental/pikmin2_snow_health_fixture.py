"""Private native health probe; uses fresh production objects, never edits native source."""
import argparse
import hashlib
import json
from pathlib import Path

PROBE = r'''
            const float fallback=enemy->mTekiParams->getF(TPF_Life);
            const bool opted=std::ifstream("p2-snow-policy.txt").good();
            const float snowExpected=opted?150.f:fallback;
            require(enemy->mHealth==snowExpected && enemy->getParameterF(TPF_Life)==snowExpected,"Snow initial/max health mismatch");
            std::printf("P2_HEALTH initial=%.1f max=%.1f fallback=%.1f opted=%d\n",enemy->mHealth,enemy->getParameterF(TPF_Life),fallback,int(opted));
            Teki* ordinary=tekiMgr->newTeki(TEKI_Chappy);
            require(ordinary && ordinary!=enemy,"ordinary probe birth failed"); ordinary->reset();
            require(ordinary->getParameterF(TPF_Life)==ordinary->mTekiParams->getF(TPF_Life),"ordinary P1 max changed");
            require(ordinary->mHealth==ordinary->mTekiParams->getF(TPF_Life),"ordinary P1 initial changed");
            require(!pc_p2_enemy_name(static_cast<PelletView*>(ordinary)),"ordinary actor inherited Snow identity");
            std::puts("P2_HEALTH ordinary=pass");
            pc_p2_snow_forget(enemy);
            require(enemy->getParameterF(TPF_Life)==fallback && !pc_p2_enemy_name(static_cast<PelletView*>(enemy)),"forget retained Snow registration");
            std::puts("P2_HEALTH forget=pass");
            pc_p2_snow_setup();
            require(enemy->getParameterF(TPF_Life)==snowExpected && enemy->mHealth==snowExpected,"setup reload health mismatch");
            require(ordinary->getParameterF(TPF_Life)==ordinary->mTekiParams->getF(TPF_Life),"reload registered ordinary actor");
            std::puts("P2_HEALTH reload=pass");
            if(enemy->removable()) {
                tekiMgr->kill(enemy);
                Teki* reused=tekiMgr->newTeki(TEKI_Chappy);
                require(reused==enemy,"fixture did not reuse expected native slot");
                require(reused->getParameterF(TPF_Life)==fallback && !pc_p2_enemy_name(static_cast<PelletView*>(reused)),"native slot retained Snow policy");
                reused->reset();require(reused->mHealth==fallback,"reused actor initial health changed");
                std::puts("P2_HEALTH slot_reuse=pass");
            } else std::puts("P2_HEALTH slot_reuse=unmeasured actor_not_removable");
            pc_p2_snow_reset();
            require(enemy->getParameterF(TPF_Life)==fallback && !pc_p2_enemy_name(static_cast<PelletView*>(enemy)),"reset retained Snow registration");
            std::puts("P2_HEALTH reset=pass");
            std::puts("PASS p2 Snow health probe");std::fflush(stdout);std::_Exit(0);
'''


def instrument(source):
    anchor='            float points[][2]='
    if source.count(anchor)!=1 or 'P2_HEALTH' in source:
        raise ValueError('Unexpected room fixture source')
    return '#include <fstream>\n#include "pc_p2_enemy.h"\n'+source.replace(anchor,PROBE+'\n'+anchor)


def evidence(log,code,expected_policy):
    import re
    match=re.search(r'P2_HEALTH initial=([\d.]+) max=([\d.]+) fallback=([\d.]+) opted=([01])',log)
    checks={name:f'P2_HEALTH {name}=pass' in log for name in ('ordinary','forget','reload','reset')}
    checks['health']=False
    if match:
        initial,maximum,fallback=map(float,match.groups()[:3]);opted=match[4]=='1'
        checks['health']=opted==expected_policy and initial==maximum==(150 if opted else fallback)
    checks['completion']='PASS p2 Snow health probe' in log
    return {'passed':code==0 and all(checks.values()),'exit_code':code,'checks':checks,
            'slot_reuse':'P2_HEALTH slot_reuse=pass' in log,
            'unmeasured':(['actual manager slot reuse'] if 'P2_HEALTH slot_reuse=pass' not in log else [])+['corpse query','scene-manager reconstruction'],
            'scope':'Real live actor query and explicit registry lifecycle APIs; no P2 AI parity claim.'}


def run(assets,converted,pod,snow,policy,exe,output,seconds=60,lifecycle=False):
    from experimental.pikmin2_snow_lifecycle import prepare
    from experimental.pikmin2_snow_policy import install
    from experimental.pikmin2_animation_profile import capture_command
    output.mkdir(parents=True,exist_ok=False)
    stage=prepare(assets,converted,pod,snow,output/'prepared')
    if policy:install(policy,stage)
    metadata=capture_command([str(exe.resolve()),'--experimental-pikmin2-room'],stage,output/'capture',seconds)
    log=(output/'capture/native.log').read_text(errors='replace')
    if lifecycle:
        from experimental.pikmin2_snow_lifecycle import evidence as lifecycle_evidence
        ledger=stage/'p2-economy.txt'
        result=lifecycle_evidence(log,metadata['exit_code'],ledger.read_text() if ledger.exists() else None,
                                 metadata.get('executable_sha256'),hashlib.sha256(exe.read_bytes()).hexdigest())
        result['corpse_health']=('P2_HEALTH corpse=pass max=150.0 opted=1' in log) if policy else ('P2_HEALTH corpse=pass' in log)
        result['passed'] &= result['corpse_health']
    else:
        result=evidence(log,metadata['exit_code'],policy is not None)
    result['executable_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
    result['capture_sha256']=metadata.get('executable_sha256')
    result['passed'] &= result['executable_sha256']==result['capture_sha256']
    (output/'evidence.json').write_text(json.dumps(result,indent=2))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    patch=sub.add_parser('instrument');patch.add_argument('--source',type=Path,required=True);patch.add_argument('--output',type=Path,required=True)
    execute=sub.add_parser('run')
    for name in ('assets','converted','pod','snow','exe','output'):execute.add_argument('--'+name,type=Path,required=True)
    execute.add_argument('--policy',type=Path)
    execute.add_argument('--lifecycle',action='store_true')
    execute.add_argument('--seconds',type=int,default=60)
    patch.add_argument('--lifecycle',action='store_true')
    args=parser.parse_args()
    if args.command=='instrument':
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x') as stream:stream.write((instrument_lifecycle if args.lifecycle else instrument)(args.source.read_text()))
    else:
        result=run(args.assets,args.converted,args.pod,args.snow,args.policy,args.exe,args.output,args.seconds,args.lifecycle)
        print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)



# Separate long-running fixture: keep ordinary combat/carrying intact and only
# query the still-allocated corpse actor while its PelletView remains attached.
def instrument_lifecycle(source):
    from experimental.pikmin2_snow_lifecycle import instrument as lifecycle
    source=lifecycle(source)
    anchor='        static unsigned snowGenerator=0;'
    observer=r'''
        if(enemy && corpse && phase==6 && corpse->mPelletView==static_cast<PelletView*>(enemy)) {
            static bool verified=false;
            if(!verified) {
                const bool opted=std::ifstream("p2-snow-policy.txt").good();
                const float snowExpected=opted?150.f:enemy->mTekiParams->getF(TPF_Life);
                require(enemy->getParameterF(TPF_Life)==snowExpected,"corpse lost maximum health policy");
                require(pc_p2_enemy_name(static_cast<PelletView*>(enemy))!=nullptr,"corpse lost Snow identity");
                std::printf("P2_HEALTH corpse=pass max=%.1f opted=%d\n",enemy->getParameterF(TPF_Life),int(opted));
                verified=true;
            }
        }
'''
    return '#include <fstream>\n#include "pc_p2_enemy.h"\n'+source.replace(anchor,observer+anchor)




if __name__=='__main__':main()
