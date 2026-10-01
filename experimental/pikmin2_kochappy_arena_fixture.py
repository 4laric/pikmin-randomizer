"""Original P1-map observer; no enemy state, target or animation injection."""
import json
import re
from pathlib import Path

APP=r'''class RoomApp : public PlugPikiApp {
    int frames=0,observed=0;
public:
    int idle() override {
        int result=PlugPikiApp::idle();require(++frames<10000,"arena timeout");
        if(frames%120==0){std::printf("P2_RED_ARENA_GATE frame=%d ready=%d navi=%d teki=%d pause=%d ui=%d movie=%d\n",frames,int(pc_p2_preview_cargo_free_ready()),int(naviMgr!=nullptr),int(tekiMgr!=nullptr),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive));std::fflush(stdout);}

        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(!pc_p2_preview_cargo_free_ready() || !naviMgr || !tekiMgr)return result;
        Navi* n=naviMgr->getNavi();if(!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive)return result;
        if(++observed==1){
            for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
            std::ifstream input("red-arena-positions.txt");unsigned id;float x,y,z;int expected=0;
            while(input>>id>>x>>y>>z){
                Teki* actor=nullptr;int matches=0;Iterator e(tekiMgr);CI_LOOP(e){Teki* a=static_cast<Teki*>(*e);if(a->mGenerator && a->mGenerator->_70==id){actor=a;++matches;}}
                require(matches==1 && actor->mTekiType==TEKI_Chappy,"arena identity count/type");
                Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();
                require(std::fabs(birth.x-x)<.02 && std::fabs(birth.y-y)<.02 && std::fabs(birth.z-z)<.02,"arena stored birth XYZ");
                require(std::fabs(gen.x-x)<.02 && std::fabs(gen.y-y)<.02 && std::fabs(gen.z-z)<.02,"arena generator XYZ");
                const char* name=pc_p2_kochappy_name(actor);float fallback=actor->mTekiParams->getF(TPF_Life);
                require(id==186001?(name && actor->mHealth==200 && actor->getParameterF(TPF_Life)==200):(!name && actor->mHealth==fallback && actor->getParameterF(TPF_Life)==fallback),"arena profile/control health");
                std::printf("P2_RED_ARENA_BIRTH id=%u x=%.3f y=%.3f z=%.3f health=%.1f fallback=%.1f red=%d\n",id,birth.x,birth.y,birth.z,actor->mHealth,fallback,int(name!=nullptr));++expected;
            }
            int count=0;Iterator all(tekiMgr);CI_LOOP(all){Teki* a=static_cast<Teki*>(*all);if(a->isAlive())++count;}
            require(expected==2 && count==2,"arena exact roster");
        }
        Iterator e(tekiMgr);CI_LOOP(e){Teki* a=static_cast<Teki*>(*e);if(!a->mGenerator)continue;unsigned id=a->mGenerator->_70;if(id!=186001 && id!=186002)continue;
            const Vector3f p=a->getPosition();
            std::printf("P2_RED_ARENA_TICK tick=%d id=%u state=%d motion=%d frame=%.4f x=%.4f y=%.4f z=%.4f target=%d frozen=%u\n",observed,id,a->mStateID,a->mTekiAnimator->getCurrentMotionIndex(),a->mTekiAnimator->getCounter(),p.x,p.y,p.z,int(a->getCreaturePointer(0)!=nullptr),a->mIsFrozen);
            require(a->isAlive() && !a->mIsFrozen,"arena actor not live/unfrozen");
        }
        if(observed==60)capture("red-arena.ppm");
        if(observed==240){std::puts("PASS P2_RED_ARENA observation");std::fflush(stdout);std::_Exit(0);}
        std::fflush(stdout);return result;
    }
};
'''


def instrument(source):
    start=source.index('class RoomApp : public PlugPikiApp {');end=source.index('int main(',start)
    if 'P2_RED_ARENA' in source:raise ValueError('Already instrumented')
    return '#include <fstream>\n#include "Generator.h"\n#include "pc_p2_kochappy.h"\n'+source[:start]+APP+source[end:]


def instrument_tutorial(source):
    create='static void createTutorialWindow(int textID, int ufoPartID, bool hasAudio)\n{'
    update='static void handleTutorialWindow(u32& result, Controller* controller)\n{'
    if source.count(create)!=1 or source.count(update)!=1:raise ValueError('Unexpected tutorial source')
    source=source.replace(create,create+'\n std::printf("P2_ARENA_TUTORIAL id=%d part=%d audio=%d\\n",textID,ufoPartID,int(hasAudio));std::fflush(stdout);')
    return '#include <cstdio>\n'+source.replace(update,update+'\n if(tutorialWindow){static unsigned pulse=0;controller->updateCont((++pulse%30)==0?KBBTN_A:0);if(pulse%30==0){std::puts("P2_ARENA_TUTORIAL_INPUT A");std::fflush(stdout);}}')


def positions(stage):
    manifest=json.loads((stage/'arena.json').read_text())
    if len(manifest['actors'])!=2:raise ValueError('Expected two actors')
    (stage/'red-arena-positions.txt').write_text(''.join(str(a['generator'])+' '+' '.join(map(str,a['position']))+'\n' for a in manifest['actors']))


def evidence(log,code):
    rows=[dict((k,float(v)) for k,v in re.findall(r'(\w+)=([-+\d.eE]+)',line)) for line in log.splitlines() if line.startswith('P2_RED_ARENA_TICK ')]
    births=[line for line in log.splitlines() if line.startswith('P2_RED_ARENA_BIRTH ')]
    checks={'completion':'PASS P2_RED_ARENA observation' in log,'birth_health':len(births)==2,'ticks':len(rows)==480,'render':'P2_KOCHAPPY_DRAW corpse=0' in log}
    checks['sequence']=all([r.get('tick') for r in rows if r.get('id')==i]==list(range(1,241)) for i in (186001,186002))
    checks['animation']=all(len({r.get('frame') for r in rows if r.get('id')==i})>2 for i in (186001,186002))
    gates=[line for line in log.splitlines() if line.startswith('P2_RED_ARENA_GATE ')]
    tutorial_ids=[int(v) for v in re.findall(r'P2_ARENA_TUTORIAL id=(\d+)',log)]
    return dict(tutorial_ids=tutorial_ids,startup_gates=gates,passed=code==0 and all(checks.values()),checks=checks,exit_code=code,observations=rows,scope='Unforced P1 proxy updates and animation; targeting/movement observed, not required or injected.',unmeasured=['combat','corpse delivery','reload','P2 FSM parity'])


def run(stage,exe,output,seconds=90):
    from experimental.pikmin2_animation_profile import capture_command
    import hashlib
    positions(stage)
    metadata=capture_command([str(exe.resolve()),'--experimental-pikmin2-room'],stage,output,seconds)
    result=evidence((output/'native.log').read_text(errors='replace'),metadata['exit_code'])
    result['capture']=metadata
    result['arena_sha256']=hashlib.sha256((stage/'arena.json').read_bytes()).hexdigest()
    (output/'evidence.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('stage','exe','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--seconds',type=float,default=90)
    a=p.parse_args();result=run(a.stage.resolve(),a.exe.resolve(),a.output.resolve(),a.seconds)
    print(json.dumps({k:v for k,v in result.items() if k!='observations'},indent=2))
