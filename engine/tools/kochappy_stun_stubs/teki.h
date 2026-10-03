#pragma once

// Test-only host boundary. The test links the real registered stun receiver;
// these fields/methods do not model production FSM execution or natural impact.
struct TestVector {
    float x = 0, y = 0, z = 0;
    void set(float a, float b, float c) { x=a; y=b; z=c; }
};
class BTeki {
public:
    enum { TEKI_OPTION_INVINCIBLE = 1 };
    int mDeadState = 0, mStateID = 0;
    bool alive = true, flying = false, invincible = false;
    bool ownFSM = false, ownEligible = true;
    int pauseCalls = 0;
    float mHealth = 200;
    void* mGroundTriangle = this;
    void* strategy = nullptr;
    TestVector mVelocity, mTargetVelocity;
    bool isAlive() { return alive; }
    bool isFlying() { return flying; }
    bool getTekiOption(int) { return invincible; }
    void* getStrategy() { return strategy; }
};
class Teki : public BTeki {};
