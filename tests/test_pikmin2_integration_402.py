"""Execute the imported native policies and the reconciled cave entry contract."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NativeIntegrationTests(unittest.TestCase):
    def test_imported_policies_and_tai_lifecycle(self):
        compiler = shutil.which('g++')
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        root = Path(__file__).resolve().parents[1] / 'engine'
        cases = {
            'purple': [root / 'tools/p2_purple_impact_policy_test.cpp'],
            'white': [root / 'tools/test_p2_white_policy.cpp'],
            'tai': [root / 'tools/p2_purple_tai_transition_test.cpp', root / 'src/plugPikiNakata/tai.cpp'],
        }
        with tempfile.TemporaryDirectory() as temp:
            for name, sources in cases.items():
                with self.subTest(policy=name):
                    output = Path(temp) / (name + '.exe')
                    command = [compiler, '-std=c++17', '-I' + str(root / 'pc_port')]
                    if name == 'tai': command += ['-I' + str(root / 'tools/purple_tai_stubs')]
                    subprocess.run(command + list(map(str, sources)) + ['-o', str(output)],
                                   check=True, capture_output=True, timeout=60)
                    subprocess.run([str(output)], check=True, capture_output=True, timeout=15)

    def test_cave_v2_keeps_beasts_profiles_separate(self):
        compiler = shutil.which('g++')
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        root = Path(__file__).resolve().parents[1] / 'engine'
        code = r'''
#include "pc_p2_cave_entry_policy.h"
#include <cassert>
int main() {
 const std::string shortToken(32,'a'), longToken(64,'a');
 for (auto version : {"P2_CAVE_ENTRY_1", "P2_CAVE_ENTRY_2"}) {
  for (int floor : {1,2}) assert(p2_cave_entry_profile(version,floor,shortToken)==P2CaveEntryProfile::Tutorial);
  assert(p2_cave_entry_profile(version,3,shortToken)==P2CaveEntryProfile::Invalid);
  assert(p2_cave_entry_profile(version,2,longToken)==P2CaveEntryProfile::Invalid);
 }
 assert(p2_cave_entry_profile("P2_BEASTS_ENTRY_1",2,longToken)==P2CaveEntryProfile::BeastsFloor2);
 assert(p2_cave_entry_profile("P2_BEASTS_FLOOR3_ENTRY_1",3,longToken)==P2CaveEntryProfile::BeastsFloor3);
 assert(p2_cave_entry_profile("P2_BEASTS_FLOOR4_ENTRY_1",4,longToken)==P2CaveEntryProfile::BeastsFloor4);
 assert(p2_cave_entry_profile("P2_BEASTS_ENTRY_1",2,shortToken)==P2CaveEntryProfile::Invalid);
 assert(p2_cave_entry_profile("P2_CAVE_ENTRY_3",1,shortToken)==P2CaveEntryProfile::Invalid);
 assert(p2_cave_entry_profile("P2_CAVE_ENTRY_2",1,std::string(32,'z'))==P2CaveEntryProfile::Invalid);
}
'''
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'entry.cpp'; output = Path(temp) / 'entry.exe'
            source.write_text(code, encoding='utf-8')
            subprocess.run([compiler, '-std=c++17', '-I' + str(root / 'pc_port'), str(source), '-o', str(output)],
                           check=True, capture_output=True, timeout=60)
            subprocess.run([str(output)], check=True, capture_output=True, timeout=15)
