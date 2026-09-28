#include "pc_p2_kabuto_events.h"

p2sampled::Clip p2_kabuto_attack_clip(int duration, int fireFrame, const char* name,
                                      const char* key2Key)
{
    p2sampled::Clip clip;
    if (!name || !*name || !key2Key || !*key2Key || duration < 2 || fireFrame < 0
        || fireFrame >= duration) {
        return clip; // invalid: valid() stays false
    }
    clip.poses.name = name;
    clip.poses.count = 1;
    clip.poses.duration = duration;
    clip.loopBegin = 0.0;
    clip.loopEnd = -1.0; // one-shot motion
    clip.events.push_back(p2sampled::Event{fireFrame, key2Key});
    return clip;
}

bool P2KabutoEventAdapter::begin(const p2sampled::Clip& clip, const char* key2Key)
{
    if (!key2Key || !*key2Key) {
        mActive = false;
        return false;
    }
    mKey2 = key2Key;
    mEndEmitted = false;
    mActive = mClock.start(clip);
    return mActive;
}

bool P2KabutoEventAdapter::restart()
{
    mEndEmitted = false;
    mActive = mClock.restart();
    return mActive;
}

void P2KabutoEventAdapter::pause(bool paused)
{
    mClock.pause(paused);
}

bool P2KabutoEventAdapter::advance(double sourceFrames, P2KabutoEvent* out, int capacity,
                                   int& count)
{
    count = 0;
    if (!out || capacity <= 0 || !mActive) {
        return false;
    }
    const p2sampled::Batch batch = mClock.advance(sourceFrames);
    if (!batch) {
        return false;
    }
    auto push = [&](P2KabutoEvent event) {
        if (count >= capacity) {
            return false;
        }
        out[count++] = event;
        return true;
    };
    // Authored gameplay events first, in source order.
    for (const p2sampled::Occurrence& occurrence : batch.events) {
        if (occurrence.key == mKey2 && !push(P2KabutoEvent::Key2)) {
            return false;
        }
    }
    // One-shot completion terminates the motion exactly once.
    if (mClock.finished() && !mEndEmitted) {
        mEndEmitted = true;
        if (!push(P2KabutoEvent::End)) {
            return false;
        }
    }
    return true;
}
