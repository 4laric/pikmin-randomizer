#include <initializer_list>
#include "pc_p2_demon_attack_window.h"
#include <cassert>
#include <limits>
#include <cstdio>
int main() {
    P2DemonAttackWindow w;
    for(float f: {10.f,16.f,30.01f}) assert(!w.step(f,true,false).attemptCapture);
    assert(w.step(16.01f,true,false).attemptCapture);
    assert(w.step(30,true,false).attemptCapture);
    assert(!w.step(20,true,true).attemptCapture);
    assert(!w.step(21,true,false).attemptCapture);
    w.reset();
    assert(w.step(20,true,false).attemptCapture);
    assert(w.step(20,false,false).next==P2DemonAttackNext::Move);
    assert(!w.step(std::numeric_limits<float>::quiet_NaN(),true,false).valid);
    using E=P2DemonAttackEvent; using N=P2DemonAttackNext;
    auto ev=P2DemonAttackWindow::eventDecision;
    assert(ev(true,true,E::CaptureCheck,0).next==N::Fail);
    assert(ev(true,true,E::CaptureCheck,1).next==N::None);
    assert(ev(true,true,E::End,2).next==N::CatchFly);
    assert(ev(true,true,E::End,0).next==N::Move);
    assert(ev(false,true,E::End,1).next==N::CatchFly);
    assert(ev(true,false,E::End,1).next==N::None);
    assert(ev(true,true,E::Interruptible,0).clearNoInterrupt);
    assert(!ev(false,true,E::Dash,0).dash);
    assert(!ev(true,true,E::End,3).valid);
    puts("p2_demon_attack_window_test PASS");
}
