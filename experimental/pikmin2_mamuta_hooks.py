"""Generate, never apply, exact native integration changes for #230."""
from pathlib import Path
import difflib

def hook_patch(engine: Path) -> str:
    specs = {
        'CMakeLists.txt': [('    pc_port/pc_p2_tank.cpp', '    pc_port/pc_p2_mamuta.cpp\n    pc_port/pc_p2_tank.cpp')],
        'pc_port/pc_p2_preview.cpp': [('#include "pc_p2_tank.h"', '#include "pc_p2_mamuta.h"\n#include "pc_p2_tank.h"'), ('    pc_p2_tank_setup();', '    pc_p2_mamuta_setup();\n    pc_p2_tank_setup();')],
        'src/plugPikiNakata/tekibteki.cpp': [('#include "pc_p2_tank.h"', '#include "pc_p2_mamuta.h"\n#include "pc_p2_tank.h"'), ('!pc_p2_frog_draw(this, gfx, mat, true)', '!pc_p2_mamuta_draw(this, gfx, mat, true) && !pc_p2_frog_draw(this, gfx, mat, true)'), ('!pc_p2_frog_draw(this, gfx, onCamMtx)', '!pc_p2_mamuta_draw(this, gfx, onCamMtx) && !pc_p2_frog_draw(this, gfx, onCamMtx)')],
        'src/plugPikiNakata/tekimgr.cpp': [('#include "pc_p2_tank.h"', '#include "pc_p2_mamuta.h"\n#include "pc_p2_tank.h"'), ('pc_p2_tank_reset();', 'pc_p2_mamuta_reset(); pc_p2_tank_reset();'), ('pc_p2_tank_forget(teki);', 'pc_p2_mamuta_forget(teki); pc_p2_tank_forget(teki);')],
    }
    expected_hooks = {
        'CMakeLists.txt': {'pc_port/pc_p2_mamuta.cpp': 1},
        'pc_port/pc_p2_preview.cpp': {'#include "pc_p2_mamuta.h"': 1, 'pc_p2_mamuta_setup();': 1},
        'src/plugPikiNakata/tekibteki.cpp': {'#include "pc_p2_mamuta.h"': 1, '!pc_p2_mamuta_draw(this, gfx, mat, true)': 1, '!pc_p2_mamuta_draw(this, gfx, onCamMtx)': 1},
        'src/plugPikiNakata/tekimgr.cpp': {'#include "pc_p2_mamuta.h"': 1, 'pc_p2_mamuta_reset();': 3, 'pc_p2_mamuta_forget(teki);': 1},
    }
    sources = {path: (engine / path).read_text(encoding='utf-8') for path in specs}
    # The later opt-in bury module is independent of these visual hooks.
    # Recognize its one exact build entry without accepting unknown/duplicate hooks.
    audited = dict(sources)
    rules = '    pc_port/pc_p2_mamuta_rules.cpp\n'
    cmake = audited['CMakeLists.txt']
    if cmake.count('pc_p2_mamuta_rules') != cmake.count(rules) or cmake.count(rules) > 1:
        raise ValueError('CMakeLists.txt: partial or conflicting Mamuta rules integration')
    audited['CMakeLists.txt'] = cmake.replace(rules, '')
    if any('pc_p2_mamuta' in source for source in audited.values()):
        for path, hooks in expected_hooks.items():
            source = audited[path]
            if any(source.count(hook) != count for hook, count in hooks.items()) or source.count('pc_p2_mamuta') != sum(hooks.values()):
                raise ValueError(f'{path}: partial or conflicting Mamuta integration')
        return ''
    patch = ''
    for path, replacements in specs.items():
        before = sources[path]
        after = before
        for old, new in replacements:
            expected = 3 if path.endswith('tekimgr.cpp') and old == 'pc_p2_tank_reset();' else 1
            if after.count(old) != expected:
                raise ValueError(f'{path}: expected {expected} unique hook anchors: {old}')
            after = after.replace(old, new)
        patch += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/'+path, tofile='b/'+path))
    return patch
