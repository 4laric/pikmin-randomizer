import copy
from pathlib import Path
import pytest
from experimental.pikmin2_kochappy_profile import EXPECTED,FIELDS,VARIANTS,audit_source,profiles


def parameters():
    return {name:[{'fp00':1},{'fp00':h,'fp06':speed,'fp08':.4,'fp28':10,'fp20':30,'fp21':20,'fp38':stun},{'fp01':2,'fp02':300,'fp03':180}] for name,(h,speed,stun) in EXPECTED.items()}


def test_variant_identity_and_complete_delta():
    result=profiles(parameters())
    assert result['Kochappy']['source_id']==1
    assert result['BlueKochappy']['source_id']==44
    assert result['YellowKochappy']['source_id']==45
    assert result['Kochappy']['texture_path'].endswith('Kochappy/kochappy_body_s3tc.1.bti')
    assert [(r['key'],r['variant']) for r in result['Kochappy']['differences_from_snow']]==[('fp00',200),('fp38',10)]
    assert [(r['key'],r['variant']) for r in result['BlueKochappy']['differences_from_snow']]==[('fp00',250),('fp06',60)]
    assert result['YellowKochappy']['differences_from_snow']==[]
    assert result['Kochappy']['profile']['attack_entry_range']['source_member']=='mMaxAttackRange'
    assert result['Kochappy']['profile']['purple_stun_duration']['unit']=='seconds'


def test_unknown_raw_difference_is_preserved():
    data=parameters();data['Kochappy'][0]['fp99']=7
    assert {'group':'creature','key':'fp99','snow':None,'variant':7} in profiles(data)['Kochappy']['differences_from_snow']


@pytest.mark.parametrize('bad',['identity','missing','nan','infinity','boolean','health','speed','turn','groups','empty'])
def test_invalid_profile(bad):
    data=parameters()
    if bad=='identity':data['Unknown']=data.pop('Kochappy')
    elif bad=='missing':del data['Kochappy'][1]['fp20']
    elif bad in ('nan','infinity','boolean'):data['Kochappy'][1]['fp99']={'nan':float('nan'),'infinity':float('inf'),'boolean':True}[bad]
    elif bad=='groups':data['Kochappy'].pop()
    elif bad=='empty':data['Kochappy'][0]={}
    else:data['Kochappy'][1][{'health':'fp00','speed':'fp06','turn':'fp08'}[bad]]=123
    with pytest.raises(ValueError):profiles(data)


def source_tree(tmp_path):
    def write(path,text):
        p=tmp_path/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    write('include/Game/enemyInfo.h','\n'.join(f'EnemyID_{s} = {i},' for s,(i,_,_) in VARIANTS.items()))
    write('src/plugProjectYamashitaU/enemyInfo.cpp',' '.join(f'"{s}"' for s in VARIANTS))
    write('include/Game/EnemyParmsBase.h','\n'.join(f"{member}(this, '{key}'" for key,member,_ in FIELDS.values()))
    write('include/Game/Entities/KochappyBase.h','struct FSM : public EnemyStateMachine')
    write('src/plugProjectYamashitaU/kochappyBaseMgr.cpp',' '.join('EnemyID_'+s for s in VARIANTS))
    for species,(_,_,texture) in VARIANTS.items():
        write(f'src/plugProjectYamashitaU/{species.lower()}.cpp','new KochappyBase::ProperAnimator; setFSM(new KochappyBase::FSM); changeImage(texture, 0)')
        write(f'src/plugProjectYamashitaU/{species.lower()}Mgr.cpp',f'/enemy/data/{species}/{texture}; init(new KochappyBase::Parms)')
    for name in ('kochappyState.cpp','enemyBase.cpp'):write('src/plugProjectYamashitaU/'+name,'source reference')


def test_source_audit_hashes_and_parameter_member(tmp_path):
    source_tree(tmp_path);result=audit_source(tmp_path)
    assert len(result)==13 and all(len(value)==64 for value in result.values())
    p=tmp_path/'include/Game/EnemyParmsBase.h';p.write_text(p.read_text().replace('mMaxAttackRange','mAttackRadius'))
    with pytest.raises(ValueError,match='source member'):audit_source(tmp_path)


@pytest.mark.parametrize('field',['id','texture','fsm'])
def test_source_drift_fails_closed(tmp_path,field):
    source_tree(tmp_path)
    if field=='id':p=tmp_path/'include/Game/enemyInfo.h';old,new='= 1,','= 2,'
    elif field=='texture':p=tmp_path/'src/plugProjectYamashitaU/kochappyMgr.cpp';old,new='.1.bti','.2.bti'
    else:p=tmp_path/'src/plugProjectYamashitaU/kochappy.cpp';old,new='new KochappyBase::FSM','new Other::FSM'
    p.write_text(p.read_text().replace(old,new))
    with pytest.raises(ValueError):audit_source(tmp_path)
