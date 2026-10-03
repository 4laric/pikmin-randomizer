"""Combined P1/P2 recovery accepts its own bootstrap, not foreign modes."""
import pytest
from randomizer.runner import NativeRun
from randomizer.seed import generate
from randomizer.session import Session


def mixed_manifest(**options):
    return generate('1153', campaign_enemies=True, p2_enemies=True,
                    p2_species='playable', p2_checks=True, **options)


def journal(tmp_path, manifest):
    session = Session(manifest, tmp_path)
    run = NativeRun(session)
    (run.directory / 'checks.txt').write_text('0\n', encoding='ascii')
    return session, run


@pytest.mark.parametrize('proxy_tier', [None, 'declared'])
def test_mixed_bootstrap_recovers_native_check_after_restart(tmp_path, proxy_tier):
    manifest = mixed_manifest(**({'p2_proxy_tier': proxy_tier} if proxy_tier else {}))
    session, run = journal(tmp_path, manifest)
    assert 'ENEMY_COMPOSITION 1 campaign\n' in run.bootstrap.read_text()
    recovered = Session(manifest, tmp_path)
    assert recovered.data['checked'] == [session.names[0]]
    assert Session(manifest, tmp_path).data['checked'] == [session.names[0]]


@pytest.mark.parametrize('replacement', ['', 'ENEMY_COMPOSITION 1 slots\n',
    'ENEMY_COMPOSITION 2 campaign\n',
    'ENEMY_COMPOSITION 1 campaign\nENEMY_COMPOSITION 1 campaign\n'])
def test_mixed_journal_rejects_missing_changed_or_duplicate_composition(tmp_path, replacement):
    manifest = mixed_manifest()
    _, run = journal(tmp_path, manifest)
    run.bootstrap.write_text(run.bootstrap.read_text().replace(
        'ENEMY_COMPOSITION 1 campaign\n', replacement))
    with pytest.raises(ValueError):
        Session(manifest, tmp_path)


def test_legacy_journal_rejects_unrequested_composition(tmp_path):
    manifest = generate('legacy-journal', campaign_enemies=True)
    _, run = journal(tmp_path, manifest)
    run.bootstrap.write_text(run.bootstrap.read_text().replace(
        'ENEMY_CAMPAIGN ', 'ENEMY_COMPOSITION 1 campaign\nENEMY_CAMPAIGN '))
    with pytest.raises(ValueError):
        Session(manifest, tmp_path)
