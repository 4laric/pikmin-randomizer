"""Isolated regular day-end Start guard proposal; shared native untouched."""
from experimental.pikmin2_tank_heap_diagnostic import once

GUARD='''    // Phase-one day-end movies reuse the gameplay Teki heap. Completing them
    // early can expose retained actors before the results flow takes ownership.
    // Intro, gameplay and phase-zero day-end movies keep their normal skip path.
    for (MovieInfo* info = static_cast<MovieInfo*>(mPlayInfoList.mChild); info;
         info = static_cast<MovieInfo*>(info->mNext)) {
        for (int stage = 0; stage < STAGE_COUNT; ++stage) {
            if (info->mMovieIndex == movie32table[stage] || info->mMovieIndex == movie56table[stage]) return;
        }
    }
'''

def apply_guard(source):
    start=source.index('void MoviePlayer::requestSkip()');end=source.index('void MoviePlayer::skipScene(',start)
    part=source[start:end]
    part=once(part,'    bool requested = false;',GUARD+'    bool requested = false;')
    return source[:start]+part+source[end:]

def observe_guard(source):
    source=once(source,'if (info->mMovieIndex == movie32table[stage] || info->mMovieIndex == movie56table[stage]) return;','if (info->mMovieIndex == movie32table[stage] || info->mMovieIndex == movie56table[stage]) { fprintf(stderr,"TANK_DAYEND_SKIP_BLOCKED movie=%u\\n",info->mMovieIndex); return; }')
    return once(source,'if (info->mPlayer) { info->mPlayer->requestSkip(); requested = true; }','if (info->mPlayer) { fprintf(stderr,"TANK_NORMAL_SKIP_REQUEST movie=%u name=%s\\n",info->mMovieIndex,info->mName); info->mPlayer->requestSkip(); requested = true; }')

def analyze_fixed(text,requested):
    import re
    blocked=re.findall(r'TANK_DAYEND_SKIP_BLOCKED movie=(\d+)',text)
    intro=re.findall(r'TANK_NORMAL_SKIP_REQUEST movie=40 name=cinemas/demo40.cin',text)
    if not intro:raise ValueError('No accepted native landing-intro skip')
    if len(blocked)!=(1 if requested else 0):raise ValueError('Unexpected selective guard count')
    if '[PC GX] DESYNC #' in text:raise ValueError('GX warning remains')
    changed=[]
    for old,new in re.findall(r'TANK_HEAP_DRAW [^\n]*original=([0-9a-f]+) now=([0-9a-f]+)[^\n]*name=tekis/tank/tank.mod',text):
        if old!=new:changed.append((old,new))
    if changed:raise ValueError('Stale Tank bytes still submitted')
    if 'dataDir/cinemas/demo56.cin' not in text:raise ValueError('Day-end transition not reached')
    return dict(blocked_movies=list(map(int,blocked)),accepted_intro_requests=len(intro),gx_warnings=0,stale_tank_submissions=0)
