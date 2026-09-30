"""Raging Long Legs (69) native tables generator (#1018): header layout."""
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    'p2_bigfoot_tables', Path(__file__).resolve().parents[1] / 'scripts' / 'p2_bigfoot_tables.py')
tables = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tables)


def test_render_layout():
    ident = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]
    names = ['kosi', 'lfoot1jnt']
    nodes = [dict(id='none', code='____', radius=225.0, offset=[0.0, -100.0, 0.0], joint=0, parent=None),
             dict(id='tama', code='st__', radius=70.0, offset=[0.0, -75.0, 0.0], joint=0, parent=0)]
    clips = [(stem, 10, 'ab' * 32, [[ident, ident]] * tables.SAMPLES) for stem in tables.CLIPS]
    text = tables.render('m' * 64, 'c' * 64, names, [ident, ident], nodes, clips)
    assert 'constexpr int kJointCount = 2;' in text and f'constexpr int kSamples = {tables.SAMPLES};' in text
    assert 'constexpr int kClipCount = 4;' in text and 'constexpr int kCollNodeCount = 2;' in text
    assert '{"tama", "st__", 70.000f, {0.000f, -75.000f, 0.000f}, 0, 0},' in text
    assert '{"none", "____", 225.000f, {0.000f, -100.000f, 0.000f}, 0, -1},' in text
    assert tables.CLIPS == ('dead', 'landing', 'wait', 'flick')  # BIGFOOTANIM order
    assert text.count('{"dead", 10, {') == 1
