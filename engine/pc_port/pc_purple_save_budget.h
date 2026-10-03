#ifndef PC_PURPLE_SAVE_BUDGET_H
#define PC_PURPLE_SAVE_BUDGET_H
#include <cmath>
// Absolute steady-clock seconds since fixture entry. One transition, no reset.
// This policy observes time and verified acquisition; it never changes gameplay.
class PcPurpleSaveBudget {
    double last_=0, acquired_=-1,acquisitionLimit_=60;
    bool failed_=false;
public:
    explicit PcPurpleSaveBudget(bool engineering=false):acquisitionLimit_(engineering?90:60) {}
    double acquisitionLimit() const {return acquisitionLimit_;}
    double wholeLimit() const {return acquisitionLimit_+60;}
    bool observe(double now) {
        if(failed_) return false;
        if(!std::isfinite(now) || now<last_ || now>=wholeLimit()
            || (acquired_<0 ? now>=acquisitionLimit_ : now-acquired_>=60)) {
            failed_=true;return false;
        }
        last_=now;return true;
    }
    bool acquired(double now,bool verified) {
        if(!verified || acquired_>=0 || !observe(now)) {
            failed_=true;return false;
        }
        acquired_=now;return true;
    }
    bool saving() const {return acquired_>=0 && !failed_;}
    double acquisitionSeconds() const {return acquired_;}
    double saveSeconds(double now) const {return now-acquired_;}
};
#endif
