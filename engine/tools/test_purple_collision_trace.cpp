#include "pc_purple_pose_envelope.h"
#include "pc_purple_collision_trace.h"
#include "pc_purple_sdl_axis_policy.h"
#include "pc_purple_dismiss_policy.h"
#include "pc_purple_save_budget.h"
#include "p2_purple_save_input.h"
#include <cstdlib>
#include <cstdio>
#include <limits>
#include <initializer_list>
static void check(bool ok, const char* why) { if (!ok) { std::fprintf(stderr,"FAIL %s\n",why);std::exit(1); } }
int main() {
    PcSaveUiSnapshot saveUi;
    saveUi.available=true;saveUi.outerMemoryRouted=true;saveUi.memoryAvailable=true;
    saveUi.failureAvailable=true;saveUi.failureInactive=true;saveUi.fileAvailable=true;
    saveUi.defaultFile.available=true;saveUi.defaultFile.successful=true;
    saveUi.defaultFile.typingComplete=true;saveUi.defaultFile.confirmationReady=true;
    check(saveUi.nestedUiBlocked && purple_save_input(true,{},PcDiaryAction::Unavailable,saveUi)==PurpleSaveInput::Confirm,
        "routed successful complete default-file prompt receives ordinary confirm while memory owns UI");
    for(bool PcSaveUiSnapshot::*gate : {&PcSaveUiSnapshot::available,&PcSaveUiSnapshot::outerMemoryRouted,
        &PcSaveUiSnapshot::memoryAvailable,&PcSaveUiSnapshot::failureAvailable,&PcSaveUiSnapshot::failureInactive,&PcSaveUiSnapshot::fileAvailable}) {
        PcSaveUiSnapshot blocked=saveUi;blocked.*gate=false;
        check(purple_save_input(true,{},PcDiaryAction::Unavailable,blocked)==PurpleSaveInput::Unexpected,
            "default-file prefix route gate cannot be omitted");
    }
    PcSaveUiSnapshot selected=saveUi;selected.fileSelection=true;
    check(purple_save_input(true,{},PcDiaryAction::Unavailable,selected)==PurpleSaveInput::Unexpected,"default-file cannot consume nested slot-selection input");
    PcSaveUiSnapshot typing=saveUi;typing.defaultFile.typingComplete=false;typing.defaultFile.confirmationReady=false;
    check(purple_save_input(true,{},PcDiaryAction::Unavailable,typing)==PurpleSaveInput::Neutral,"default-file text must finish naturally");
    PcSaveUiSnapshot failed=saveUi;failed.defaultFile.successful=false;
    check(purple_save_input(true,{},PcDiaryAction::Unavailable,failed)==PurpleSaveInput::Neutral,"failed creation cannot be confirmed as success");
    PcSaveUiSnapshot dormant=saveUi;dormant.defaultFile.available=false;
    check(purple_save_input(true,{},PcDiaryAction::Unavailable,dormant)==PurpleSaveInput::Neutral,"dormant default-file manager cannot receive input");
    PcSaveUiSnapshot incomplete=saveUi;incomplete.defaultFile.typingComplete=false;
    check(purple_save_input(true,{},PcDiaryAction::Unavailable,incomplete)==PurpleSaveInput::Unexpected,"inconsistent typing-ready evidence refused");
    check(purple_save_input(false,{},PcDiaryAction::Unavailable,saveUi)==PurpleSaveInput::Neutral,"default-file input cannot precede actual day advance");
    PcPurpleSaveBudget budget;
    check(budget.observe(0) && budget.observe(59.9),"acquisition has original hard60");
    check(budget.acquired(59.9,true) && budget.saving(),"verified late acquisition starts save once");
    check(budget.observe(119.8),"save phase may run another bounded60");
    check(!budget.observe(119.9) && !budget.observe(119.8),"save deadline failure sticky");
    PcPurpleSaveBudget late;
    check(!late.acquired(60,true),"late acquisition cannot extend its original deadline");
    PcPurpleSaveBudget missing;
    check(!missing.observe(60),"missing acquisition cannot use save budget");
    PcPurpleSaveBudget duplicate;
    check(duplicate.acquired(40,true) && !duplicate.acquired(50,true)
        && !duplicate.observe(50),"duplicate acquisition cannot reset save deadline");
    PcPurpleSaveBudget unverified;
    check(!unverified.acquired(20,false),"unverified acquisition refused");
    PcPurpleSaveBudget backwards;
    check(backwards.observe(20) && !backwards.observe(19),"backward clock refused");
    PcPurpleSaveBudget jump;
    check(jump.acquired(10,true) && !jump.observe(71),"forward time jump exceeds save limit");
    PcPurpleSaveBudget nan;
    check(!nan.observe(std::numeric_limits<double>::quiet_NaN()),"nonfinite clock refused");
    int captain=0, partner=0;
    for(unsigned formation=0;formation<=19;++formation)
        check(pcPurpleDismissInitialModes(formation,19-formation),"legitimate mixed Free/Formation initial roster");
    check(!pcPurpleDismissInitialModes(19,1),"extra initial body refused");
    check(!pcPurpleDismissInitialModes(18,0),"missing initial body refused");
    check(!pcPurpleDismissInitialModes(20,0),"extra Formation roster refused without unsigned underflow");
    PcPurpleDismissPolicy dismiss;
    check(dismiss.observe(false,true,false,false)==PcPurpleDismissInput::Neutral,"walking dismiss establishes released edge");
    check(dismiss.observe(false,true,false,false)==PcPurpleDismissInput::Press,"ordinary loaded button press");
    check(dismiss.observe(false,true,false,true)==PcPurpleDismissInput::Neutral,"Free roster alone cannot prove native Release");
    check(dismiss.observe(false,false,true,true)==PcPurpleDismissInput::Neutral,"observe actual Release and release button");
    check(dismiss.observe(false,true,false,true)==PcPurpleDismissInput::Done,"Release then Walk plus Free roster completes");
    PcPurpleDismissPolicy idleDismiss;
    check(idleDismiss.observe(true,false,false,false)==PcPurpleDismissInput::Press,"ordinary Idle wake press");
    check(idleDismiss.observe(true,false,false,false)==PcPurpleDismissInput::Press,"wait for actual Walk without state writes");
    check(idleDismiss.observe(false,true,false,false)==PcPurpleDismissInput::Neutral,"release wake before fresh click");
    check(idleDismiss.observe(false,true,false,false)==PcPurpleDismissInput::Press,"fresh click after observed Walk");
    check(idleDismiss.observe(false,false,true,false)==PcPurpleDismissInput::Neutral,"Release alone with Formation does not complete");
    check(idleDismiss.observe(false,true,false,false)==PcPurpleDismissInput::Neutral,"Walk alone with Formation does not complete");
    check(idleDismiss.observe(false,true,false,true)==PcPurpleDismissInput::Done,"actual Free roster required");
    PcPurpleDismissPolicy missingRelease;
    for(unsigned i=0;i<120;++i)check(missingRelease.observe(false,true,false,true)!=PcPurpleDismissInput::Refuse,"finite dismiss observation budget");
    check(missingRelease.observe(false,true,false,true)==PcPurpleDismissInput::Refuse,"missing Release cannot hang or certify Free roster");
    check(pcPurpleCursorBandSafe(.2f,.1f,.5f,0.f),"ordinary cursor-band input stays movement neutral");
    check(!pcPurpleCursorBandSafe(.1f,.1f,.5f,0.f),"neutral boundary cannot guarantee turning");
    check(pcPurpleCursorBandSafe(.5f,.1f,.5f,0.f),"exact cursor upper boundary remains movement neutral");
    check(!pcPurpleCursorBandSafe(.50001f,.1f,.5f,0.f),"outside cursor band refused");
    check(!pcPurpleCursorBandSafe(.2f,.1f,.5f,.000001f),"any modeled movement target refused");
    check(!pcPurpleCursorBandSafe(std::numeric_limits<float>::quiet_NaN(),.1f,.5f,0.f),"nonfinite cursor input refused");
    PcPurplePoseProbeBudget probeBudget;
    for(unsigned frame=0;frame<64;++frame)check(probeBudget.take(),"finite pose probe capacity");
    for(unsigned repeat=0;repeat<4;++repeat)check(!probeBudget.take(),"budget exhausted cannot restart");
    check(probeBudget.frames()==64,"pose budget stable after refusal");
    for(int axis:{-8,8})check(pcPurpleSdlPulseSampleAxis(axis,8)==0,"exact default dead-zone boundary suppressed");
    for(int axis:{-9,9})check(pcPurpleSdlPulseSampleAxis(axis,8)==axis,"outside default boundary preserved");
    check(pcPurpleSdlPulseSampleAxis(-6,8)==0 && pcPurpleSdlPulseSampleAxis(64,8)==64,
        "captured command -6,64 samples actual 0,64");
    check(pcPurpleSdlPulseSampleAxis(-6,0)==-6,"zero dead-zone preserves captured minor axis");
    for(int deadZone:{0,3,8,12,64,127})for(int axis=-74;axis<=74;++axis) {
        const int sdlAxis=axis*256;
        const int sampled=std::abs(sdlAxis)>deadZone*256 ? sdlAxis/256 : 0;
        check(pcPurpleSdlPulseSampleAxis(axis,deadZone)==sampled,"native-unit model matches actual SDL sampling equation");
    }
    check(pcPurpleCollisionAcquisitionMode("sdl_acquire"),"direct acquisition mode captures typed evidence");
    check(pcPurpleCollisionAcquisitionMode("sdl_dayend"),"ordinary dayend acquisition captures typed evidence");
    const char* unrelatedModes[]={nullptr,"","sdl_health","sdl_resume","ordinary","sdl_acquire_extra"};
    for(const char* mode:unrelatedModes)
        check(!pcPurpleCollisionAcquisitionMode(mode),"unrelated modes remain inert");
    PcPurpleCollisionTraceWindow trace;
    check(!trace.take(&captain,true),"default inactive");
    trace.begin(false,true,&captain,1); check(!trace.take(&captain,true),"explicit flag required");
    trace.begin(true,false,&captain,2); check(!trace.take(&captain,true),"active pulse required");
    trace.begin(true,true,nullptr,3); check(!trace.take(nullptr,true),"actual captain required");
    trace.begin(true,true,&captain,4);
    check(!trace.take(&partner,true),"foreign actor refused");
    check(!trace.take(&captain,false),"unchanged force not logged");
    for(unsigned i=0;i<16;++i)check(trace.take(&captain,true),"per-tick capacity");
    trace.begin(true,true,&captain,4);check(!trace.take(&captain,true),"same tick cannot reset budget");
    trace.begin(true,true,&captain,5);check(trace.take(&captain,true),"new tick resets only per-tick count");
    trace.begin(true,true,&captain,3);check(!trace.take(&captain,true),"backward tick refused");
    check(trace.tick()==5,"backward tick cannot replace captured history");
    trace.begin(true,true,&captain,3);check(!trace.take(&captain,true),"repeated backward tick refused");
    for(unsigned tick=6;tick<150;++tick) { trace.begin(true,true,&captain,tick);for(unsigned i=0;i<16;++i)trace.take(&captain,true); }
    check(trace.sequence()==2048,"whole-process log bound");
    trace.begin(true,true,&captain,200);check(!trace.take(&captain,true),"global limit cannot reset");
    PcPurpleCollisionClosure closure;
    PcPurpleQueuedForce a{.00812473707f,0,.0027200568f},b{.0162494704f,0,.00544011313f};
    auto arm=[&](unsigned tick) { closure.begin(true,&captain,tick,tick+100,{}); };
    arm(1);closure.record(&captain,101,true,{},a);closure.record(&captain,101,true,a,b);
    check(closure.matches(&captain,1,101,b),"actual two-write collision closes exactly");
    check(!closure.matches(&partner,1,101,b),"foreign captain cannot consume evidence");
    check(!closure.matches(&captain,2,101,b),"stale fixture tick refused");
    check(!closure.matches(&captain,1,102,b),"stale authoritative tick refused");
    check(!closure.matches(&captain,1,101,a),"unexplained final force refused");
    arm(2);check(!closure.matches(&captain,2,102,{}),"empty trace is not provenance");
    closure.record(&captain,102,false,{},a);check(!closure.matches(&captain,2,102,a),"unowned or unsupported partner refused");
    arm(3);closure.record(&captain,103,true,a,b);check(!closure.matches(&captain,3,103,b),"intervening unobserved force refused");
    arm(4);closure.record(&captain,0,true,{},a);check(!closure.matches(&captain,4,104,a),"non-authoritative write refused");
    arm(5);closure.record(&captain,104,true,{},a);check(!closure.matches(&captain,5,105,a),"wrong write tick refused");
    arm(6);closure.record(&partner,106,true,{},a);check(!closure.matches(&captain,6,106,a),"foreign actor write not evidence");
    arm(7);PcPurpleQueuedForce last{};
    for(unsigned i=0;i<17;++i) { PcPurpleQueuedForce next{float(i+1),0,0};closure.record(&captain,107,true,last,next);last=next; }
    check(!closure.matches(&captain,7,107,last),"overflow cannot certify incomplete trace");
    arm(8);closure.record(&captain,108,true,{},a);arm(8);
    closure.record(&captain,108,true,{},a);check(!closure.matches(&captain,8,108,a),"same tick cannot reset closure");
    arm(9);closure.record(&captain,109,true,{},a);arm(8);
    check(!closure.matches(&captain,9,109,a),"backward context invalidates closure");
    closure.begin(false,&captain,10,110,{});closure.record(&captain,110,true,{},a);
    check(!closure.watches(&captain)&&!closure.matches(&captain,10,110,a),"ordinary inactive context inert");
    closure.begin(true,&captain,11,111,a);closure.record(&captain,111,true,a,b);
    check(!closure.matches(&captain,11,111,b),"unproven queued input force refused");
    arm(12);closure.record(&captain,112,true,{}, {std::numeric_limits<float>::quiet_NaN(),0,0});
    check(!closure.matches(&captain,12,112,a),"nonfinite force refused");
    closure.beginIdle(true,&captain,13,112,{});closure.record(&captain,113,true,{},a);
    closure.beginIdle(true,&captain,14,113,a);closure.record(&captain,114,true,{},b);
    check(closure.matches(&captain,14,114,b),"previous proven queue consumed then fresh owned collision qualifies");
    closure.beginIdle(true,&captain,15,114,b);closure.record(&captain,115,true,b,a);
    check(!closure.matches(&captain,15,115,a),"uncleared preceding queue refused");
    closure.beginIdle(true,&captain,16,115,a);closure.record(&captain,116,true,{},b);
    check(!closure.matches(&captain,16,116,b),"unproven initial queue cannot qualify fresh collision");
    closure.beginIdle(true,&captain,17,116,{});closure.record(&captain,117,true,{},a);
    closure.beginIdle(true,&captain,19,117,a);closure.record(&captain,118,true,{},b);
    check(!closure.matches(&captain,19,118,b),"skipped fixture tick cannot reuse initial queue");
    PcPurplePoseEnvelope poses;float reserve=0;
    check(poses.observe(1,2,3,1,14,2,8.4f),"capture actual pose");
    check(poses.observe(1,2,3,3,15,4,8.5f),"capture animated growth");
    const auto* pose=poses.find(3,2);check(pose&&pose->horizontal==5&&pose->low==14&&pose->high==15&&pose->radius==8.5f,"bounded union retains extrema");
    check(PcPurplePoseEnvelope::projectedRadius(*pose,14.5f,6,reserve)&&reserve>17.f&&reserve<20.f,"all-yaw captured band reserve");
    check(PcPurplePoseEnvelope::projectedRadius(*pose,100,6,reserve)&&reserve==0,"vertically separated band");
    check(!poses.observe(1,4,3,0,0,0,1),"same id foreign part refused");
    check(!poses.find(3,2),"identity refusal sticky");
    PcPurplePoseEnvelope owner;check(owner.observe(1,2,1,0,0,0,1)&&!owner.observe(9,2,1,0,0,0,1),"foreign owner refused");
    PcPurplePoseEnvelope invalid;check(!invalid.observe(1,2,1,NAN,0,0,1),"nonfinite pose refused");
    PcPurplePoseEnvelope captured17;
    check(captured17.observe(1,2,1751474532,1.726929f,14.588223f,2.445801f,8.4f)
        &&captured17.observe(1,2,1751474532,1.903809f,14.625286f,2.176514f,8.4f),"captured17 animation frames");
    const auto* actual=captured17.find(1751474532,2);
    check(PcPurplePoseEnvelope::projectedRadius(*actual,14.6f,6,reserve)&&reserve>15.4f&&reserve<17.f,"captured animation retains reserve beyond current14.655 circle");
    auto bad=*pose;bad.horizontal=NAN;check(!PcPurplePoseEnvelope::projectedRadius(bad,14,6,reserve),"malformed captured bound refused");
    PcPurplePoseEnvelope bound;for(unsigned i=0;i<32;++i)check(bound.observe(1,i+1,i,0,0,0,1),"bounded part capture");
    check(!bound.observe(1,33,33,0,0,0,1),"part overflow refused");
    PcPurplePoseEnvelope rotation;
    check(rotation.observe(1,2,3,3,14,0,8.4f,1.570796327f),"captured rotated local pose");
    float rx=0,rz=0;check(PcPurplePoseEnvelope::rotatedOffset(*rotation.find(3,2),1.570796327f,rx,rz)&&std::fabs(rx-3)<.0001f&&std::fabs(rz)<.0001f,"actual yaw reconstruction");
    check(pcPurplePulseYawEligible(0,0,10,0,100,100,1,1.f/30.f),"native face and neutral cursor stay in admitted arc");
    check(!pcPurplePulseYawEligible(0,10,0,0,100,100,1,1.f/30.f),"opposite pulse yaw refused");
    check(!pcPurplePulseYawEligible(0,0,10,100,0,100,1,1.f/30.f),"neutral cursor heading outside arc refused");
    check(!pcPurplePulseYawEligible(0,0,10,0,1,100,1,1.f/30.f),"cursor displacement may cross origin refused");
    check(!pcPurplePulseYawEligible(0,0,10,0,100,100,3.1f,1.f/30.f),"loaded face overshoot refused");
    check(!pcPurplePulseYawEligible(0,0,10,0,100,100,1,.04f),"unsupported timing refused");
    check(!pcPurplePulseYawEligible(NAN,0,10,0,100,100,1,1.f/30.f),"invalid yaw refused");
    check(pcPurplePulseYawEligible(0,0,10,0,100,100,3,1.f/60.f),"variable supported frame rate remains bounded");
    check(pcPurplePulseYawEligible(0,0,10,std::sin(.39f)*100,std::cos(.39f)*100,0,1,1.f/30.f),"cursor arc boundary inside");
    check(!pcPurplePulseYawEligible(0,0,10,std::sin(.4f)*100,std::cos(.4f)*100,0,1,1.f/30.f),"cursor beyond admitted yaw arc refuses");
    const auto* captured=rotation.find(3,2);
    check(PcPurplePoseEnvelope::projectedRadius(*captured,14,6,reserve),"local envelope projection");
    for(int i=0;i<=32;++i){
        const float yaw=-PcPurplePulseYawHalfArc+2*PcPurplePulseYawHalfArc*i/32;
        float x=0,z=0;check(PcPurplePoseEnvelope::rotatedOffset(*captured,yaw,x,z),"intermediate captured yaw");
        float nearest=1000;
        for(int sample=-1;sample<=1;++sample){float sx=0,sz=0;check(PcPurplePoseEnvelope::rotatedOffset(*captured,sample*PcPurplePulseYawHalfArc,sx,sz),"envelope sample yaw");nearest=std::min(nearest,std::hypot(x-sx,z-sz));}
        check(nearest<=reserve-15.4f+.0001f,"sampled chord reserve covers admitted intermediate yaw");
    }
    PcPurpleMotionPoseCatalog motion;
    check(motion.select(1,2,3)&&motion.observe(1,4,5,1,14,2,10),"motion family first capture");
    check(motion.select(1,4,3)&&motion.observe(1,4,5,1,14,2,4),"different compatible family capture");
    check(motion.find(5,4)&&motion.find(5,4)->radius==4,"foreign animation extrema not applied to current family");
    check(motion.select(1,2,3)&&motion.find(5,4)->radius==10,"same family history retained on return");
    check(motion.observe(1,4,5,2,13,3,11)&&motion.find(5,4)->radius==11,"same family grows conservatively");
    check(!motion.select(2,2,3)&&!motion.find(5,4),"foreign captain sticky refusal");
    PcPurpleMotionPoseCatalog replacement;
    check(replacement.select(1,0,0)&&replacement.observe(1,4,5,0,1,0,2),"part identity established");
    check(replacement.select(1,1,0)&&!replacement.observe(1,6,5,0,1,0,2),"part replacement across motion refuses");
    PcPurpleMotionPoseCatalog overflow;
    for(int i=0;i<16;++i)check(overflow.select(1,i,0),"bounded16 motion families");
    check(!overflow.select(1,16,0)&&!overflow.select(1,0,0),"motion overflow sticky refuses");
    PcPurpleMotionPoseCatalog invalidMotion;
    check(!invalidMotion.select(1,-1,0),"invalid native motion refuses");
    float cursorArc=0;
    check(pcPurpleCursorYawBound(0,0,100,0,1.f/30.f,cursorArc)&&cursorArc==0,"aligned stationary cursor has zero native turn");
    check(pcPurpleCursorYawBound(0,100,0,0,1.f/30.f,cursorArc)&&std::fabs(cursorArc-.2f*1.570796327f)<.00001f,"native one-fifth cursor-facing bound");
    check(!pcPurpleCursorYawBound(0,0,1,100,1.f/30.f,cursorArc),"cursor may cross origin refuses");
    check(!pcPurpleCursorYawBound(0,0,100,100,.04f,cursorArc),"unsupported cursor timing refuses");
    check(!pcPurpleCursorYawBound(0,0,100,INFINITY,1.f/30.f,cursorArc),"nonfinite cursor speed refuses");
    for(int frame=1;frame<=30;++frame)for(int direction=0;direction<64;++direction){
        const float dt=frame/(30.f*30.f),yaw=.2f,cx=10.f,cz=100.f;
        check(pcPurpleCursorYawBound(yaw,cx,cz,100,dt,cursorArc),"source cursor bound finite");
        const float angle=direction*6.283185307f/64.f;
        const float actual=.2f*std::remainder(std::atan2(cx+100*dt*std::sin(angle),cz+100*dt*std::cos(angle))-yaw,6.283185307f);
        check(std::fabs(actual)<=cursorArc+.000001f,"all one-tick cursor directions within native yaw bound");
    }
    for(float arc:{0.f,.001f,.4f,1.5f}){
        check(PcPurplePoseEnvelope::projectedRadius(*captured,14,6,reserve,arc),"variable native arc projection");
        for(int i=0;i<=32;++i){float x=0,z=0;PcPurplePoseEnvelope::rotatedOffset(*captured,-arc+2*arc*i/32,x,z);float nearest=1000;
            for(int sample=-1;sample<=1;++sample){float sx=0,sz=0;PcPurplePoseEnvelope::rotatedOffset(*captured,sample*arc,sx,sz);nearest=std::min(nearest,std::hypot(x-sx,z-sz));}
            check(nearest<=reserve-15.4f+.0001f,"variable arc chord covers intermediate captured rotations");
        }
    }
    check(!PcPurplePoseEnvelope::projectedRadius(*captured,14,6,reserve,-.1f),"negative arc refuses");
    check(!PcPurplePoseEnvelope::projectedRadius(*captured,14,6,reserve,INFINITY),"nonfinite arc refuses");
    float nextX=0,nextZ=0;
    check(pcPurpleCursorStep(0,100,0,1,100,1.f/30.f,100,nextX,nextZ)&&nextX==0&&std::fabs(nextZ-100)<.00001f,"native radial cursor cap removes outward step");
    check(pcPurpleCursorStep(0,100,1,0,100,1.f/30.f,100,nextX,nextZ)&&nextX>0&&nextZ<100,"native tangential cursor projection retained");
    check(pcPurpleCursorStep(0,50,0,1,100,1.f/30.f,100,nextX,nextZ)&&std::fabs(nextZ-53.333333f)<.0001f,"below-cap native cursor step");
    check(!pcPurpleCursorStep(0,100,2,0,100,1.f/30.f,100,nextX,nextZ),"nonunit cursor direction refuses");
    check(!pcPurpleCursorStep(0,100,1,0,100,.04f,100,nextX,nextZ),"cursor timing outside model refuses");
    check(!pcPurpleCursorStep(0,100,1,0,INFINITY,1.f/30.f,100,nextX,nextZ),"invalid cursor speed refuses");
    PcPurpleSaveBudget engineeringBudget(true);
    check(engineeringBudget.acquisitionLimit()==90&&engineeringBudget.wholeLimit()==150,"explicit engineering90 has bounded total150");
    check(engineeringBudget.observe(89)&&engineeringBudget.acquired(89,true)&&engineeringBudget.observe(148.9),"late engineering acquisition gets only original save60");
    check(!engineeringBudget.observe(149),"engineering post-save hard60 refuses");
    PcPurpleSaveBudget engineeringLate(true);check(!engineeringLate.acquired(90,true),"engineering acquisition hard90 refuses");
    PcPurpleSaveBudget defaultBudget;check(!defaultBudget.acquired(60,true),"default acquisition hard60 unchanged");
    PcPurpleSaveBudget engineeringReset(true);check(engineeringReset.acquired(80,true)&&!engineeringReset.acquired(81,true),"engineering cannot reset phase fence");
    const float extreme=std::numeric_limits<float>::max();
    check(pcPurpleSegmentCircleClear(0,0,10,0,5,2,1,.05f),"ordinary segment safely outside margin");
    check(!pcPurpleSegmentCircleClear(0,0,10,0,5,1,1,.05f),"margin intersection still refuses");
    check(pcPurpleSegmentCircleClear(0,0,10,0,5,1.05f,1,.05f),"exact tangent reserve boundary unchanged");
    check(!pcPurpleSegmentCircleClear(0,0,10,0,5,0,1,.05f),"crossing circle refuses");
    check(pcPurpleSegmentCircleClear(0,0,0,0,2,0,1,.05f),"stationary clear segment admits");
    check(!pcPurpleSegmentCircleClear(-extreme,0,extreme,0,0,0,1,.05f),"finite delta overflow refuses");
    check(!pcPurpleSegmentCircleClear(0,0,extreme,0,0,0,1,.05f),"finite squared segment overflow refuses");
    check(!pcPurpleSegmentCircleClear(0,0,100,0,extreme,0,1,.05f),"finite numerator overflow refuses");
    check(!pcPurpleSegmentCircleClear(0,0,1,0,0,0,extreme,extreme),"finite circle sum overflow refuses");
    check(!pcPurpleCursorYawBound(0,extreme,extreme,0,1.f/30.f,cursorArc),"finite cursor radius overflow refuses yaw admission");
    check(!pcPurpleCursorStep(extreme,extreme,1,0,1,1.f/30.f,extreme,nextX,nextZ),"finite cursor length overflow refuses predicted step");
    auto extremePart=*captured;extremePart.radius=extreme;
    check(!PcPurplePoseEnvelope::projectedRadius(extremePart,14,extreme,reserve),"finite projected radius sum overflow refuses");
    std::puts("Purple collision trace controls PASS");
}
