"""Observe the unresolved two-flower fixture without changing its inputs."""
import argparse
from pathlib import Path
from experimental.pikmin2_floor2_fixture import instrument as base_instrument
from scripts.build_pikmin2_fixture import build_fixture

ACCESS = r'''
#include "Collision.h"
// Explicit-instantiation member pointers provide read-only fixture access;
// no class layout, header access modifier or production method is changed.
template<class Tag,typename Tag::type Member>struct VioletRead { friend typename Tag::type field(Tag){return Member;} };
struct AiTag {using type=PomAi* Pom::*;friend type field(AiTag);};
struct PreviousTag {using type=int PomAi::*;friend type field(PreviousTag);};
struct ReleasedTag {using type=int PomAi::*;friend type field(ReleasedTag);};
struct MaximumTag {using type=int PomAi::*;friend type field(MaximumTag);};
struct AnimatorTag {using type=PaniTekiAnimator Boss::*;friend type field(AnimatorTag);};
template struct VioletRead<AiTag,&Pom::mPomAi>;
template struct VioletRead<PreviousTag,&PomAi::mPrevStickPikiCount>;
template struct VioletRead<ReleasedTag,&PomAi::mReleasedSeedCount>;
template struct VioletRead<MaximumTag,&PomAi::mMaxSeedCount>;
template struct VioletRead<AnimatorTag,&Boss::mAnimator>;
'''

PROBE = r'''
        if(timer%150==0){
            for(int i=0;i<2;++i){Pom* f=flowers[i];PomAi* ai=f->*field(AiTag{});
                auto& animator=f->*field(AnimatorTag{});
                std::printf("VIOLET_DIAG flower=%d state=%d alive=%d sticks=%d prev=%d released=%d max=%d walk=%.3f anim_speed=%.3f motion=%d frame=%.3f\n",i,f->getCurrentState(),int(f->isAlive()),f->getStickPikiCount(),ai->*field(PreviousTag{}),ai->*field(ReleasedTag{}),ai->*field(MaximumTag{}),f->getWalkTimer(),f->getAnimTimer(),animator.getCurrentMotionIndex(),animator.getCounter());
                CollPart* bound=f->mCollInfo->getBoundingSphere();CollPart* slot=f->mCollInfo->getSphere('slot');
                std::printf("VIOLET_COLL flower=%d atari=%d aiCullable=%d pos=%.1f,%.1f,%.1f rot=%.2f,%.2f,%.2f\n",i,int(f->isAtari()),int(f->aiCullable()),f->mSRT.t.x,f->mSRT.t.y,f->mSRT.t.z,f->mSRT.r.x,f->mSRT.r.y,f->mSRT.r.z);
                for(CollPart* part:{bound,slot,slot?slot->getChildAt(0):nullptr})if(part)std::printf("VIOLET_SPHERE flower=%d ptr=%p center=%.1f,%.1f,%.1f radius=%.1f stickable=%d\n",i,(void*)part,part->mCentre.x,part->mCentre.y,part->mCentre.z,part->mRadius,int(part->isStickable()));}
            for(size_t i=0;i<original.size();++i){Piki* p=original[i];Creature* stick=p->getStickObject();
                std::printf("VIOLET_PIKI index=%d alive=%d state=%d stick=%p stick_type=%d pos=%.1f,%.1f,%.1f\n",int(i),int(p->isAlive()),p->getState(),(void*)stick,stick?stick->mObjType:-1,p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z);}
        }
'''


def instrument(source):
    result=base_instrument(source)
    anchor='static void floorTwoFixture(Navi* n) {'
    call='        if(timer%150==0)std::printf("P2_FLOOR2_PROGRESS'
    if result.count(anchor)!=1 or result.count(call)!=1:raise ValueError('Diagnostic framing changed')
    return result.replace(anchor,ACCESS+'\n'+anchor).replace(call,PROBE+'\n'+call)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native','build','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--expected-head',required=True);a=p.parse_args()
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
    source=a.output/'violet_diagnostic.cpp';source.write_text(instrument((a.native/'tools/preview_p2_room.cpp').read_text()))
    print(build_fixture(a.build,a.native,source,a.output/'linked',a.expected_head)['status'])


if __name__=='__main__':main()
