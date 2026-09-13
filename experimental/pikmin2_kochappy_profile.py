"""Retail dwarf-Bulborb reference profiles and Dwarf Red assets; no native install."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from experimental.pikmin2_assets import archive_files,disc_files
from experimental.pikmin2_enemy import replace_texture_zero
from experimental.pikmin2_snow_policy import animation_events,parameter_groups

VARIANTS={
    'Kochappy':(1,'Dwarf Red Bulborb','kochappy_body_s3tc.1.bti'),
    'BlueKochappy':(44,'Dwarf Orange Bulborb','kochappy_body_s3tc.3.bti'),
    'YellowKochappy':(45,'Snow Bulborb','kochappy_body_s3tc.2.bti'),
}
FIELDS={
    'health':('fp00','mHealth','health'),
    'move_speed':('fp06','mMoveSpeed','world_units_per_second'),
    'turn_gain':('fp08','mTurnSpeed','fraction_per_update'),
    'maximum_turn':('fp28','mMaxTurnAngle','degrees_per_update'),
    'attack_entry_range':('fp20','mMaxAttackRange','world_units'),
    'attack_entry_half_angle':('fp21','mMaxAttackAngle','degrees'),
    'purple_stun_duration':('fp38','mPurplePikiStunDuration','seconds'),
}
GROUPS=('creature','general','proper')
CLIPS={'attack.bca','dead.bca','flick.bca','move1.bca','type1.bca','type5.bca','wait1.bca','waitact1.bca','waitact2.bca'}
EXPECTED={
    'Kochappy':(200,50,10),
    'BlueKochappy':(250,60,5),
    'YellowKochappy':(150,50,5),
}


def profiles(parameters):
    """Strict revision-bounded profiles while retaining every raw source field."""
    if set(parameters)!=set(VARIANTS):raise ValueError('Expected all three source identities')
    result={}
    for species,groups in parameters.items():
        if len(groups)!=3 or any(not isinstance(g,dict) or not g for g in groups):raise ValueError('Expected three nonempty parameter groups')
        if any(not isinstance(k,str) or type(v) not in (float,int) or not math.isfinite(v) for g in groups for k,v in g.items()):raise ValueError('Invalid/nonfinite parameter')
        try:values={name:groups[1][key] for name,(key,_,_) in FIELDS.items()}
        except KeyError as error:raise ValueError('Missing required general parameter') from error
        if (values['health'],values['move_speed'],values['purple_stun_duration'])!=EXPECTED[species]:raise ValueError('Unsupported retail variant profile')
        if (values['turn_gain'],values['maximum_turn'],values['attack_entry_range'],values['attack_entry_half_angle'])!=(.4,10,30,20):raise ValueError('Unsupported shared steering/attack profile')
        identity,name,texture=VARIANTS[species]
        result[species]={'source_id':identity,'display_name':name,'source_species':species,
                         'shared_model':'Kochappy','shared_animation':'Kochappy','source_fsm':'KochappyBase::FSM',
                         'texture_path':f'enemy/data/{species}/{texture}','texture_slot':0,
                         'parameters':dict(zip(GROUPS,groups)),
                         'profile':{name:{'value':value,'source_group':'general','source_key':FIELDS[name][0],'source_member':FIELDS[name][1],'unit':FIELDS[name][2]} for name,value in values.items()}}
    snow=result['YellowKochappy']['parameters']
    for variant in result.values():
        delta=[]
        for group in GROUPS:
            current=variant['parameters'][group]
            for key in sorted(set(current)|set(snow[group])):
                if current.get(key)!=snow[group].get(key):delta.append({'group':group,'key':key,'snow':snow[group].get(key),'variant':current.get(key)})
        variant['differences_from_snow']=delta
    return result


def audit_source(research):
    """Verify resource/class/parameter mappings against the local source revision."""
    hashes={}
    def read(path):
        data=(research/path).read_bytes();hashes[path]=hashlib.sha256(data).hexdigest();return data.decode('utf-8')
    ids=read('include/Game/enemyInfo.h');info=read('src/plugProjectYamashitaU/enemyInfo.cpp')
    parms=read('include/Game/EnemyParmsBase.h');base=read('include/Game/Entities/KochappyBase.h')
    manager=read('src/plugProjectYamashitaU/kochappyBaseMgr.cpp')
    if 'KochappyBase::FSM' not in base and 'struct FSM : public EnemyStateMachine' not in base:raise ValueError('Missing shared FSM declaration')
    for species,(identity,_,texture) in VARIANTS.items():
        if not re.search(r'EnemyID_'+species+r'\s*=\s*'+str(identity)+r'\s*,',ids):raise ValueError('Enemy source ID mismatch')
        cpp=read(f'src/plugProjectYamashitaU/{species.lower()}.cpp')
        mgr=read(f'src/plugProjectYamashitaU/{species.lower()}Mgr.cpp')
        if any(token not in cpp for token in ('new KochappyBase::ProperAnimator','setFSM(new KochappyBase::FSM)','changeImage(texture, 0)')):raise ValueError('Variant behavior/material contract changed')
        if f'/enemy/data/{species}/{texture}' not in mgr or 'init(new KochappyBase::Parms)' not in mgr:raise ValueError('Variant resource contract changed')
        if f'EnemyID_{species}' not in manager or f'"{species}"' not in info:raise ValueError('Missing shared resource source entry')
    for key,member,_ in FIELDS.values():
        if not re.search(re.escape(member)+r"\(this, '"+key+r"'",parms):raise ValueError('Parameter source member mismatch: '+member)
    read('src/plugProjectYamashitaU/kochappyState.cpp')
    read('src/plugProjectYamashitaU/enemyBase.cpp')
    return hashes


def extract(iso,research,output):
    source_hashes=audit_source(research);catalog=disc_files(iso);hashes={}
    with iso.open('rb') as stream:
        def read(path):
            offset,size=catalog[path];stream.seek(offset);data=stream.read(size)
            if len(data)!=size:raise ValueError('Truncated disc asset')
            hashes[path]=hashlib.sha256(data).hexdigest();return data
        parm_archive=archive_files(read('enemy/parm/enemyParms.szs'))
        parameters={}
        for species in VARIANTS:
            path=species.lower()+'/enemyparm.txt';data=parm_archive[path];hashes[path]=hashlib.sha256(data).hexdigest()
            parameters[species]=parameter_groups(data.decode('shift_jis'))
        variants=profiles(parameters)
        animation_path='kochappy/enemyanimmgr.txt';animation=parm_archive[animation_path]
        hashes[animation_path]=hashlib.sha256(animation).hexdigest();events=animation_events(animation.decode('shift_jis'))
        models=archive_files(read('enemy/data/Kochappy/model.szs'));motions=archive_files(read('enemy/data/Kochappy/anim.szs'))
        if set(events)!=CLIPS or set(events)!=set(motions):raise ValueError('Source animation files and event catalog disagree')
        textures={species:read(profile['texture_path']) for species,profile in variants.items()}
    red_model=replace_texture_zero(models['enemy.bmd'],textures['Kochappy'])
    # Keep all exported content private; these are source assets, not a runtime bank.
    output.mkdir(parents=True,exist_ok=False);(output/'source-animation').mkdir()
    (output/'dwarf-red.bmd').write_bytes(red_model)
    (output/'dwarf-red.bti').write_bytes(textures['Kochappy'])
    for name,data in motions.items():(output/'source-animation'/name).write_bytes(data)
    result={'schema':1,'family':'KochappyBase','next_species':'Kochappy','source_scope':'US GPVE01 revision 0 audited local assets',
            'variants':variants,'source_sha256':hashes,'research_sha256':source_hashes,
            'shared_animation_events':events,'shared_animation_sha256':{name:hashlib.sha256(data).hexdigest() for name,data in motions.items()},
            'exported_model_sha256':hashlib.sha256(red_model).hexdigest(),'source_model_sha256':hashlib.sha256(models['enemy.bmd']).hexdigest(),
            'cost':{'exported_model_bytes':len(red_model),'source_animation_bytes':sum(map(len,motions.values())),'sampled_pose_count':0,'native_runtime_cost':'unmeasured'},
            'runtime_status':'Reference extraction only; no native actors, visual bank, parameter hooks or placements installed.',
            'placement_contract':'Separate arena generator binding and full effective XYZ; no source yaw applied here.',
            'unimplemented':['Kochappy native visual/profile binding','source Purple stun reaction','source event timing/FSM parity','natural arena lifecycle and corpse delivery']}
    (output/'kochappy-profile.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','research','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=extract(args.iso,args.research,args.output)
    print(json.dumps({'next_species':result['next_species'],'variants':{name:v['differences_from_snow'] for name,v in result['variants'].items()},'cost':result['cost']},indent=2))
