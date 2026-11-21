import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adrobot.config import load_environment


class EnvironmentTests(unittest.TestCase):
    def test_loads_configuration_without_interpolating_values(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            path = Path(folder) / '.env'
            path.write_text("KEITARO_URL=https://example.test\nKEITARO_API_KEY='literal ${TOKEN} # space'\n")
            load_environment(path)
            self.assertEqual(os.environ['KEITARO_URL'], 'https://example.test')
            self.assertEqual(os.environ['KEITARO_API_KEY'], 'literal ${TOKEN} # space')

    def test_process_environment_takes_precedence(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'PORT': '8794'}, clear=True):
            path = Path(folder) / '.env'
            path.write_text('PORT=8000\n')
            load_environment(path)
            self.assertEqual(os.environ['PORT'], '8794')

    def test_missing_file_is_optional(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            load_environment(Path(folder) / '.env')
            self.assertNotIn('KEITARO_API_KEY', os.environ)
