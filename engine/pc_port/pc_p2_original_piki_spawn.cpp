#include "pc_p2_original_piki_spawn.h"
#include <cmath>
namespace p2original {
namespace {
bool finite(const std::array<float,3>& value){for(float x:value)if(!std::isfinite(x))return false;return true;}
bool unit(float x){return std::isfinite(x)&&x>=0.0f&&x<=1.0f;}
}
bool spawnOriginalPiki(const PikiSpawnRecord& row,const PikiSpawnProgress& progress,
    PikiSpawnProvider& provider,PikiSpawnResult& out,std::string& error){
    if(row.count>65535||row.species<0||row.species>5
       ||(progress.met&~31u)||(progress.boot&~7u)||!finite(row.position)||!finite(row.offset)){
        error="invalid original Piki source/progress";return false;
    }
    std::array<float,3> center{};
    for(unsigned i=0;i<3;++i)center[i]=row.position[i]+row.offset[i];
    if(!finite(center)){error="original Piki center overflow";return false;}
    const bool wild=row.wildParameter==1;
    // Source hasMetPikmin(Bulbmin) is always true. Purple/White have no boot
    // container; they still have independent meet flags.
    const bool blocked=wild ? row.species==5 || (progress.met&(1u<<row.species))
        || (row.species<3&&(progress.boot&(1u<<row.species))) : !progress.allowDebug;
    if(!provider.prepare(row,error))return false;
    PikiSpawnResult result;
    for(std::uint32_t attempt=0;attempt<row.count;++attempt){
        const float angleDraw=provider.randomUnit();
        const float radiusDraw=provider.randomUnit();
        ++result.attempts;
        if(!unit(angleDraw)||!unit(radiusDraw)){
            out=result;error="original Piki RNG returned non-unit draw";return false;
        }
        const float angle=6.28318530717958647692f*angleDraw;
        float radius=10.0f*radiusDraw;
        if(row.species==2&&wild)radius=0.0f;
        std::array<float,3> position{{center[0]+radius*std::sin(angle),center[1],center[2]+radius*std::cos(angle)}};
        if(!finite(position)){out=result;error="original Piki position overflow";return false;}
        if(blocked){++result.policySkipped;continue;}
        switch(provider.birth(attempt,position,wild,error)){
        case PikiBirthResult::Born:++result.born;break;
        case PikiBirthResult::CapacitySkipped:++result.capacitySkipped;break;
        case PikiBirthResult::Failed:out=result;return false;
        default:out=result;error="invalid original Piki provider result";return false;
        }
    }
    out=result;error.clear();return true;
}
}
