import subprocess
import os
from pathlib import Path
import pytest
from experimental.pikmin2_cave_nav_diagnostics import HEADER,instrument


def test_native_rate_limits_reset_and_wrap(tmp_path):
    compiler=Path('C:/msys64/mingw64/bin/g++.exe')
    if not compiler.exists():pytest.skip('MinGW unavailable')
    (tmp_path/'rate.h').write_text(HEADER)
    (tmp_path/'test.cpp').write_text('''#include "rate.h"
#include <cassert>
int main(){P2CaveNavRate r;assert(!r.due(0));r.reset(true);assert(r.due(0));assert(!r.due(1999));assert(r.due(2000));for(unsigned i=2;i<120;++i)assert(r.due(i*2000));assert(!r.due(240000));r.reset(false);assert(!r.due(0));r.reset(true);assert(r.due(0xfffffff0));assert(!r.due(4));assert(r.due(2000));}
''')
    exe=tmp_path/'test.exe'
    env=dict(os.environ,PATH=str(compiler.parent)+';'+os.environ.get('PATH',''))
    subprocess.run([str(compiler),'-std=c++17',str(tmp_path/'test.cpp'),'-o',str(exe)],check=True,capture_output=True,env=env)
    subprocess.run([str(exe)],check=True,capture_output=True,env=env)


def test_changes_only_presentation_and_logging():
    source='#include "pc_p2_cave.h"\nShape* transitionShape=nullptr;\nvoid notice(const char* text) {}\nvoid pc_p2_cave_setup(){ }\nbool pc_p2_cave_checkpoint(bool confirm){ return confirm; }\nvoid pc_p2_cave_tick(){ }\n    static bool logged=false;\n    if(!logged){std::puts("P2_CAVE_MARKER_DRAW");logged=true;}\n'
    result=instrument(source)
    before=source[source.index('bool pc_p2_cave_checkpoint'):source.index('void pc_p2_cave_tick')]
    after=result[result.index('bool pc_p2_cave_checkpoint'):result.index('void pc_p2_cave_tick')]
    assert before==after
    assert result.count('navigationDiagnostic();')==1
    assert 'PIKMIN_CAVE_NAV_DIAGNOSTICS' in result
    with pytest.raises(ValueError):instrument(result)
