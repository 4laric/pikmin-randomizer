import shutil
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from experimental.pikmin2_mamuta_hooks import hook_patch

ROOT = Path(__file__).resolve().parents[1]
class MamutaNativeTests(unittest.TestCase):
    def test_actual_policy_compiles_and_controls(self):
        compiler = shutil.which('g++') or 'C:/msys64/mingw64/bin/g++.exe'
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'policy.cpp'
            source.write_text('''#include "pc_p2_mamuta_policy.h"
#include <cassert>
int main() {
 for (int t=0;t<50;++t) for(int m=-1;m<30;++m) {
  if(t!=24) {assert(p2mamuta::anchor(t,m,false)==-1);assert(p2mamuta::anchor(t,m,true)==-1);}
 }
 assert(p2mamuta::anchor(24,2,false)==0);
 assert(p2mamuta::anchor(24,0,false)==1);
 assert(p2mamuta::anchor(24,14,true)==1);
 for(int m: {10,11,12}) assert(p2mamuta::anchor(24,m,false)==2);
 for(int m: {1,3,4,5,6,7,8,9,13,14,-1}) assert(p2mamuta::anchor(24,m,false)==-1);
}'''.replace('#include <cassert>', '#include <cassert>\n#include <initializer_list>'))
            exe = Path(tmp)/'policy.exe'
            env=dict(os.environ, PATH=str(Path(compiler).parent)+os.pathsep+os.environ['PATH'])
            subprocess.run([compiler,'-std=c++17',str(source),'-I'+str(ROOT/'experimental/native_mamuta'),'-o',str(exe)],check=True,env=env)
            subprocess.run([str(exe)],check=True)

    def test_exact_hooks_and_no_gameplay_mutation(self):
        patch=hook_patch(ROOT/'engine')
        if patch:
            self.assertEqual(patch.count('+    pc_p2_mamuta_setup();'),1)
            self.assertEqual(patch.count('pc_p2_mamuta_forget(teki)'),1)
            self.assertIn('pc_p2_mamuta_draw(this, gfx, mat, true)',patch)
            self.assertIn('pc_p2_mamuta_draw(this, gfx, onCamMtx)',patch)
        module=(ROOT/'experimental/native_mamuta/pc_p2_mamuta.cpp').read_text()
        self.assertNotIn('InteractBury',module)
        self.assertNotIn('Shijimi',module)
        self.assertIn('actors.erase(actor)',module)
        self.assertIn('word!="Miulin"',module)
        self.assertIn('found!=wanted',module)

    def test_integrated_partial_and_duplicate_hooks(self):
        files = ['CMakeLists.txt','pc_port/pc_p2_preview.cpp','src/plugPikiNakata/tekibteki.cpp','src/plugPikiNakata/tekimgr.cpp','pc_port/pc_p2_teki_lifetime.cpp']
        with tempfile.TemporaryDirectory() as tmp:
            engine=Path(tmp)
            for name in files:
                target=engine/name; target.parent.mkdir(parents=True,exist_ok=True)
                source=(ROOT/'engine'/name).read_text(encoding='utf-8')
                # Normalize to a pre-integration fixture without touching shared files.
                source=source.replace('#include "pc_p2_mamuta.h"\n','').replace('    pc_port/pc_p2_mamuta.cpp\n','').replace('    pc_p2_mamuta_setup();\n','').replace('pc_p2_mamuta_reset(); ','').replace('pc_p2_mamuta_forget(teki); ','').replace('!pc_p2_mamuta_draw(this, gfx, mat, true) && ','').replace('!pc_p2_mamuta_draw(this, gfx, onCamMtx) && ','')
                source=source.replace('\tpc_p2_mamuta_forget(actor);\n','').replace('\tpc_p2_mamuta_reset();\n','')
                target.write_text(source,encoding='utf-8')
            patch=hook_patch(engine)
            self.assertTrue(patch)
            patchfile=engine/'integration.patch';patchfile.write_text(patch,encoding='utf-8')
            subprocess.run(['git','apply','--unsafe-paths',str(patchfile)],cwd=engine,check=True)
            self.assertEqual(hook_patch(engine),'')
            cmake=engine/'CMakeLists.txt'; original=cmake.read_text(encoding='utf-8')
            rules='    pc_port/pc_p2_mamuta_rules.cpp\n'
            cmake.write_text(original.replace(rules,'')+rules,encoding='utf-8')
            self.assertEqual(hook_patch(engine),'')
            cmake.write_text(original.replace(rules,'')+rules+rules,encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'conflicting'): hook_patch(engine)
            cmake.write_text(original,encoding='utf-8')
            target=engine/'pc_port/pc_p2_preview.cpp'; source=target.read_text(encoding='utf-8')
            target.write_text(source.replace('pc_p2_mamuta_setup();',''),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'partial'): hook_patch(engine)
            target.write_text(source+'\npc_p2_mamuta_setup();\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'conflicting'): hook_patch(engine)

if __name__=='__main__': unittest.main()
