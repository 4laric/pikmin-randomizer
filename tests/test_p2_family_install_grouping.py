"""install_layout installs each family once with every actor bound to it (seeds repeat families)."""
import experimental.pikmin2_family_install as fi


def test_repeated_family_installs_once_with_all_actors(tmp_path, monkeypatch):
    calls = []

    def fake(source, run, actors):
        assert not (run / 'fake-installed').exists(), 'family installed twice'
        (run / 'fake-installed').write_text('x')
        calls.append(list(actors))
        return {'actors': list(actors)}

    monkeypatch.setitem(fi._OVERRIDES, 'dweevil', fake)
    for enum in ('FireOtakara', 'WaterOtakara'):
        (tmp_path / 'content' / enum).mkdir(parents=True)
    layout = {'bindings': [
        {'target': '11', 'source_id': 59, 'enum_name': 'FireOtakara'},
        {'target': '12', 'source_id': 60, 'enum_name': 'WaterOtakara'},
        {'target': '13', 'source_id': 59, 'enum_name': 'FireOtakara'},
    ]}
    result = fi.install_layout(tmp_path / 'run', layout, tmp_path / 'content', {'11': 1, '12': 2, '13': 3})
    assert calls == [[(1, 'FireOtakara'), (2, 'WaterOtakara'), (3, 'FireOtakara')]]
    assert set(result['receipts']) == {'11', '12', '13'}
    assert (tmp_path / 'run' / fi.BINDING_RECEIPT).is_file()
