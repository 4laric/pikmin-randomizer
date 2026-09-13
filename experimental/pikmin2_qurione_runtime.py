"""Private native Honeywisp observer and labeled attack-receiver stimulus."""
from experimental.pikmin2_kochappy_arena_fixture import instrument as red_observer

def instrument(source):
    s=red_observer(source).replace('pc_p2_kochappy','pc_p2_qurione').replace('P2_RED','P2_QURIONE').replace('red-arena','qurione-arena').replace('TEKI_Chappy','TEKI_Qurione').replace('186001','203001').replace('186002','203002')
    s=s.replace('name && actor->mHealth==200 && actor->getParameterF(TPF_Life)==200','name && actor->mHealth==fallback && actor->getParameterF(TPF_Life)==fallback')
    s=s.replace('require(a->isAlive() && !a->mIsFrozen,"arena actor not live/unfrozen");','require(!a->mIsFrozen,"arena actor frozen");')
    marker='        Iterator e(tekiMgr);CI_LOOP(e){Teki* a=static_cast<Teki*>(*e);if(!a->mGenerator)continue;'
    addition=r'''        static Teki* proxy=nullptr;
        if(!proxy){Iterator find(tekiMgr);CI_LOOP(find){Teki* a=static_cast<Teki*>(*find);if(a->mGenerator && a->mGenerator->_70==203001)proxy=a;}require(proxy,"proxy missing");}
        if(observed==1){Vector3f point=proxy->getPosition()+Vector3f(70,0,50);point.y=mapMgr->getMinY(point.x,point.z,true);n->resetPosition(point);}
        if(observed==20){InteractAttack attack(n,nullptr,1.f,false);bool accepted=proxy->stimulate(attack);std::printf("P2_QURIONE_STIMULUS tick=%d injected_attack_receiver=1 accepted=%d\n",observed,int(accepted));}
        Creature* nectar=proxy->getCreaturePointer(2);
        std::printf("P2_QURIONE_REWARD tick=%d state=%d nectar=%d type=%d\n",observed,proxy->mStateID,int(nectar!=nullptr),nectar?nectar->mObjType:-1);
'''
    if s.count(marker)!=1:raise ValueError('Observer anchor changed')
    return '#include "Interactions.h"\n'+s.replace(marker,addition+marker)


def evidence(log, exit_code):
    import re
    rows=[dict((k,float(v)) for k,v in re.findall(r'(\w+)=([-+\d.eE]+)',line)) for line in log.splitlines() if line.startswith('P2_QURIONE_ARENA_TICK ')]
    births=[line for line in log.splitlines() if line.startswith('P2_QURIONE_ARENA_BIRTH ')]
    return dict(exit_code=exit_code,completed=exit_code==0 and 'PASS P2_QURIONE_ARENA observation' in log,
        births=len(births),registered_draw='P2_QURIONE_DRAW corpse=0' in log,
        counter_values={str(i):len({r['frame'] for r in rows if r.get('id')==i}) for i in (203001,203002)},
        attack_accepted='injected_attack_receiver=1 accepted=1' in log,
        nectar_pointer=any('nectar=1' in line for line in log.splitlines() if line.startswith('P2_QURIONE_REWARD ')),
        material_fidelity='unaccepted: first capture white silhouette',P2_Egg='unimplemented',
        stimulus='Injected InteractAttack receiver; not player throw collision')
