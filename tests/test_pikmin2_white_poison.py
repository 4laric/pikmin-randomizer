from pathlib import Path

import pytest

from experimental.pikmin2_white_poison import extract, generator_id, source_profile


def parameters(proper):
    # The same key in a general block must not be mistaken for proper fp02.
    return ('{\n{fp02} 4 300\n{_eof}\n}\n' * 2
            + '{\n' + proper + '\n{_eof}\n}\n').encode()


def test_poison_reads_proper_block_and_rejects_header_default():
    profile = source_profile(parameters('{fp01} 4 30\n{fp02} 4 750'))
    assert profile['poison_damage'] == 750
    for proper in ('{fp01} 4 30\n{fp02} 4 300', '{fp02} 4 750',
                   '{fp01} 4 30\n{fp02} 4 750\n{fp02} 4 750'):
        with pytest.raises(ValueError):
            source_profile(parameters(proper))


@pytest.mark.parametrize('token', ['-1', '+1', '4294967296', '1.0', '1x', ''])
def test_generator_tokens_reject_signed_or_invalid(token):
    with pytest.raises(ValueError):
        generator_id(token)


def test_generator_boundaries():
    assert generator_id('0') == 0
    assert generator_id('4294967295') == 0xffffffff


@pytest.mark.parametrize('ids', [[], [-1], [True], [1, 1], [0x100000000], list(range(33))])
def test_bad_bindings_fail_before_disc_access(tmp_path, ids):
    with pytest.raises(ValueError):
        extract(tmp_path / 'missing.iso', tmp_path / 'out', ids)


def test_local_retail_poison_config(tmp_path):
    iso = Path('output/pikmin2-runtime/pikmin2-source-test.iso')
    if not iso.exists():
        pytest.skip('Requires local user-owned GPVE01 disc')
    import hashlib
    report = extract(iso, tmp_path / 'profile', [26])
    config = (tmp_path / 'profile/p2-white-poison.txt').read_bytes()
    assert config == b'P2_WHITE_POISON_1\ndamage 750\npredator_generators 1 26\n'
    assert report['poison_damage'] == 750
    assert report['config_sha256'] == hashlib.sha256(config).hexdigest()
    assert report['archive_sha256'] == '3618455a8561f1e1b0aad0253a75a69fae1fe3a47160d1c1efa294b0ddeb2a84'
    assert report['member_sha256'] == '12abc387cf05d4bf2c53f453694a268bec4d00e4fee33b03626d0d071b0f80c4'
