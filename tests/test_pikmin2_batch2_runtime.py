"""Batch-4 arena runtime probe instrumentation tests (#352, #353, #312)."""
import pytest

import experimental.pikmin2_batch2_runtime as runtime

SYNTHETIC = ("class RoomApp : public PlugPikiApp {\n"
             " int frames=0;\n"
             "};\n"
             "int main(int argc,char** argv) { return 0; }\n")


def test_instrument_replaces_roomapp_and_keeps_main():
    source = runtime.instrument(SYNTHETIC)
    assert 'class RoomApp : public PlugPikiApp {' in source
    assert 'int main(' in source
    assert 'P2_BATCH4_BIRTH' in source and 'PASS P2_BATCH4_RUNTIME' in source
    assert source.index('P2_BATCH4_BIRTH') < source.index('int main(')
    assert 'int frames=0;\n};' not in source


def test_instrument_rejects_missing_anchor():
    with pytest.raises(ValueError):
        runtime.instrument('int main() { return 0; }\n')


def test_instrument_is_deterministic():
    assert runtime.instrument(SYNTHETIC) == runtime.instrument(SYNTHETIC)
