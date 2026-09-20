"""Host-level install smoke check for the Agent Plugin package.

Runs the real `hermes plugins validate` and `hermes plugins doctor` against this
package inside a throwaway HOME plus HERMES_HOME, so nothing in the operator's
profile is read or written. Every command here is local: no network call, no
provider credential and no live contact action is performed. When the hermes CLI
is not installed the module skips with that reason instead of pretending to pass.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERMES_CLI = shutil.which('hermes') or ''
COMMAND_TIMEOUT = 180
COPY_SKIP = {'.git', '.venv', 'out', 'private', 'evidence', 'bin', '__pycache__', '.cache'}
DOCTOR_OK = 'OK: runtime discovery, manifest parsing, import, and registration passed'


def copy_package(destination):
    """Copy the plugin tree exactly as a host would install it."""
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if any(part in COPY_SKIP for part in relative.parts):
            continue
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    return destination


@unittest.skipUnless(HERMES_CLI, 'hermes CLI not installed: the host install smoke check needs it')
class HermesPluginInstallSmokeTests(unittest.TestCase):
    def install_isolated_package(self, tmp):
        """Return (home, hermes_home, installed plugin path) for a throwaway host."""
        home = tmp / 'home'
        hermes_home = tmp / 'hermes'
        home.mkdir(parents=True, exist_ok=True)
        hermes_home.mkdir(parents=True, exist_ok=True)
        return home, hermes_home, copy_package(hermes_home / 'plugins' / 'contact-brief')

    def run_hermes(self, home, hermes_home, *args):
        environment = {**os.environ, 'HOME': str(home), 'HERMES_HOME': str(hermes_home)}
        return subprocess.run([HERMES_CLI, *args], capture_output=True, text=True,
                              env=environment, timeout=COMMAND_TIMEOUT)

    @staticmethod
    def json_report(output):
        start = output.index('{')
        return json.loads(output[start:])

    def test_package_is_admissible_and_registers_in_an_isolated_host(self):
        with tempfile.TemporaryDirectory() as raw:
            home, hermes_home, plugin = self.install_isolated_package(Path(raw))

            validate = self.run_hermes(home, hermes_home, 'plugins', 'validate', str(plugin), '--json')
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
            report = self.json_report(validate.stdout)
            self.assertTrue(report['ok'], report)
            self.assertEqual(report['warnings'], [], 'the package must not trip portable-manifest diagnostics')
            self.assertTrue(all(check['ok'] for check in report['checks']), report['checks'])

            doctor = self.run_hermes(home, hermes_home, 'plugins', 'doctor', 'contact-brief', '--ci')
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            self.assertIn(DOCTOR_OK, doctor.stdout)
            self.assertIn('manifest: contact-brief', doctor.stdout)

    def test_isolated_run_does_not_write_the_operators_profile(self):
        real_home = Path(os.environ.get('HERMES_HOME') or Path.home() / '.hermes')
        config = real_home / 'config.yaml'
        before = config.read_bytes() if config.is_file() else None
        with tempfile.TemporaryDirectory() as raw:
            home, hermes_home, plugin = self.install_isolated_package(Path(raw))
            self.run_hermes(home, hermes_home, 'plugins', 'doctor', 'contact-brief', '--ci')
            self.assertTrue((hermes_home / 'plugins' / 'contact-brief' / 'plugin.json').is_file())
            self.assertFalse(home.joinpath('.hermes', 'plugins', 'contact-brief').exists(),
                             'the temporary HOME must not receive a second copy')
        after = config.read_bytes() if config.is_file() else None
        self.assertEqual(before, after, 'the isolated smoke run must not modify the real Hermes config')

    def test_smoke_check_rejects_a_corrupted_package(self):
        with tempfile.TemporaryDirectory() as raw:
            home, hermes_home, plugin = self.install_isolated_package(Path(raw))
            (plugin / 'plugin.json').write_text(json.dumps({
                '$schema': 'https://example.org/not-agent-plugins.json', 'name': 'contact-brief'}))
            validate = self.run_hermes(home, hermes_home, 'plugins', 'validate', str(plugin), '--json')
            self.assertNotEqual(validate.returncode, 0, validate.stdout + validate.stderr)
            doctor = self.run_hermes(home, hermes_home, 'plugins', 'doctor', 'contact-brief', '--ci')
            self.assertNotEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)


if __name__ == '__main__':
    unittest.main()
