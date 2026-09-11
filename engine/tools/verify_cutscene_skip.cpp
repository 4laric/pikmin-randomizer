// Links against the actual game implementation; no replacement cinematic logic.
#include "CinematicPlayer.h"
#include "MoviePlayer.h"
#include "Interface.h"
#include "gameflow.h"
#include "system.h"
#include <cstdio>
#include <cstdlib>
#include <vector>

struct Recorder : GameInterface {
    std::vector<int> events;
    void message(int cmd, int data) override { events.push_back(data); }
};
static void require(bool ok, const char* what) {
    if (!ok) { std::fprintf(stderr, "FAIL %s\n", what); std::exit(1); }
}
static std::vector<int> run(bool skip, int preFrames, bool loop, float delta, bool coincident = false) {
    Recorder recorder;
    gameflow.mGameInterface = &recorder;
    CinematicPlayer player(nullptr);
    SceneCut first, second;
    first.mStartFrame = 10; first.mEndFrame = 110;
    first.mFlags = loop ? 4 : 0; // Author disallows skipping; optionally loops.
    second.mStartFrame = 0; second.mEndFrame = 100;
    second.mFlags = 0;
    player.mSceneList.add(&first); player.mSceneList.add(&second);
    AnimKey keys[6];
    int frames[] = {10, 30, coincident ? 30 : 108, 0, 40, coincident ? 40 : 98};
    for (int i=0; i<6; ++i) {
        keys[i].mFrameIndex = frames[i]; keys[i].mEventType = ANIMEVENT_Notify;
        keys[i].mEventCmdID = MOVIECMD_SetPauseAllowed; keys[i].mKeyType = i;
        SceneCut& scene = i < 3 ? first : second;
        scene.mKey.mPrev->insertAfter(&keys[i]);
    }
    player.mIsPlaying = true; player.calcMaxFrames();
    gsys->mDeltaTime = delta;
    for (int i=0; i<preFrames; ++i) require(!player.update(), "premature completion");
    if (skip) player.requestSkip();
    bool done=false, firstEnd=false, secondEnd=false;
    int ticks=0;
    for (; ticks<2000 && !done; ++ticks) {
        if (skip && ticks % 2 == 0) player.requestSkip(); // Repeated Start must not replay events.
        done = player.update();
        if (player.mCurrentScene == &first && player.mCurrentSceneFrame > 109.9f) firstEnd=true;
        if (player.mCurrentScene == &second && player.mCurrentSceneFrame > 99.9f) secondEnd=true;
    }
    require(done, "completion including looping scenes");
    require(!player.mCurrentScene && !player.mPreviousScene, "scene cleanup");
    if (skip) {
        require(ticks < 20, "bounded skip latency");
        require(firstEnd && secondEnd, "final actor pose visited for each scene");
    }
    for (int e : recorder.events) std::printf("%d ", e); std::printf(" skip=%d pre=%d loop=%d dt=%f ticks=%d\n",skip,preFrames,loop,delta,ticks);
    return recorder.events;
}
int main() {
    MoviePlayer movies;
    gameflow.mMoviePlayer = &movies;
    const std::vector<int> expected{0,1,2,3,4,5};
    for (float delta : {1.f/30, 1.f/60, 1.f/120}) {
        require(run(false,0,false,delta) == expected, "watched event baseline");
        require(run(true,0,false,delta,true) == expected, "all co-timed events dispatched");
        for (int start : {0,1,15,35,99,100}) {
            require(run(true,start,false,delta) == expected, "skipped events once and in order");
            require(run(true,start,true,delta) == expected, "looping events once and in order");
        }
    }
    std::puts("PASS actual CinematicPlayer: watched/skip event parity, partial playback, repeated requests, loops, final poses, 30/60/120 Hz");
    std::fflush(stdout);
    std::_Exit(0);
}
