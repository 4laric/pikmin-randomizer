"""Private Uji proxy registration/death/receipt regression fixture generator."""
from pathlib import Path
import argparse,json,os,subprocess

HOOK = r'''
#include "pc_p2_sheargrub.h"
static bool ujiFixture(Navi* n) {
    static int ticks=0,step=0,repairs=0;static Teki* bugs[2]={};static Pellet* bodies[2]={};
    if(++ticks>5000)require(false,"Uji fixture timeout");
    if(step==0){ phase=2;
        Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);const char* name=pc_p2_sheargrub_name(static_cast<PelletView*>(t));if(!name)continue;int index=std::string(name)=="UjiA"?0:1;require(!bugs[index],"duplicate Uji species");bugs[index]=t;}
        require(bugs[0]&&bugs[1],"missing Uji pair");repairs=playerState->getCurrParts();require(pc_p2_preview_pokos()==0,"dirty Uji ledger");
        for(int i=0;i<2;++i){unsigned generator;int value;require(pc_p2_sheargrub_receipt(bugs[i],generator,value)&&value==i+1,"source corpse mapping");bugs[i]->mSRT.t=n->mSRT.t+Vector3f(70+i*60,0,40);bugs[i]->mSRT.t.y=mapMgr->getMinY(bugs[i]->mSRT.t.x,bugs[i]->mSRT.t.z,true);}
        std::puts("P2_UJI_PAIR registered=2 source_values=1,2 synthetic_placement=1 proxy=P1");step=1;ticks=0;
    }else if(step==1&&ticks==60){capture("uji-live.ppm");for(auto* bug:bugs)bug->mHealth=0;step=2;ticks=0;}
    else if(step==2){
        Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);for(int i=0;i<2;++i)if(p->isAlive()&&p->mPelletView==static_cast<PelletView*>(bugs[i]))bodies[i]=p;}
        if(bodies[0]&&bodies[1]){capture("uji-corpses.ppm");int index=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(!v->isAlive())continue;v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Transport;v->mActiveAction->mChildActions[PikiAction::Transport].initialise(bodies[index++%2]);v->mMode=PikiMode::TransportMode;}require(index>=4,"insufficient Uji carriers");std::puts("P2_UJI_CORPSES real_transport_assigned=1 corpse_relocation=0");step=3;ticks=0;}
    }else if(step==3&&pc_p2_preview_pokos()==3){
        require(playerState->getCurrParts()==repairs,"Uji repairs changed");
        // Duplicate economy replay is asserted inside the private valid delivery callback; corpse pointers may already be recycled.
        require(pc_p2_preview_pokos()==3,"duplicate Uji credit");
        for(auto* bug:bugs){pc_p2_sheargrub_forget(bug);unsigned id;int value;require(!pc_p2_sheargrub_name(bug)&&!pc_p2_sheargrub_receipt(bug,id,value),"forgotten actor retains registration");}
        capture("uji-delivered.ppm");std::puts("PASS Uji proxy: both identities, live/corpse captures, native corpse delivery3, duplicate0, repairs unchanged, forget fallback");std::fflush(stdout);std::_Exit(0);
    }
    std::fflush(stdout);return true;
}
'''


def instrument(source):
    anchor='class RoomApp : public PlugPikiApp {';call='        if(cargoCarryFixture(n))return result;'
    if source.count(anchor)!=1 or source.count(call)!=1:raise ValueError('Room fixture framing changed')
    return source.replace(anchor,HOOK+'\n'+anchor).replace(call,'        if(ujiFixture(n))return result;\n'+call)


def build(native,recipe,output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False);source=output/'uji_fixture.cpp';source.write_text(instrument((native/'tools/preview_p2_room.cpp').read_text()))
    commands=json.loads(recipe.read_text())
    preview=(native/'pc_port/pc_p2_preview.cpp').read_text()
    anchor='        bool added=economy.credit(receipt,value);'
    if preview.count(anchor)!=1:raise ValueError('Preview economy framing changed')
    preview=preview.replace(anchor,anchor+'\n        if(added && receipt.find("uji:")!=std::string::npos){int total=economy.total();if(economy.credit(receipt,value)||economy.total()!=total)std::abort();std::printf("P2_UJI_DUPLICATE id=%s value=%d duplicate_credit=0\\n",receipt.c_str(),value);}')
    preview_source=output/'uji_preview.cpp';preview_source.write_text(preview)
    preview_object=output/'uji_preview.obj'
    compile_preview=[str(preview_source) if item.replace('\\','/').split('/')[-1]=='preview_p2_room.cpp' else str(preview_object) if item.replace('\\','/').split('/')[-1]=='preview_p2_room.obj' else item for item in commands['compile']]
    env=dict(os.environ);env['PATH']=str(Path(compile_preview[0]).parent)+os.pathsep+env.get('PATH','')
    with (output/'preview-compile.log').open('w') as log:result=subprocess.run(compile_preview,cwd=commands['cwd'],env=env,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError('Private preview compile failed')
    for kind in ('compile','link'):
        args=[]
        for item in commands[kind]:
            name=item.replace('\\','/').split('/')[-1]
            item=str(source) if name=='preview_p2_room.cpp' else str(output/'uji_fixture.obj') if name=='preview_p2_room.obj' else str(output/'uji_fixture.exe') if name=='preview_p2_room.exe' else item
            if kind=='link' and name=='pc_p2_preview.cpp.obj':item=str(preview_object)
            args.append(item)
        if kind=='compile':args.insert(1,'-I'+str(native/'tools'))
        if kind=='link' and not any('pc_p2_sheargrub.cpp.obj' in x.replace('\\','/') for x in args):
            candidate=Path(commands['cwd'])/'CMakeFiles/pikmin_pc.dir/pc_port/pc_p2_sheargrub.cpp.obj'
            if not candidate.exists():raise ValueError('Fresh Uji object missing; coordinate root build')
            args.insert(1,str(candidate))
        env=dict(os.environ);env['PATH']=str(Path(args[0]).parent)+os.pathsep+env.get('PATH','')
        with (output/(kind+'.log')).open('w') as log:r=subprocess.run(args,cwd=commands['cwd'],env=env,stdout=log,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError('Private '+kind+' failed')
    return output/'uji_fixture.exe'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(build(a.native.resolve(),a.recipe,a.output))

def validate(log):
    required=['P2_UJI_PAIR registered=2 source_values=1,2','P2_UJI_CORPSES real_transport_assigned=1 corpse_relocation=0','PASS Uji proxy:']
    if any(x not in log for x in required):raise ValueError('Incomplete Uji regression evidence')
    import re
    rows=re.findall(r'P2_POD_RECEIPT id=(corpse:[^ ]*uji:\d+) value=([12]) new=([01]) pokos=(\d+) seeds=0',log)
    identities={identity for identity,value,new,total in rows if new=='1'}
    if len(identities)!=2 or {value for identity,value,new,total in rows if new=='1'}!={'1','2'}:raise ValueError('Missing distinct natural source receipts')
    replay=set(re.findall(r'P2_UJI_DUPLICATE id=(corpse:[^ ]*uji:\d+) value=[12] duplicate_credit=0',log))
    if replay!=identities:raise ValueError('Missing duplicate receipt evidence')
    return {'identities':sorted(identities),'total_pokos':3,'duplicate_credit':0,'proxy_ai':'P1'}
