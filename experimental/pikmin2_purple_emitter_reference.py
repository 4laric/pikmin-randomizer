"""Retail Purple earthquake emission/filter contract; no native installation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from experimental.pikmin2_assets import disc_files

PATH='user/Abe/piki/pikiParms.txt'
SOURCES=('src/plugProjectKandoU/pikiState.cpp','src/plugProjectKandoU/cellIterator.cpp','include/Vector3.h','src/plugProjectYamashitaU/enemyInteractBattle.cpp','src/plugProjectYamashitaU/enemyBase.cpp','src/plugProjectYamashitaU/KochappyBase.cpp','include/Game/PikiParms.h')


def parameter(raw,key):
    values=re.findall(r'\{'+re.escape(key)+r'\}\s+4\s+(\S+)',raw.decode('shift_jis'))
    if len(values)!=1:raise ValueError('Missing/duplicate retail parameter '+key)
    value=float(values[0])
    if not math.isfinite(value) or value<0:raise ValueError('Invalid retail value')
    return value


def candidate(dx,dy,dz,bounding_radius,radius=60):
    values=(dx,dy,dz,bounding_radius,radius)
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in values) or min(bounding_radius,radius)<0:raise ValueError('Invalid sphere')
    return dx*dx+dz*dz <= (radius+bounding_radius)**2


def receiver(*,floor,alive=True,dead=False,flying=False,hard_constrained=False,bitter=False,no_interrupt=False,bitter_immune=False,birth_drop_waiting=False):
    return floor and alive and not any((dead,flying,hard_constrained,bitter,no_interrupt,bitter_immune,birth_drop_waiting))


def collision_order(initial_vy,after_hipdrop_vy,*,target_piki=False,target_enemy=True):
    if not all(math.isfinite(x) for x in (initial_vy,after_hipdrop_vy)):raise ValueError('Invalid vertical velocity')
    if target_piki:return []
    result=['impact_effects']
    if target_enemy:
        if initial_vy<0:result+=['hipdrop:press_first_then_fallback','earthquake']
        if after_hipdrop_vy<0:result+=['press_again']
    result+=['leave_hipdrop_if_still_active']
    return result


def extract(iso,research,output):
    offset,size=disc_files(iso)[PATH]
    with iso.open('rb') as stream:stream.seek(offset);raw=stream.read(size)
    radius=parameter(raw,'P017');damage=parameter(raw,'P022')
    if (radius,damage)!=(60.,20.):raise ValueError('Unexpected retail revision parameters')
    texts={p:(research/p).read_text(encoding='utf-8') for p in SOURCES}
    checks={SOURCES[0]:['mPoundAOERange.mValue','iterArg.mUseCustomRadius = 1','if (velocity.y < 0.0f)','if (velocity2.y < 0.0f)'],SOURCES[1]:['mArg.mSphere.mRadius + boundingSphere.mRadius','mObject->mPassID == mPassID'],SOURCES[2]:['return distance > radius;','pToCheck.sqrMagnitude2D()'],SOURCES[3]:['enemy->checkBirthTypeDropEarthquake()','enemy->pressCallBack(mCreature, mDamage, mCollPart)']}
    for path,anchors in checks.items():
        if any(a not in texts[path] for a in anchors):raise ValueError('Changed source contract '+path)
    report=dict(schema=1,scope='source reference, no native emitter',retail=dict(path=PATH,sha256=hashlib.sha256(raw).hexdigest(),pound_aoe_radius=radius,pound_damage=damage),sources={p:hashlib.sha256((research/p).read_bytes()).hexdigest() for p in SOURCES},filter='XZ squared distance <= (60 + target bounding radius)^2; vertical separation ignored; target position, not bounding-sphere center; deduplicated by iterator passID',eligibility=['DropEarthquake birth state transitions to Appear instead of normal earthquake','floor triangle','alive and not dead','not flying','not hard constrained','not bitter','not no-interrupt','not bitter-immune'],ordering=['descending enemy collision: Hipdrop dispatch first (press then fallback)','same branch emits Earthquake after Hipdrop','re-read vertical velocity then direct Press if still descending','leave HipDrop state if still active','ground/plat dosin emits earthquake then0.3s landing pause'],damage='Earthquake callback does not itself add damage. Retail direct pound passes20 to Hipdrop; Kochappy press may handle before generic enemy50 fallback.',not_implemented=['P2 homing/hipdrop state','native emitter/target-radius mapping','P1 flag equivalents','stun action preserving damage/death'])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','research','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(extract(a.iso,a.research,a.output),indent=2))
