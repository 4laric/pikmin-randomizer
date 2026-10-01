import json
from pathlib import Path
import tempfile
import unittest

from workflow.managed_config import output_access


class ManagedConfigTests(unittest.TestCase):
    def test_unattended_default_denies_unknown_paths_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); config = root / 'config.json'
            original = '{"permission":{"task":"deny","question":"deny"}}'
            config.write_text(original)
            result = output_access(config, root / 'output/lane', root)
            self.assertEqual(list(result['permission']['external_directory'].items()),
                             [('*', 'deny'), (root.as_posix() + '/**', 'allow')])
            self.assertEqual(config.read_text(), original)
            self.assertEqual(result['permission']['task'], 'deny')

    def test_explicit_policies_are_never_overridden(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); config = root / 'config.json'
            for permission in [{'external_directory': 'ask'}, {'external_directory': {'*': 'deny'}}, {'*': 'ask'}]:
                config.write_text(json.dumps({'permission': permission}))
                before = config.read_bytes()
                self.assertIsNone(output_access(config, root / 'output/lane', root))
                self.assertEqual(config.read_bytes(), before)
