import pytest
from scripts.test_pikmin2_breadbug_cargo_animation_native import animation_evidence

def test_optional_bank_and_actual_native_render_gates():
    rows='P2_BREADBUG_ANIMATION_PAUSE_PASS\n'
    assert animation_evidence(rows,False)['render_states']==[]
    for state in (5,6,8):
        rows+=f'P2_BREADBUG_CARGO_VISUAL generator=186081 state={state}\n'
        for frame in (1,2):rows+=f'P2_BREADBUG_ANIMATION_FRAME state={state} counter={frame} kind={1 if state==8 else 0} source={frame}\n'
    assert animation_evidence(rows,True)['render_states']==[5,6,8]
    with pytest.raises(ValueError):animation_evidence(rows,False)
    with pytest.raises(ValueError):animation_evidence(rows.replace('P2_BREADBUG_ANIMATION_PAUSE_PASS',''),True)
    with pytest.raises(ValueError):animation_evidence(rows.replace('state=8','state=7'),True)
    with pytest.raises(ValueError):animation_evidence(rows.replace('kind=1','kind=0'),True)
    with pytest.raises(ValueError):animation_evidence(rows.replace('source=2','source=1'),True)
