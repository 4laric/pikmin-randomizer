#pragma once
#include "pc_goal_birth_ledger.h"

// Fixture census arithmetic only; no actor pointers or game state writes.
struct PcGoalPopulationCensus {
    int field[6][3]{},stock[6][3]{},heads[6][3]{};
    bool valid() const {
        for(int s=0;s<6;++s){
            for(int m=0;m<3;++m)if(field[s][m]<0 || field[s][m]>100000
                || stock[s][m]<0 || stock[s][m]>100000 || heads[s][m]<0 || heads[s][m]>100000)return false;
        }
        return true;
    }
    int total(int species) const {
        int n=0;
        for(int m=0;m<3;++m)n+=field[species][m]+stock[species][m]+heads[species][m];
        return n;
    }
};
struct PcGoalPopulationAccounting {
    PcGoalPopulationCensus initial;
    int birthsAtBaseline[3]{};
    std::size_t conversionsAtBaseline=0;
    bool begun=false;
    bool begin(const PcGoalPopulationCensus& c,const PcGoalBirthLedger& l) {
        if(begun || !c.valid() || !l.armed || !l.complete || l.conversionCount)return false;
        for(int s=0;s<6;++s){
            for(int m=0;m<3;++m)if(c.heads[s][m] || c.stock[s][m] || (s!=1&&c.field[s][m]))return false;
        }
        if(c.total(1)!=20)return false;
        initial=c;
        for(int s=0;s<3;++s)birthsAtBaseline[s]=l.emitted[s]+l.stored[s]+l.bootEmitted[s];
        conversionsAtBaseline=l.conversionCount;begun=true;return true;
    }
    bool closes(const PcGoalPopulationCensus& c,const PcGoalBirthLedger& l,bool saved) const {
        if(!begun || !c.valid() || !l.complete || !l.armed || l.conversionCount!=conversionsAtBaseline+1)return false;
        const auto& conversion=l.conversions[conversionsAtBaseline];
        if(conversion.inputSpecies!=1 || conversion.inputMaturity<0 || conversion.inputMaturity>2)return false;
        for(int s=0;s<6;++s){
            const int born=s<3?l.emitted[s]+l.stored[s]+l.bootEmitted[s]-birthsAtBaseline[s]:0;
            if(born<0 || c.total(s)!=initial.total(s)+born+(s==3?1:s==1?-1:0))return false;
            if(saved){
                    for(int m=0;m<3;++m)if(c.heads[s][m] || c.field[s][m])return false;
            }
        }
        return !saved || l.settled();
    }
};
