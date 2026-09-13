import tempfile,unittest,subprocess,os
from pathlib import Path
class NativeTests(unittest.TestCase):
 def test_typed_config(self):
  root=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(r'''#include "pc_p2_kogane_policy.h"
#include <sstream>
#include <cassert>
int main(){p2kogane::Config c;std::string tail=" move 2 12 0 11 wait 2 15 0 14 damage 2 30 0 29";
std::istringstream good("P2_KOGANE_NATIVE_1 karada 0 actors 3 219001 9 219002 10 219003 11"+tail);assert(p2kogane::read(good,c));assert(c.ids.at(219002)==10);assert(p2kogane::karada(9)==60&&p2kogane::karada(10)==100&&p2kogane::karada(11)==15);
for(const char* bad:{"P2_KOGANE_ACTORS_1 3 1 2 3","P2_KOGANE_NATIVE_1 karada 0 actors 1 1 12","P2_KOGANE_NATIVE_1 karada 0 actors 2 1 9 1 10"}){std::istringstream in(std::string(bad)+tail);assert(!p2kogane::read(in,c));}
}''')
   env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ['PATH'])
   subprocess.run(['C:/msys64/mingw64/bin/g++.exe','-std=c++17','-I'+str(root/'engine/pc_port'),'-I'+str(root/'native-patches/kogane'),str(p/'test.cpp'),'-o',str(p/'test.exe')],check=True,env=env,capture_output=True)
   subprocess.run([str(p/'test.exe')],check=True,env=env)
if __name__=='__main__':unittest.main()
