#include "pc_p2_original_checkpoint_graph.h"
#include <cstdlib>
#include <iostream>
#include <stdexcept>
using namespace p2originalcheckpoint;
static unsigned checks;
static void check(bool value) { ++checks; if(!value) std::abort(); }
struct Authority : ProofSource {
    Proof proof;
    mutable unsigned calls=0;
    unsigned driftAt=0;
    bool selected(Proof& out,std::string&) const override {
        out=proof;
        if(++calls==driftAt)++out.generation;
        return true;
    }
};
struct Staged : Provider {
    unsigned failAt=0,throwAt=0,phase=0,aborts=0,published=0;
    std::vector<unsigned> calls;
    bool step(unsigned next) {
        check(next==phase+1);phase=next;calls.push_back(next);
        if(throwAt==next)throw std::runtime_error("staged provider failure");
        return next!=failAt;
    }
    bool preflight(const Graph& g,std::string&) override {
        return step(1)&&g.sections.size()==1&&g.sections[0].role=="gas";
    }
    bool reserve(const Graph&,std::string&) override {return step(2);}
    bool allocateNoInit(const Graph&,std::string&) override {return step(3);}
    bool resolveAndApply(const Graph&,std::string&) override {return step(4);}
    void publish() noexcept override {check(phase==4&&!aborts);++published;}
    void abort() noexcept override {check(!published);++aborts;}
};
int main() {
    Graph g{std::string(64,'a'),std::string(64,'b'),{{"gas",1,"typed family graph"}}};
    Proof proof;proof.generation=7;proof.sha[31]=1;
    std::string error;
    auto run=[&](const Graph& graph,Authority& a,Staged& p){return restore(graph,proof,g.campaign,g.session,a,p,error);};
    {Authority a;a.proof=proof;Staged p;check(run(g,a,p));check(p.published==1&&p.aborts==0&&a.calls==4);}
    for(unsigned fail=1;fail<=4;++fail){Authority a;a.proof=proof;Staged p;p.failAt=fail;check(!run(g,a,p));check(!p.published&&p.phase==fail&&p.aborts==1);}
    for(unsigned drift=1;drift<=4;++drift){Authority a;a.proof=proof;a.driftAt=drift;Staged p;check(!run(g,a,p));check(!p.published&&p.aborts==(drift>1));}
    for(unsigned throwing=1;throwing<=4;++throwing){Authority a;a.proof=proof;Staged p;p.throwAt=throwing;try{run(g,a,p);check(false);}catch(const std::runtime_error&){check(p.aborts==1&&!p.published);}}
    // Reject malformed or foreign envelopes before any family/provider work.
    for(unsigned bad=0;bad<7;++bad){Graph next=g;
        if(bad==0)next.session=std::string(64,'c');
        if(bad==1)next.campaign=std::string(64,'c');
        if(bad==2)next.sections.clear();
        if(bad==3)next.sections[0].version=0;
        if(bad==4)next.sections[0].role="gas/../card";
        if(bad==5)next.sections.push_back(next.sections[0]);
        if(bad==6)next.sections[0].bytes.resize(1024*1024+1);
        Authority a;a.proof=proof;Staged p;check(!run(next,a,p));check(!p.phase&&!p.published&&!p.aborts);
    }
    {Graph next=g;next.sections[0].role="unknown";Authority a;a.proof=proof;Staged p;check(!run(next,a,p));check(p.phase==1&&p.aborts==1&&!p.published);}
    {Authority a;a.proof=proof;Staged p;Proof empty;check(!restore(g,empty,g.campaign,g.session,a,p,error));check(!p.phase);}
    std::cout<<"PASS staged original graph transaction "<<checks<<" controls (protocol only; no physical provider)\n";
}
