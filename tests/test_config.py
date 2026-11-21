import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adrobot.config import load_environment


class EnvironmentTests(unittest.TestCase):
    def test_loads_credentials_without_interpolating_password(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            path = Path(folder) / '.env'
            path.write_text("KEITARO_URL=https://example.test\nKEITARO_LOGIN=test-user\nKEITARO_PASSWORD='literal ${TOKEN} # space'\nKEITARO_API_KEY=test-key\n")
            load_environment(path)
            self.assertEqual(os.environ['KEITARO_URL'], 'https://example.test')
            self.assertEqual(os.environ['KEITARO_LOGIN'], 'test-user')
            self.assertEqual(os.environ['KEITARO_PASSWORD'], 'literal ${TOKEN} # space')
            self.assertEqual(os.environ['KEITARO_API_KEY'], 'test-key')

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
