import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import pytest
from experimental.pikmin2_kochappy_bank import HEADER,PROFILE,parse_bank,validate_files,install


def fixture(tmp_path):
    imported=tmp_path/'bank';imported.mkdir();run=tmp_path/'run';(run/'assets/dataDir/courses/pikmin2room').mkdir(parents=True)
    text=HEADER+'\n'+''.join(f'{n} 2 2 0 1\n' for n in ('wait1','move1','attack','dead','flick'))
    blob=b''.join(struct.pack('>II',tag,0) for tag in (32,34,48,65535))
    hashes={}
    for name in parse_bank(text):
        for i in range(2):
            p=imported/f'kochappy_{name}_{i:02}.mod';p.write_bytes(blob);hashes[p.name]=hashlib.sha256(blob).hexdigest()
    (imported/'p2-kochappy-bank.txt').write_text(text);(imported/'p2-kochappy-profile.txt').write_text(PROFILE)
    (imported/'kochappy-bank.json').write_text(json.dumps({'schema':1,'species':'Kochappy','source_id':1,'health':200,'motions':parse_bank(text),'file_sha256':hashes}))
    return imported,run


def test_bank_install_separate(tmp_path):
    imported,run=fixture(tmp_path);install(imported,run,[5000,0xffffffff])
    assert (run/'p2-kochappy-actors.txt').read_text().split()==['P2_KOCHAPPY_ACTORS_1','2','5000','4294967295']
    assert not (run/'p2-snow.txt').exists()
    with pytest.raises(ValueError):install(imported,run,[5000])


@pytest.mark.parametrize('bad',['duplicate','negative','overflow','bool','empty','overlap','profile','hash','identity','metadata','header','resource'])
def test_bad_install_no_write(tmp_path,bad):
    imported,run=fixture(tmp_path);ids=[5000]
    if bad in ('duplicate','negative','overflow','bool','empty'):ids={'duplicate':[1,1],'negative':[-1],'overflow':[2**32],'bool':[True],'empty':[]}[bad]
    elif bad=='overlap':(run/'p2-snow-actors.txt').write_text('P2_SNOW_ACTORS_1 1\n5000\n')
    elif bad=='profile':(imported/'p2-kochappy-profile.txt').write_text(PROFILE.replace('200','150'))
    elif bad in ('identity','metadata','hash'):
        p=imported/'kochappy-bank.json';d=json.loads(p.read_text())
        if bad=='identity':d['species']='YellowKochappy'
        elif bad=='metadata':d['motions']['wait1']['source_frames']=3
        else:d['file_sha256']['kochappy_wait1_00.mod']='0'*64
        p.write_text(json.dumps(d))
    elif bad=='header':(imported/'p2-kochappy-bank.txt').write_text((imported/'p2-kochappy-bank.txt').read_text().replace(HEADER,'P2_SNOW_2'))
    else:(imported/'kochappy_wait1_00.mod').write_bytes(b'broken')
    with pytest.raises(ValueError):install(imported,run,ids)
    assert not (run/'p2-kochappy-profile.txt').exists()
    assert not list((run/'assets/dataDir/courses/pikmin2room').iterdir())


def test_compiled_family_policy(tmp_path):
    compiler=shutil.which('g++') or ('C:/msys64/mingw64/bin/g++.exe' if Path('C:/msys64/mingw64/bin/g++.exe').exists() else None)
    if not compiler:pytest.skip('C++ compiler unavailable')
    source=tmp_path/'policy.cpp';exe=tmp_path/('policy.exe' if os.name=='nt' else 'policy')
    source.write_text(r'''
#include "pc_p2_kochappy_policy.h"
#include <cassert>
int main(){
 p2kochappy::Health health;int actor,ordinary;assert(health.life(&actor,130)==130);
 std::istringstream good("P2_KOCHAPPY_PROFILE_1 species Kochappy health 200");assert(health.read(good));
 assert(health.bind(&actor));assert(!health.bind(&actor));assert(!health.bind(nullptr));
 assert(health.life(&actor,130)==200);assert(health.life(&ordinary,130)==130);
 health.forget(&actor);assert(health.life(&actor,130)==130);assert(health.bind(&actor));health.reset();assert(health.life(&actor,130)==130);
 for(const char* text:{"P2_KOCHAPPY_PROFILE_1 species YellowKochappy health 200","P2_KOCHAPPY_PROFILE_1 species Kochappy health 150","P2_KOCHAPPY_PROFILE_1 species Kochappy health nan","P2_KOCHAPPY_PROFILE_1 species Kochappy health 200 extra"}){std::istringstream in(text);assert(!health.read(in));assert(!health.bind(&actor));}
 std::set<std::uint32_t> ids;std::istringstream idok("P2_KOCHAPPY_ACTORS_1 2 0 4294967295");assert(p2kochappy::bindings(idok,ids));assert(ids.size()==2);
 for(const char* text:{"P2_KOCHAPPY_ACTORS_1 2 1 1","P2_KOCHAPPY_ACTORS_1 1 -1","P2_KOCHAPPY_ACTORS_1 1 4294967296","P2_KOCHAPPY_ACTORS_1 1 +1","P2_KOCHAPPY_ACTORS_1 1 1 tail","P2_KOCHAPPY_ACTORS_1 0"}){std::istringstream in(text);assert(!p2kochappy::bindings(in,ids));}
 std::vector<p2animation::Clip> clips;
 std::string rows="wait1 2 2 0 1 move1 2 2 0 1 attack 2 2 0 1 dead 2 2 0 1 flick 2 2 0 1";
 std::istringstream bank("P2_KOCHAPPY_BANK_1 "+rows);assert(p2kochappy::bank(bank,clips));assert(clips.size()==5);assert(clips[3].index(0,true)==1);
 std::istringstream snow("P2_SNOW_2 "+rows);assert(!p2kochappy::bank(snow,clips));
}
''')
    env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([compiler,'-std=c++17','-I'+str(Path('native/pc_port').resolve()),str(source),'-o',str(exe)],check=True,capture_output=True,env=env)
    subprocess.run([str(exe)],check=True,capture_output=True,env=env)
