#include "pc_p2_original_progress.h"
#include <iostream>
#include <stdexcept>
using namespace p2original;
unsigned checks=0;void check(bool b){++checks;if(!b)throw std::runtime_error("progress control "+std::to_string(checks));}
int main(){Progress p;std::string e,bytes;check(p.met(5));check(!p.booted(5)&&!p.met(1));check(!p.recruited(1,e));check(!p.encode(bytes,e));check(!p.initialize("wrong",e));
 const std::string campaign(64,'a');check(p.initialize(campaign,e));const auto fresh=p.snapshot();
 for(unsigned color=0;color<5;++color)check(!p.met(color)&&!p.container(color)&&!p.booted(color));
 check(p.recruited(1,e));check(p.booted(1)&&p.container(1)&&!p.met(1));check(p.recruited(1,e));check(!p.met(1));check(p.hello(1,e));check(p.met(1));
 check(p.boot(2,e));check(p.booted(2)&&!p.container(2)&&!p.met(2));check(p.recruited(2,e));check(!p.met(2)); // already booted: no first-meet event
 check(p.hello(2,e));check(p.met(2)&&p.container(2));check(p.recruited(0,e));check(p.met(0)&&p.booted(0)&&p.container(0));
 check(p.hello(3,e));check(p.hello(4,e));check(p.met(3)&&p.met(4)&&p.container(3)&&p.container(4));check(!p.booted(3)&&!p.booted(4));check(!p.boot(3,e)&&!p.recruited(4,e)&&!p.hello(5,e));
 check(p.encode(bytes,e));check(bytes.size()==104);Progress restored;check(restored.decode(bytes,campaign,e));check(restored.snapshot().met==31&&restored.snapshot().boot==7&&restored.snapshot().container==31);
 for(size_t n=0;n<bytes.size();++n)check(!restored.decode(bytes.substr(0,n),campaign,e));auto corrupt=bytes;corrupt[70]^=1;check(!restored.decode(corrupt,campaign,e));check(!restored.decode(bytes,std::string(64,'b'),e));check(!restored.initialize(std::string(64,'b'),e));
 // Unsaved discoveries roll back with the selected native checkpoint.
 check(restored.restore(fresh,e));check(!restored.met(1)&&!restored.booted(1));auto bad=fresh;bad.boot=8;check(!restored.restore(bad,e));bad=fresh;bad.met=32;check(!restored.restore(bad,e));bad=fresh;bad.container=32;check(!restored.restore(bad,e));bad=fresh;bad.campaign=std::string(64,'b');check(!restored.restore(bad,e));
 check(restored.discover(4,e));check(restored.container(4)&&!restored.met(4));check(!restored.discover(5,e));check(restored.met(5)&&!restored.booted(5)&&!restored.container(5));
 check(!restored.captainAllowed(2,true));check(restored.captainAllowed(0,true)&&!restored.captainAllowed(0,false));check(restored.captainAllowed(1,false)&&!restored.captainAllowed(1,true));
 const auto initialContext=restored.context();std::string context;check(restored.encodeContext(context,e));check(context.size()==106);check(restored.reunite(e));check(restored.captainAllowed(0,false)&&restored.captainAllowed(1,true));check(restored.decodeContext(context,campaign,e));check(!restored.captainAllowed(0,false));check(restored.nextDay(e));check(restored.context().day==1&&restored.captainAllowed(0,false));
 check(restored.restoreContext(initialContext,e));auto other=initialContext;other.campaign=std::string(64,'b');check(!restored.restoreContext(other,e));for(size_t n=0;n<context.size();++n)check(!restored.decodeContext(context.substr(0,n),campaign,e));context[70]^=1;check(!restored.decodeContext(context,campaign,e));
 std::cout<<"PASS original PlayData progression "<<checks<<" controls\n";
}
