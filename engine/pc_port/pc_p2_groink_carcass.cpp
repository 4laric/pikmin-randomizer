#include "pc_p2_groink_carcass.h"
#include <cmath>
namespace {
bool finite(float x) { return std::isfinite(x)&&x>=0&&x<=1.0e6f; }
int sTotalBirths = 0;
}
void p2_groink_carcass_note_birth() { ++sTotalBirths; }
int p2_groink_carcass_total_births() { return sTotalBirths; }
bool P2GroinkCarcass::become(const P2GroinkCarcassConfig& config) {
    if (!finite(config.gaugeDelay)||!finite(config.recoverySeconds)||config.recoverySeconds<=0||
        !finite(config.maxHealth)||!std::isfinite(config.maxHealth/config.recoverySeconds)) return false;
    config_=config; ready_=true; timer_=health_=0; return true;
}
void P2GroinkCarcass::reset() { ready_=false; timer_=health_=0; config_={}; }
P2GroinkCarcassStep P2GroinkCarcass::step(float delta, bool pelletAlive, bool gaugeManager, bool activeTick) {
    P2GroinkCarcassStep out;
    if (!ready_) return out;
    if (!activeTick) { out.valid=true; return out; }
    if (!std::isfinite(delta)||delta<0||delta>0.25f) return out;
    out.valid=true;
    if (pelletAlive) {
        if (timer_<config_.gaugeDelay) {
            timer_+=delta;
            if (gaugeManager&&timer_>=config_.gaugeDelay)
                out.commands[out.count++]=P2GroinkCarcassCommand::ActivateGauge;
        } else if (health_<config_.maxHealth) {
            // Preserve source overshoot and its else-if: the threshold-crossing
            // tick never also recovers health. Failed birth has no automatic retry.
            health_+=(config_.maxHealth/config_.recoverySeconds)*delta;
            if (health_>=config_.maxHealth) {
                out.commands[out.count++]=P2GroinkCarcassCommand::KillPellet;
                out.commands[out.count++]=P2GroinkCarcassCommand::RequestBirth;
            }
        }
    } else if (gaugeManager&&timer_>=config_.gaugeDelay) {
        timer_=health_=0;
        out.commands[out.count++]=P2GroinkCarcassCommand::DeactivateGauge;
    }
    return out;
}
