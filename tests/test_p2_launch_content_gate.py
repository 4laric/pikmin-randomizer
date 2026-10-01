"""Reject native P2 launch before session creation if no checked content is supplied."""
from unittest.mock import patch
import pytest
from randomizer.runner import _launch


@pytest.mark.parametrize('family', [None, 'dwarf_orange'])
def test_unstaged_p2_launch_never_creates_session(tmp_path, family):
    with patch('randomizer.runner.Session') as session:
        with pytest.raises(ValueError, match='P2 native launch requires'):
            _launch({'mode': 'ap', 'p2_layout': {'bindings': [{'source_id': 44}]}},
                    tmp_path, exe='unused.exe', server='localhost:38281', family_install=family)
        session.assert_not_called()
