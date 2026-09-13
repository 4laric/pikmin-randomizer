#pragma once

class Teki {
public:
    int mStateID = 0;
    bool mIsStateReady = true;
    int mReturnStateID = 0;
    int mCurrentQueueId = 0;
    int mTekiType = 0;
    float mHealth = 0.0f;
    float mStoredDamage = 0.0f;
    int startCount = 0;
    int finishCount = 0;
    int damageCount = 0;
    int deathCount = 0;
    int stunCount = 0;
};

struct TekiEvent {
    Teki* mTeki = nullptr;
};
