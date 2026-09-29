"""Compiled input/policy/adapter regression; not a rendered gameplay claim."""
import subprocess

from test_pikmin2_captain_adapter import _compiler, _compile_env, _source_root


def test_captain_switch_controls(tmp_path):
    port, sources = _source_root('pc_p2_captain_switch_policy.h', 'test_p2_captain_switch.cpp')
    assert port is not None, 'captain switch candidate must be present'
    compiler = _compiler()
    assert compiler is not None, 'g++ is required for this acceptance check'
    exe = tmp_path / 'captain-switch.exe'
    subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    '-I', str(port), str(sources / 'test_p2_captain_switch.cpp'),
                    '-o', str(exe)], check=True, capture_output=True, text=True,
                   env=_compile_env(compiler))
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30,
                            env=_compile_env(compiler))
    assert result.returncode == 0, result.stderr
    assert 'PASS P2_CAPTAIN_SWITCH' in result.stdout
