#pragma once

class Teki;
struct TekiEvent;

#define immut const
#define TAI_NO_TRANSIT (-1)
#define TAI_RETURN_TRANSIT (-2)

class TekiStrategy {
public:
    virtual ~TekiStrategy() = default;
    virtual void start(Teki&) {}
    virtual void act(Teki&) {}
    virtual void eventPerformed(immut TekiEvent&) {}
};

class TaiAction {
public:
    explicit TaiAction(int nextState) : mNextState(nextState) {}
    virtual ~TaiAction() = default;
    virtual void start(Teki&) {}
    virtual void finish(Teki&) {}
    virtual bool act(Teki&) { return false; }
    virtual bool actByEvent(immut TekiEvent&) { return false; }
    virtual bool hasNextState() { return mNextState >= 0 || mNextState == TAI_RETURN_TRANSIT; }
    int mNextState;
};

struct TaiSerialAction : TaiAction {
    TaiSerialAction(int, int);
    void start(Teki&) override;
    void finish(Teki&) override;
    bool act(Teki&) override;
    bool actByEvent(immut TekiEvent&) override;
    int mCount;
    TaiAction** mActionQueue;
};

class TaiState {
public:
    explicit TaiState(int);
    virtual ~TaiState() = default;
    virtual void start(Teki&);
    virtual void finish(Teki&);
    virtual bool act(Teki&);
    virtual bool eventPerformed(immut TekiEvent&);
    void setAction(int idx, TaiAction* action) { mActions[idx] = action; }
    int mCount;
    TaiAction** mActions;
};

struct TaiStrategy : TekiStrategy {
    TaiStrategy(int, int);
    void start(Teki&) override;
    void act(Teki&) override;
    void eventPerformed(immut TekiEvent&) override;
    void init(int, int);
    bool transit(Teki&, int);
    void setState(int idx, TaiState* state) { mStateList[idx] = state; }
    int mStateCount;
    TaiState** mStateList;
    int mStateID;
};
