import pytest
from experimental.pikmin2_purple_motion import CLIPS,PHASE_CLIPS,validate_profile
from scripts.preview_pikmin2_emergence import _purple_motion_files,prepare

def test_retail_motion_contract():
    assert CLIPS==(('rolljmp',14),('fall',20))

def test_phase_mapping_retains_source_motion_across_pause_and_recovery():
    assert PHASE_CLIPS=={'Ascent':'rolljmp','EntryPause':'rolljmp','Descent':'fall','Recovery':'fall'}

def test_emitted_config_contract_requires_both_headers_before_matrices():
    matrices=[f'happa {name} {index} '+ ' '.join(['0']*12) for name,count in CLIPS for index in range(count)]
    valid='\n'.join(['P2_PURPLE_MOTION_1','rolljmp 14 0.466667','fall 20 0.666667']+matrices)+'\n'
    assert validate_profile(valid)==valid
    interleaved='\n'.join(['P2_PURPLE_MOTION_1','rolljmp 14 0.466667',matrices[0],'fall 20 0.666667']+matrices[1:])+'\n'
    with pytest.raises(ValueError,match='headers must precede'):validate_profile(interleaved)

def motion_bank(root):
    matrices=[f'happa {name} {index} '+ ' '.join(['0']*12) for name,count in CLIPS for index in range(count)]
    profile='\n'.join(['P2_PURPLE_MOTION_1','rolljmp 14 0.466667','fall 20 0.666667']+matrices)+'\n'
    (root/'p2-purple-motion.txt').write_text(profile)
    for name,count in CLIPS:
        for index in range(count):(root/f'purple_{name}_{index:02}.mod').write_bytes(f'{name}:{index}'.encode())
    return profile

def test_preview_stages_exact_motion_bank(tmp_path):
    expected=motion_bank(tmp_path);profile,files=_purple_motion_files(tmp_path)
    assert profile==expected and len(files)==34
    (tmp_path/'purple_fall_20.mod').write_bytes(b'extra')
    with pytest.raises(ValueError,match='exactly 34'):_purple_motion_files(tmp_path)

def test_preview_motion_requires_purple_and_pod(tmp_path):
    with pytest.raises(ValueError,match='requires Purple bank and Research Pod'):
        prepare(tmp_path,tmp_path,tmp_path/'treasure.mod',tmp_path/'runs',purple_motion=tmp_path)
