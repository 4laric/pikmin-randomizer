"""Source-only Purple earthquake/Fit reference; not a native stun implementation."""
import argparse
import hashlib
import json
import math
from pathlib import Path

SOURCES={
 'enemy_base':'src/plugProjectYamashitaU/enemyBase.cpp',
 'interactions':'src/plugProjectYamashitaU/enemyInteractBattle.cpp',
 'kochappy':'src/plugProjectYamashitaU/KochappyBase.cpp',
 'piki':'src/plugProjectKandoU/pikiState.cpp',
 'parameters':'include/Game/EnemyParmsBase.h',
}


def finite(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Expected finite number')
    return value


def fit_after_landing(*,steps,grounded,dead,timer,roll,chance=.3,bitter_queued=False,no_interrupt=False):
    finite(timer);finite(roll);finite(chance)
    if type(steps)is not int or steps<0 or timer<0 or not 0<=roll<=1 or not 0<=chance<=1:raise ValueError('Invalid earthquake input')
    if dead and grounded:return 'living'
    if steps<=3 or not grounded:return 'earthquake'
    return 'fit' if timer>0 or (roll<chance and not bitter_queued and not no_interrupt) else 'living'


def fit_tick(timer,dt,duration,*,dead=False,bitter_queued=False):
    for value in (timer,dt,duration):finite(value)
    if timer<0 or dt<0 or duration<=0:raise ValueError('Invalid fit timer')
    elapsed=timer+dt
    return (0.,'living') if elapsed>duration or dead or bitter_queued else (elapsed,'fit')


def bounce_speed(factor,roll):
    finite(factor);finite(roll)
    if not 0<=roll<=1:raise ValueError('Invalid random roll')
    return factor*200+roll*100


def extract(reference,research,output):
    profile=json.loads(reference.read_text())
    if profile.get('next_species')!='Kochappy':raise ValueError('Expected audited Kochappy profile')
    expected={'Kochappy':(1,10.),'BlueKochappy':(44,5.),'YellowKochappy':(45,5.)}
    variants={}
    for name,(identity,duration) in expected.items():
        v=profile['variants'][name];g=v['parameters']['general']
        if v['source_id']!=identity or (g['fp36'],g['fp37'],g['fp38'])!=(50.,.3,duration):raise ValueError('Unexpected retail stun profile')
        variants[name]=dict(source_id=identity,hipdrop_fallback_damage=g['fp36'],fit_probability=g['fp37'],fit_duration_seconds=g['fp38'])
    texts={name:(research/path).read_text(encoding="utf-8") for name,path in SOURCES.items()}
    anchors={'enemy_base':['mStunAnimTimer += sys->mDeltaTime','mStunAnimTimer > enemy->getParms().mPurplePikiStunDuration','++mEarthquakeStepTimer > 3','mCurrentVelocity.y = yVelocityScale * 200.0f + randFloat() * 100.0f'],
      'interactions':['enemy->pressCallBack(mCreature, mDamage, mCollPart)','enemy->hipdropCallBack(mCreature, mDamage, mCollPart)'],
      'kochappy':['mFsm->transit(this, KOCHAPPY_Press, nullptr)'],
      'piki':['mPoundAOERange.mValue','InteractEarthquake earthquake(piki, 1.0f)'],
      'parameters':["mPurplePikiStunDuration(this, 'fp38'"]}
    for name,required in anchors.items():
        if any(a not in texts[name] for a in required):raise ValueError('Source receiver changed: '+name)
    result=dict(schema=1,scope='reference only; no runtime/native installation',profile_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),variants=variants,sources={k:dict(path=v,sha256=hashlib.sha256((research/v).read_bytes()).hexdigest()) for k,v in SOURCES.items()},semantics=['Direct hipdrop calls press first; Kochappy accepts live nonbitter Piki press, so generic50damage fallback is not automatically applied','Earthquake tests grounded/alive/nonflying/unconstrained/notbitter/interruption guards','After more than3 updates and ground contact: retained positive stun timer or random roll strictly below chance enters Fit','Fit uses elapsed delta time and exits strictly after duration, or on death/bitter queued','Repeated earthquake while timer positive resumes Fit without resetting accumulated timer'],unresolved=['PoundAOERange numeric retail value not extracted here','native P1 death/damage processing while immobilized','complete P2 press and lifecycle FSM parity'])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','research','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(extract(a.reference,a.research,a.output),indent=2))
