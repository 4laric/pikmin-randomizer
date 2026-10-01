import os,re,subprocess,tempfile,unittest
from pathlib import Path
from experimental.pikmin2_tank_skip_guard import GUARD,apply_guard,observe_guard
class TankSkipGuardTests(unittest.TestCase):
    def test_guard_is_confined_to_request_skip(self):
        raw='void MoviePlayer::requestSkip(){\n    bool requested = false;\n}\nvoid MoviePlayer::skipScene(){}'
        out=apply_guard(raw);self.assertTrue(out.endswith('void MoviePlayer::skipScene(){}'));self.assertIn('movie32table[stage]',out)
        self.assertIn('TANK_DAYEND_SKIP_BLOCKED',observe_guard(out.replace('    bool requested = false;','    bool requested = false;\nif (info->mPlayer) { info->mPlayer->requestSkip(); requested = true; }')))
    def test_actual_guard_snippet_covers_source_translation_tables(self):
        root=Path(__file__).resolve().parents[1];compiler=Path('C:/msys64/mingw64/bin/g++.exe')
        if not compiler.exists():self.skipTest('Private native compiler unavailable')
        source=(root/'engine/src/plugPikiColin/moviePlayer.cpp').read_text();header=(root/'engine/include/MoviePlayer.h').read_text();tables=[]
        for name in ('movie32table','movie56table'):
            body=re.search(r'int '+name+r'\[STAGE_COUNT\] = \{(.*?)\};',source,re.S).group(1)
            ids=re.findall(r'\b(DEMOID_\w+)\s*,',body);tables.append([int(re.search(r'\b'+key+r'\s*=\s*(\d+)',header).group(1)) for key in ids])
        self.assertEqual(len(tables[0]),len(tables[1]))
        code='#include <cassert>\nstruct MovieInfo{unsigned mMovieIndex;void* mNext;};\nconst int STAGE_COUNT='+str(len(tables[0]))+';\n'
        for name,values in zip(('movie32table','movie56table'),tables):code+='int '+name+'[]={'+','.join(map(str,values))+'};\n'
        code+='struct Fixture{struct {void* mChild;} mPlayInfoList;int accepted=0;void request(){\n'+GUARD+'++accepted;}};\n'
        blocked=sorted(set(sum(tables,[])))
        code+='int main(){int blocked[]={'+','.join(map(str,blocked))+'};for(unsigned id=0;id<120;++id){MovieInfo info{id,nullptr};Fixture f{{&info}};f.request();bool deny=false;for(int x:blocked)if(id==unsigned(x))deny=true;assert(f.accepted==!deny);}Fixture empty{{nullptr}};empty.request();assert(empty.accepted==1);MovieInfo bad{unsigned(blocked[0]),nullptr},intro{40,&bad};Fixture concurrent{{&intro}};concurrent.request();assert(concurrent.accepted==0);}\n'
        parent=root/'output/p2-lifecycle-batch';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='guard-test-',dir=parent) as folder:
            p=Path(folder);(p/'test.cpp').write_text(code);env=dict(os.environ,PATH=str(compiler.parent)+';'+os.environ['PATH']);subprocess.run([str(compiler),'-std=c++17',str(p/'test.cpp'),'-o',str(p/'test.exe')],check=True,capture_output=True,env=env);subprocess.run([str(p/'test.exe')],check=True,capture_output=True,env=env)
    def test_native_evidence_requires_intro_and_no_stale_draw(self):
        from experimental.pikmin2_tank_skip_guard import analyze_fixed
        valid='TANK_NORMAL_SKIP_REQUEST movie=40 name=cinemas/demo40.cin\ndataDir/cinemas/demo56.cin\nTANK_DAYEND_SKIP_BLOCKED movie=56'
        self.assertEqual(analyze_fixed(valid,True)['blocked_movies'],[56])
        for text in (valid+'\n[PC GX] DESYNC #1',valid.replace('movie=40','movie=41'),valid+'\nTANK_HEAP_DRAW original=ab now=cd name=tekis/tank/tank.mod'):
            with self.assertRaises(ValueError):analyze_fixed(text,True)
