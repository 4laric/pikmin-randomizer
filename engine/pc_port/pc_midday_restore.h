#pragma once
#include "pc_midday_codec.h"
#include <functional>
#include <map>
namespace pc_midday {
struct RestoreGate {
    bool freshProcess=false,paused=false,zeroInput=false;
    bool birthEffectsSuppressed=false,rewardsSuppressed=false;
    bool rngDrawsSuppressed=false,audioVoicesSuppressed=false;
};
using ActorStateValidator=std::function<bool(const Actor&,std::string&)>;
using GlobalStateValidator=std::function<bool(const Section&,std::string&)>;
using StagedHandle=uint64_t; // local backend handle, never checkpoint wire state
// Production backend must own a disposable staged scene. begin/allocate/allocateSubobjects/bind/
// apply/verify must not publish live managers, grant AP rewards, advance a tick,
// consume RNG, emit audio or trigger birth effects. publishPaused is all-or-none;
// false/exception must leave the active world unchanged. Abort is noexcept.
class RestoreBackend {
public:
    virtual ~RestoreBackend()=default;
    virtual RestoreGate gate()const=0;
    virtual bool begin(const Snapshot&,std::string&)=0;
    virtual bool allocate(const Actor&,StagedHandle&,std::string&)=0;
    // Allocate every saved action/listener subobject, including inactive but
    // referenced pool entries, without callbacks. All root actors already exist;
    // no actor/global reference is bound until this phase completes for all actors.
    virtual bool allocateSubobjects(const Actor&,StagedHandle,std::string&)=0;
    virtual bool bind(const Actor&,StagedHandle,const std::vector<StagedHandle>&,std::string&)=0;
    virtual bool applyGlobal(const Section&,std::string&)=0;
    virtual bool verify(const Snapshot&,const std::map<uint64_t,StagedHandle>&,std::string&)=0;
    virtual bool publishPaused(const Snapshot&,std::string&)=0;
    virtual void abort()noexcept=0;
};
bool restorePaused(const Snapshot&,const Binding&,const Coverage&,
    const std::map<std::pair<uint32_t,uint32_t>,ActorStateValidator>&,
    const std::map<std::pair<uint32_t,uint32_t>,GlobalStateValidator>&,
    RestoreBackend&,std::string&);
}
