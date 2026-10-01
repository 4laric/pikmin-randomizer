"""Seed-bound second-captain protocol; no game launch or injected admission."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from randomizer.runner import NativeRun
from randomizer.seed import fingerprint, generate, validate
from randomizer.session import Session


CAPABILITY = 'p2-second-captain-v1'


def p2_manifest(**options):
    return generate('second-captain-contract', p2_enemies=True, p2_species=[2],
                    starting_flarlic=2, **options)


def test_opt_in_is_valid_and_fingerprint_bound():
    legacy = p2_manifest()
    enabled = p2_manifest(p2_second_captain=True)
    validate(enabled)
    assert enabled['p2_second_captain'] is True
    assert enabled['capabilities'].count(CAPABILITY) == 1
    assert fingerprint(enabled) != fingerprint(legacy)
    assert CAPABILITY not in legacy['capabilities']
    assert 'p2_second_captain' not in legacy


@pytest.mark.parametrize('p2', [False, True])
def test_false_preserves_legacy_manifest_exactly(p2):
    options = {'p2_enemies': True, 'p2_species': [2]} if p2 else {}
    assert generate('legacy-captain', **options) == generate(
        'legacy-captain', p2_second_captain=False, **options)


@pytest.mark.parametrize('value', [None, 0, 1, 'true', [], {}])
def test_non_boolean_option_rejected(value):
    with pytest.raises(ValueError):
        p2_manifest(p2_second_captain=value)


def test_opt_in_requires_p2_seed():
    with pytest.raises(ValueError):
        generate('not-a-p2-seed', p2_second_captain=True)


@pytest.mark.parametrize('mutation', ['missing-capability', 'missing-field',
                                     'false-field', 'integer-field'])
def test_manifest_field_and_capability_must_agree(mutation):
    manifest = copy.deepcopy(p2_manifest(p2_second_captain=True))
    if mutation == 'missing-capability':
        manifest['capabilities'].remove(CAPABILITY)
    elif mutation == 'missing-field':
        del manifest['p2_second_captain']
    else:
        manifest['p2_second_captain'] = False if mutation == 'false-field' else 1
    with pytest.raises(ValueError):
        validate(manifest)


@pytest.mark.parametrize('purple', [False, True])
def test_bootstrap_suffix_and_real_journal_recovery(tmp_path, purple):
    manifest = p2_manifest(p2_second_captain=True, p2_purple_campaign=purple)
    session = Session(manifest, tmp_path)
    run = NativeRun(session, purple_campaign=purple)
    text = run.bootstrap.read_text()
    suffix = ('PURPLE 1\n' if purple else '') + 'CAPTAINS 2\nEND\n'
    assert text.endswith(suffix)
    assert text.count('CAPTAINS') == 1
    (run.directory / 'checks.txt').write_text('0\n')
    recovered = Session(manifest, tmp_path)
    assert recovered.names[0] in recovered.data['checked']
    # Re-reading an unchanged journal must not duplicate the recovered check.
    again = Session(manifest, tmp_path)
    assert again.data['checked'].count(again.names[0]) == 1


@pytest.mark.parametrize('purple', [False, True])
@pytest.mark.parametrize('replacement', ['', 'CAPTAINS 1\n', 'CAPTAINS 3\n',
                                         'CAPTAINS 02\n', 'CAPTAINS 2\nCAPTAINS 2\n'])
def test_recovery_rejects_missing_or_malformed_suffix(tmp_path, purple, replacement):
    manifest = p2_manifest(p2_second_captain=True, p2_purple_campaign=purple)
    run = NativeRun(Session(manifest, tmp_path), purple_campaign=purple)
    original = run.bootstrap.read_text()
    assert original.endswith('CAPTAINS 2\nEND\n')
    run.bootstrap.write_text(original.replace('CAPTAINS 2\n', replacement))
    (run.directory / 'checks.txt').write_text('0\n')
    with pytest.raises(ValueError):
        Session(manifest, tmp_path)


def test_recovery_rejects_reordered_purple_suffix(tmp_path):
    manifest = p2_manifest(p2_second_captain=True, p2_purple_campaign=True)
    run = NativeRun(Session(manifest, tmp_path), purple_campaign=True)
    text = run.bootstrap.read_text()
    assert text.endswith('PURPLE 1\nCAPTAINS 2\nEND\n')
    run.bootstrap.write_text(text.replace('PURPLE 1\nCAPTAINS 2\n',
                                          'CAPTAINS 2\nPURPLE 1\n'))
    (run.directory / 'checks.txt').write_text('0\n')
    with pytest.raises(ValueError):
        Session(manifest, tmp_path)


def test_foreign_true_suffix_cannot_upgrade_legacy_session(tmp_path):
    manifest = p2_manifest()
    run = NativeRun(Session(manifest, tmp_path))
    text = run.bootstrap.read_text()
    assert 'CAPTAINS' not in text
    run.bootstrap.write_text(text.removesuffix('END\n') + 'CAPTAINS 2\nEND\n')
    (run.directory / 'checks.txt').write_text('0\n')
    with pytest.raises(ValueError):
        Session(manifest, tmp_path)


def test_enabled_manifest_cannot_reopen_legacy_session(tmp_path):
    Session(p2_manifest(), tmp_path).save()
    with pytest.raises(ValueError):
        Session(p2_manifest(p2_second_captain=True), tmp_path)


def test_ap_resolved_checks_keep_capability_order_and_recover(tmp_path):
    manifest = generate('captain-ap', 'ap', p2_enemies=True, p2_species=[2],
                        p2_checks=True, p2_second_captain=True)
    assert manifest['capabilities'][-2:] == ['resolved-enemy-checks-v1', CAPABILITY]
    session = Session(manifest, tmp_path)
    session.bind_ap('captain-ap-room', 0, 1)
    run = NativeRun(session)
    (run.directory / 'checks.txt').write_text('0\n')
    restored = Session(manifest, tmp_path)
    assert restored.data['ap_identity'] == ['captain-ap-room', 0, 1]
    assert restored.names[0] in restored.data['checked']


def test_cli_exposes_seed_bound_opt_in(tmp_path):
    output = tmp_path / 'manifest.json'
    result = subprocess.run(
        [sys.executable, '-m', 'randomizer', 'generate', '--seed', 'captain-cli',
         '--p2-enemies', '--p2-species', '2', '--p2-second-captain', '--output', str(output)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads(output.read_text())
    validate(manifest)
    assert manifest['p2_second_captain'] is True
    assert CAPABILITY in manifest['capabilities']
