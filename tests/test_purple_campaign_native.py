"""Compile the production Violet binding parser; no engine/runtime acceptance."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class VioletPolicyTests(unittest.TestCase):
    def test_stage_generator_binding_and_malformed_input(self):
        native = Path(os.environ.get('PIKMIN_NATIVE_SOURCE', Path(__file__).resolve().parents[1] / 'native'))
        compiler = shutil.which('g++')
        if not compiler or not (native / 'pc_port/pc_p2_purple_campaign_policy.h').exists():
            self.skipTest('Set PIKMIN_NATIVE_SOURCE and supply g++ for production-header test')
        source = r'''
#include "pc_p2_purple_campaign_policy.h"
#include <sstream>
#include <cassert>
int main() {
    using namespace p2purplecampaign;
    Config c;
    std::istringstream good("P2_PURPLE_CAMPAIGN_1 2\n0 100\n1 200\n");
    assert(parse(good,c));
    assert(c.matches(0,100)); assert(c.matches(1,200));
    assert(!c.matches(0,200)); assert(!c.matches(2,200)); assert(!c.matches(0,0));
    const char* bad[]={"", "P2_PURPLE_CAMPAIGN_1 0", "P2_PURPLE_CAMPAIGN_1 6",
        "P2_PURPLE_CAMPAIGN_1 1 0 0", "P2_PURPLE_CAMPAIGN_1 1 5 100",
        "P2_PURPLE_CAMPAIGN_1 1 -1 100", "P2_PURPLE_CAMPAIGN_1 1 0 4294967296",
        "P2_PURPLE_CAMPAIGN_1 2 0 100 0 101", "P2_PURPLE_CAMPAIGN_1 1 0 100 garbage",
        "P2_PURPLE_CAMPAIGN_1 1 0 -1", "P2_PURPLE_CAMPAIGN_1 2 0 100"};
    for(auto text:bad){ std::istringstream in(text); assert(!parse(in,c)); assert(c.matches(1,200)); }
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'policy.cpp'; file.write_text(source)
            exe = Path(tmp) / 'policy.exe'
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(native / 'pc_port'),
                            str(file), '-o', str(exe)], check=True, capture_output=True)
            subprocess.run([str(exe)], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
