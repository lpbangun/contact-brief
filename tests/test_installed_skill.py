"""Exercise documented offline commands against clean installed package layouts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUPPORT_DIRS = ('examples', 'references', 'scripts', 'skills')
SUPPORT_FILES = ('README.md', 'plugin.json', 'requirements.txt', 'routes.json')


def copy_support(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name in SUPPORT_DIRS:
        shutil.copytree(source / name, destination / name)
    for name in SUPPORT_FILES:
        shutil.copy2(source / name, destination / name)


def locate_tool_root(skill_file):
    """Apply the two layouts documented in SKILL.md."""
    skill_dir = skill_file.parent
    if (skill_dir / 'scripts' / 'contact_brief.py').is_file():
        return skill_dir
    portable_root = skill_dir.parents[1]
    if (portable_root / 'scripts' / 'contact_brief.py').is_file():
        return portable_root
    raise AssertionError(f'cannot resolve compiler root from {skill_file}')


class InstalledSkillInvocationTests(unittest.TestCase):
    def run_demo(self, layout):
        with tempfile.TemporaryDirectory(prefix=f'contact-brief-{layout}-') as raw:
            base = Path(raw)
            package = base / 'installed package with spaces'
            if layout == 'portable':
                copy_support(ROOT, package)
                skill_file = package / 'skills' / 'contact-brief' / 'SKILL.md'
                tool_root = locate_tool_root(skill_file)
            else:
                skill_dir = package / 'skills' / 'contact-brief'
                skill_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / 'skills' / 'contact-brief' / 'SKILL.md', skill_dir / 'SKILL.md')
                for name in ('examples', 'references', 'scripts'):
                    shutil.copytree(ROOT / name, skill_dir / name)
                for name in ('README.md', 'requirements.txt'):
                    shutil.copy2(ROOT / name, skill_dir / name)
                skill_file = skill_dir / 'SKILL.md'
                tool_root = locate_tool_root(skill_file)

            self.assertEqual(tool_root, package if layout == 'portable' else skill_file.parent)
            original_files = sorted(str(p.relative_to(package)) for p in package.rglob('*') if p.is_file())
            run_dir = base / 'writable run outside plugin'
            run_dir.mkdir()
            work_dir = base / 'unrelated terminal cwd'
            work_dir.mkdir()
            env = dict(os.environ)
            env['PYTHONPATH'] = ''
            script = tool_root / 'scripts' / 'contact_brief.py'
            request = tool_root / 'examples' / 'offline-request.json'
            out_base = run_dir / 'demo'

            build = subprocess.run(
                [sys.executable, str(script), 'build', str(request), '--out', str(out_base),
                 '--now', '2026-09-08T12:00:00Z'],
                cwd=work_dir, env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            validate = subprocess.run(
                [sys.executable, str(script), 'validate', str(run_dir / 'demo.json')],
                cwd=work_dir, env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)

            result = json.loads((run_dir / 'demo.json').read_text())
            self.assertEqual(result['schema_version'], 'contact-brief.v1')
            self.assertFalse(result['acceptance']['passed'])
            self.assertTrue((run_dir / 'demo.md').is_file())
            self.assertEqual(
                original_files,
                sorted(str(p.relative_to(package)) for p in package.rglob('*') if p.is_file()),
                'the installed package must remain untouched')
            self.assertFalse((package / '.venv').exists())
            self.assertFalse((package / 'out').exists())

    def test_portable_agent_plugin_layout_runs_offline_from_unrelated_cwd(self):
        self.run_demo('portable')

    def test_codex_flattened_skill_layout_runs_offline_from_unrelated_cwd(self):
        self.run_demo('flattened')

    def test_both_skill_surfaces_document_root_resolution_and_external_run_dir(self):
        for relative in ('SKILL.md', 'skills/contact-brief/SKILL.md'):
            text = (ROOT / relative).read_text()
            self.assertIn('if scripts/contact_brief.py is beside SKILL.md', text)
            self.assertIn('../../scripts/contact_brief.py', text)
            self.assertIn('RUN_DIR', text)
            self.assertIn('Never write into TOOL_ROOT', text)


class JobsssHandoffDocumentationTests(unittest.TestCase):
    def test_handoff_matches_native_brief_import_and_reconciliation(self):
        text = (ROOT / 'references' / 'jobsss.md').read_text()
        self.assertIn('contact-brief.v1 JSON contract natively', text)
        self.assertIn('A completed Contact Brief with no email is a valid contact import.', text)
        self.assertIn('Repeated imports reconcile onto an existing logical contact', text)
        self.assertNotIn('This API is not a contact-brief.v1 importer.', text)
        self.assertNotIn('omitting email may produce new contacts', text)


if __name__ == '__main__':
    unittest.main()
