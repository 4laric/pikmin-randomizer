import tempfile,unittest,subprocess,os
from pathlib import Path

import pytest

from experimental import pikmin2_kogane_native as native

class NativeTests(unittest.TestCase):
 def test_typed_config(self):
  root=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(r'''#include "pc_p2_kogane_policy.h"
#include <sstream>
#include <cassert>
int main(){p2kogane::Config c;std::string tail=" move 2 12 0 11 wait 2 15 0 14 damage 2 30 0 29";
std::istringstream good("P2_KOGANE_NATIVE_1 karada 0 actors 3 219001 9 219002 10 219003 11"+tail);assert(p2kogane::read(good,c));assert(c.ids.at(219002)==10);assert(c.treasures.empty());assert(p2kogane::karada(9)==60&&p2kogane::karada(10)==100&&p2kogane::karada(11)==15);
std::istringstream treasure("P2_KOGANE_NATIVE_1 karada 0 actors 3 219001 9 219002 10 219003 11 treasure 219001 1 treasure 219002 5"+tail);assert(p2kogane::read(treasure,c));assert(c.treasures.size()==2&&c.treasures.at(219001)==1&&c.treasures.at(219002)==5&&!c.treasures.count(219003));
for(const char* bad:{"P2_KOGANE_ACTORS_1 3 1 2 3","P2_KOGANE_NATIVE_1 karada 0 actors 1 1 12","P2_KOGANE_NATIVE_1 karada 0 actors 2 1 9 1 10"}){std::istringstream in(std::string(bad)+tail);assert(!p2kogane::read(in,c));}
for(const char* bad:{"P2_KOGANE_NATIVE_1 karada 0 actors 1 219001 9 treasure 219001 3","P2_KOGANE_NATIVE_1 karada 0 actors 1 219001 9 treasure 219001","P2_KOGANE_NATIVE_1 karada 0 actors 2 219001 9 219002 10 treasure 219999 1","P2_KOGANE_NATIVE_1 karada 0 actors 1 219001 9 treasure 219001 1 treasure 219001 5"}){std::istringstream in(std::string(bad)+tail);assert(!p2kogane::read(in,c));}
}''')
   env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ['PATH'])
   subprocess.run(['C:/msys64/mingw64/bin/g++.exe','-std=c++17','-I'+str(root/'engine/pc_port'),'-I'+str(root/'native-patches/kogane'),str(p/'test.cpp'),'-o',str(p/'test.exe')],check=True,env=env,capture_output=True)
   subprocess.run([str(p/'test.exe')],check=True,env=env)


def test_treasure_lines_round_trip_the_native_token():
    assert native.treasure_lines([(219001, 1), (219002, 5)], [219001, 219002, 219003]) == \
        ['treasure 219001 1', 'treasure 219002 5']
    assert native.treasure_lines([], [219001]) == []


def test_treasure_lines_reject_malformed_entries():
    with pytest.raises(ValueError, match='1 or 5'):
        native.treasure_lines([(219001, 3)], [219001])
    with pytest.raises(ValueError, match='registered actor'):
        native.treasure_lines([(219999, 1)], [219001])
    with pytest.raises(ValueError, match='Duplicate'):
        native.treasure_lines([(219001, 1), (219001, 5)], [219001])


if __name__=='__main__':unittest.main()
