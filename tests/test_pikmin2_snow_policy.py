import pytest
from pathlib import Path
import os
import shutil
import subprocess
from experimental.pikmin2_snow_policy import animation_events,parameter_groups,validate_policy,install

PARAMS='''{
{s000} 4 0.5
{_eof}
}
{
{fp00} 4 150
{fp01} 4 20
{_eof}
}
{
{fp01} 4 2
{_eof}
}
'''
ANIM='''2
{
Z:\\source\\attack.bca
attack.bca
8 2
88 3
-1
}
{
Z:\\source\\dead.bca
dead.bca
-1
}
'''


def test_parameter_scopes_do_not_confuse_repeated_proper_ids():
    groups=parameter_groups(PARAMS)
    assert groups[1]['fp00']==150 and groups[1]['fp01']==20 and groups[2]['fp01']==2


@pytest.mark.parametrize('text',[PARAMS.replace('{fp00} 4 150','{fp00} 4 150\n{fp00} 4 1'),
    PARAMS.replace('{_eof}','',1),PARAMS.replace('4 150','4 nan'),PARAMS+'garbage',PARAMS[:-2]])
def test_bad_parameter_data_fails(text):
    with pytest.raises(ValueError):parameter_groups(text)


def test_events_preserve_source_frames_and_no_event_death():
    assert animation_events(ANIM)=={'attack.bca':[{'frame':8,'type':2},{'frame':88,'type':3}], 'dead.bca':[]}


@pytest.mark.parametrize('text',[ANIM+'garbage',ANIM.replace('88 3','88'),ANIM.replace('88 3','7 3'),
                                ANIM.replace('-1','',1),ANIM.replace('dead.bca','attack.bca')])
def test_bad_animation_events_fail(text):
    with pytest.raises(ValueError):animation_events(text)


def test_policy_is_explicit_and_only_accepts_supported_source_value(tmp_path):
    assert validate_policy('P2_SNOW_POLICY_1\nhealth 150\n')==150
    for text in ('','P2_SNOW_POLICY_1 health 100','P2_SNOW_POLICY_1 health 150 extra','P2_SNOW_POLICY_2 health 150'):
        with pytest.raises(ValueError):validate_policy(text)
    imported=tmp_path/'import';imported.mkdir();(imported/'p2-snow-policy.txt').write_text('P2_SNOW_POLICY_1 health 150')
    run=tmp_path/'run';run.mkdir()
    with pytest.raises(ValueError):install(imported,run)
    assert not (run/'p2-snow-policy.txt').exists()
    (run/'p2-snow.txt').touch();(run/'p2-snow-actors.txt').touch()
    install(imported,run)
    assert validate_policy((run/'p2-snow-policy.txt').read_text())==150


def test_native_policy_isolation_and_recycled_address_teardown(tmp_path):
    compiler=shutil.which('g++') or 'C:/msys64/mingw64/bin/g++.exe'
    if not Path(compiler).is_file():pytest.skip('C++ compiler unavailable')
    source=tmp_path/'policy.cpp'
    source.write_text(r'''
#include "pc_p2_snow_policy.h"
#include <sstream>
#include <cassert>
int main() {
    int snow=0,p1=0;
    P2SnowHealthPolicy policy;
    policy.bind(&snow);
    assert(policy.life(&snow,123)==123); // no config, including known address
    std::stringstream config("P2_SNOW_POLICY_1 health 150");
    assert(policy.read(config));policy.bind(&snow);
    assert(policy.life(&snow,100)==150);
    assert(policy.life(&p1,123)==123); // same P1 family remains untouched
    policy.bind(&p1);policy.forget(&snow);
    assert(policy.life(&snow,123)==123 && policy.life(&p1,80)==150);
    policy.reset();
    assert(policy.life(&snow,80)==80); // reused pool address cannot inherit health
    std::stringstream next("P2_SNOW_POLICY_1 health 150");
    assert(policy.read(next));
    assert(policy.life(&snow,80)==80); // policy alone does not restore stale binding
    policy.bind(&p1);assert(policy.life(&p1,80)==150);
    std::stringstream invalid("P2_SNOW_POLICY_1 health 150 extra");
    assert(!policy.read(invalid));assert(policy.life(&p1,80)==80);
}
''')
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    exe=tmp_path/'policy.exe';include=Path(__file__).resolve().parents[1]/'native/pc_port'
    subprocess.run([compiler,'-std=c++17','-I',str(include),str(source),'-o',str(exe)],env=env,check=True,capture_output=True)
    subprocess.run([str(exe)],env=env,check=True,capture_output=True)
