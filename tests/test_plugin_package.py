"""Agent Plugin packaging is validated offline: manifest, installable skill surface,
route metadata and boundary declarations. No network, no provider key, no Hermes
profile and no live provider call are touched by this module.

Everything asserted here is reproduced from the repository itself. The host-level
smoke check (real `hermes plugins validate`/`doctor` in an isolated HERMES_HOME)
lives in tests/test_plugin_smoke.py.
"""
import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SCHEMA_V1 = 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'

# Agent Plugins v1 plugin.json constraints (subset enforced by the Hermes portable reader).
PLUGIN_FIELDS = {
    '$schema', 'name', 'version', 'description', 'author', 'homepage',
    'repository', 'license', 'keywords', 'extensions',
}
PLUGIN_NAME_RE = re.compile(r'^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$')
SKILL_NAME_RE = re.compile(r'^(?!.*--)[a-z0-9]+(?:-[a-z0-9]+)*$')

ROUTE_REQUIRED = (
    'id', 'label', 'kind', 'owner', 'briefLookupProvider', 'purpose', 'inputs',
    'limits', 'approval', 'spend', 'resultSchema', 'importer', 'statuses',
    'capabilities', 'evidence',
)
CAPABILITY_KEYS = (
    'browser', 'social', 'messaging', 'sending', 'mailboxCheck',
    'genericSearch', 'peopleDiscovery',
)
REQUIRED_NEVER = (
    'browser_automation', 'social_research', 'message_sending',
    'application_submission', 'exa_job_or_people_discovery', 'address_guessing',
    'smtp_or_mailbox_check_via_exa', 'credential_management',
)
REQUIRED_VISIBILITY = (
    'sourceUrl', 'mailbox', 'channel', 'confidence', 'provenance', 'freshness',
    'missReason', 'spendUsd',
)
IGNORED_DIRS = {'.git', '.venv', 'out', 'private', 'evidence', 'bin', '__pycache__', '.cache'}
SECRET_ASSIGNMENT = re.compile(
    r'(?:^|\n)\s*[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z0-9_]*\s*[=:]\s*\S+')
ABSOLUTE_USER_PATH = re.compile(r'(/home/[a-z0-9_-]+/|/Users/[A-Za-z0-9_-]+/|[A-Z]:\\\\Users\\\\)')


def package_files():
    out = []
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        out.append(rel)
    return out


def split_frontmatter(text):
    """Return (block, body) for a SKILL.md, requiring a fenced YAML frontmatter block."""
    text = text.lstrip('\ufeff')
    if not text.startswith('---'):
        raise ValueError('missing YAML frontmatter')
    match = re.search(r'\n---\s*\n', text[3:])
    if match is None:
        raise ValueError('unterminated YAML frontmatter')
    return text[3:match.start() + 3], text[3 + match.end():]


def unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def parse_frontmatter(block):
    """Parse the flat string-only frontmatter this package uses (no YAML dependency)."""
    data, nested = {}, None
    for line in block.splitlines():
        if not line.strip():
            continue
        indented = re.match(r'^ {2}(\S+):\s*(.*)$', line)
        if indented and nested:
            data[nested][indented.group(1)] = unquote(indented.group(2).strip())
            continue
        top = re.match(r'^(\S+):\s*(.*)$', line)
        if top is None:
            raise ValueError(f'unparseable frontmatter line: {line!r}')
        nested = top.group(1)
        if top.group(2).strip():
            data[nested] = unquote(top.group(2).strip())
            nested = None
        else:
            data[nested] = {}
    return data


def resolve_pointer(document, pointer):
    node = document
    for raw in pointer.split('/'):
        if not raw:
            continue
        segment = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(node, list):
            node = node[int(segment)]
        else:
            if segment not in node:
                raise KeyError(segment)
            node = node[segment]
    return node


def dotted_schema_path(schema, path):
    """Resolve 'email.lookup.provider' or 'email.evidence[].url' inside a JSON schema."""
    node = schema
    for raw in path.split('.'):
        name = raw.split('[')[0]
        node = node['properties'][name]
        if raw != name:
            node = node['items'] if 'items' in node else node
    return node

class PluginManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / 'plugin.json').read_text())

    def test_manifest_is_agent_plugins_v1(self):
        manifest = self.manifest
        self.assertEqual(manifest['$schema'], PLUGIN_SCHEMA_V1)
        self.assertEqual(sorted(set(manifest) - PLUGIN_FIELDS), [], 'unknown plugin.json fields are ignored by the loader')
        name = manifest['name']
        self.assertTrue(PLUGIN_NAME_RE.fullmatch(name), name)
        self.assertLessEqual(len(name), 64)
        self.assertEqual(name, 'contact-brief')
        for field in ('version', 'description', 'license'):
            self.assertIsInstance(manifest[field], str)
            self.assertTrue(manifest[field].strip(), field)
        self.assertIsInstance(manifest['keywords'], list)
        self.assertTrue(all(isinstance(keyword, str) for keyword in manifest['keywords']))

    def test_manifest_declares_no_network_or_send_surface(self):
        description = self.manifest['description']
        self.assertIn('Agent Plugin', description)
        for forbidden in ('browser', 'sending'):
            self.assertIn(forbidden, description)

class InstallableSkillSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.skill_path = ROOT / 'skills' / 'contact-brief' / 'SKILL.md'
        self.assertTrue(self.skill_path.is_file(), 'the Agent Plugin skill surface is missing')
        self.block, self.body = split_frontmatter(self.skill_path.read_text())
        self.meta = parse_frontmatter(self.block)
        self.canonical_block, self.canonical_body = split_frontmatter((ROOT / 'SKILL.md').read_text())

    def test_skill_name_matches_its_directory_and_v1_constraints(self):
        self.assertEqual(self.meta['name'], self.skill_path.parent.name)
        self.assertTrue(SKILL_NAME_RE.fullmatch(self.meta['name']), self.meta['name'])
        description = self.meta['description']
        self.assertIsInstance(description, str)
        self.assertTrue(1 <= len(description) <= 1024)
        self.assertEqual(self.meta['license'], 'MIT')

    def test_frontmatter_metadata_is_a_flat_string_map(self):
        metadata = self.meta['metadata']
        self.assertIsInstance(metadata, dict)
        self.assertTrue(metadata, 'metadata must not be empty')
        for key, value in metadata.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, str, f'metadata.{key} must be a string for Agent Plugins v1')
            self.assertNotIn(value.strip()[:1], ('[', '{'), f'metadata.{key} must be a scalar string')

    def test_skill_body_is_the_canonical_skill_body(self):
        self.assertEqual(self.body, self.canonical_body,
                         'skills/contact-brief/SKILL.md must mirror SKILL.md verbatim '
                         '(only the frontmatter differs, flattened for Agent Plugins v1)')
        self.assertEqual(self.meta['description'], self.canonical_block
                         .split('description:', 1)[1].splitlines()[0].strip(),
                         'the installable skill must keep the canonical trigger description')

    def test_declared_version_matches_the_package_version(self):
        self.assertEqual(self.meta['metadata']['version'], self.manifest_version())

    def manifest_version(self):
        return json.loads((ROOT / 'plugin.json').read_text())['version']

class RouteMetadataTests(unittest.TestCase):
    def setUp(self):
        self.routes = json.loads((ROOT / 'routes.json').read_text())
        self.brief_schema = json.loads((ROOT / 'references' / 'contact-brief.schema.json').read_text())

    def test_route_metadata_shape_and_plugin_join(self):
        self.assertEqual(self.routes['$schema'], 'contact-brief-routes/v1')
        self.assertEqual(self.routes['plugin'], json.loads((ROOT / 'plugin.json').read_text())['name'])
        self.assertEqual(set(self.routes['routes']), {
            'codex_exa_plugin', 'exa_agent_fiber', 'aftership_mailbox_check'})
        for key, route in self.routes['routes'].items():
            self.assertEqual(route['id'], key)
            missing = [field for field in ROUTE_REQUIRED if field not in route]
            self.assertEqual(missing, [], f'{key} is missing {missing}')
            self.assertTrue(route['purpose'].strip(), key)
            self.assertIsInstance(route['inputs'], list)
            self.assertTrue(route['inputs'], key)

    def test_every_route_command_and_schema_is_real(self):
        for key, route in self.routes['routes'].items():
            for field in ('importer', 'runner'):
                if field not in route:
                    continue
                argv = route[field].split()
                self.assertEqual(argv[0], 'python3', key)
                script = ROOT / argv[1]
                self.assertTrue(script.is_file(), f'{key}.{field} names a missing script: {argv[1]}')
                match = re.search(r'choices=\[([^\]]*)\]', script.read_text())
                if match is None:
                    self.fail(f'{key}.{field}: {argv[1]} declares no subcommand choices')
                declared = {token.strip().strip("'\"") for token in match.group(1).split(',')}
                self.assertIn(argv[2], declared, f'{key}.{field}: unknown subcommand {argv[2]}')
            schema_ref, _, pointer = route['resultSchema'].partition('#')
            schema_path = ROOT / schema_ref
            self.assertTrue(schema_path.is_file(), f'{key}.resultSchema missing: {schema_ref}')
            json.loads(schema_path.read_text())
            if pointer:
                resolve_pointer(json.loads(schema_path.read_text()), pointer)

    def test_route_miss_and_success_statuses_match_the_result_envelope(self):
        brief_statuses = set(self.brief_schema['properties']['email']['properties']['lookup']
                             ['properties']['status']['enum'])
        for key, route in self.routes['routes'].items():
            if route['kind'] == 'mailbox_check':
                continue
            schema = json.loads((ROOT / route['resultSchema']).read_text())
            envelope = set(schema['properties']['status']['enum'])
            declared = set(route['statuses']['success']) | set(route['statuses']['miss'])
            self.assertEqual(declared, envelope, f'{key} statuses disagree with {route["resultSchema"]}')
            if route['briefLookupProvider'] == 'exa_agent_fiber':
                self.assertTrue(declared <= brief_statuses,
                                f'{key} declares statuses the brief lookup cannot represent: {declared - brief_statuses}')

    def test_complied_evidence_fields_exist_in_the_brief_schema(self):
        visibility = self.routes['evidenceVisibility']
        for name in REQUIRED_VISIBILITY:
            self.assertIn(name, visibility, f'route metadata must expose {name}')
        for name, path in visibility.items():
            self.assertTrue(path.strip(), name)
            dotted_schema_path(self.brief_schema, path)

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.routes = json.loads((ROOT / 'routes.json').read_text())

    def test_stage_rules_forbid_generic_search_and_person_substitution(self):
        for rule, value in self.routes['stageRules'].items():
            self.assertIs(value, True, f'stageRules.{rule} must stay true')
        self.assertIs(self.routes['stageRules']['researchAndIdentityPrecedeDiscovery'], True)
        order = self.routes['stageOrder']
        self.assertLess(order.index('identity_resolution'), order.index('email_discovery'))
        self.assertLess(order.index('email_discovery'), order.index('mailbox_check'))
        self.assertIs(self.routes['paidDiscoveryRequiresApproval'], True)

    def test_never_list_covers_the_bounded_contact_contract(self):
        declared = set(self.routes['capabilitiesNever'])
        missing = [item for item in REQUIRED_NEVER if item not in declared]
        self.assertEqual(missing, [], f'capabilitiesNever is missing {missing}')

    def test_every_route_is_single_subject_and_capability_bounded(self):
        for key, route in self.routes['routes'].items():
            limits = route['limits']
            self.assertEqual(limits['subjectsPerRun'], 1, key)
            self.assertEqual(limits['addressesPerResult'], 1, key)
            self.assertEqual(limits['automaticRetries'], 0, key)
            self.assertIs(limits['bulk'], False, key)
            capabilities = route['capabilities']
            missing = [name for name in CAPABILITY_KEYS if name not in capabilities]
            self.assertEqual(missing, [], f'{key} does not declare {missing}')
            for name in CAPABILITY_KEYS:
                expected = name == 'mailboxCheck' and route['kind'] == 'mailbox_check'
                self.assertIs(capabilities[name], expected,
                              f'{key}.capabilities.{name} must be {expected}')
            self.assertIs(capabilities['packageNetwork'], route['owner'] == 'package', key)

    def test_paid_routes_require_explicit_approval(self):
        for key in ('exa_agent_fiber', 'aftership_mailbox_check'):
            approval = self.routes['routes'][key]['approval']
            self.assertIs(approval['required'], True, key)
            self.assertTrue(approval['kind'].strip(), key)
        plugin_route = self.routes['routes']['codex_exa_plugin']['approval']
        self.assertIs(plugin_route['required'], False)
        self.assertEqual(plugin_route['kind'], 'host_tool_availability')

    def test_fiber_route_is_email_only_with_provider_reported_spend(self):
        fiber = self.routes['routes']['exa_agent_fiber']
        self.assertEqual(fiber['limits']['effort'], 'low_only')
        self.assertIs(fiber['spend']['providerEnforcedCap'], False)
        self.assertIsNone(fiber['spend']['reservedAllowanceUsd'])
        self.assertIn('provider_reported', fiber['statuses']['success'])
        self.assertIn('uncertain', fiber['statuses']['miss'])

    def test_redaction_keeps_uncertain_candidates_private(self):
        redaction = self.routes['redaction']
        self.assertIs(redaction['rawProviderEnvelopeRetainedPrivately'], True)
        self.assertIs(redaction['uncertainCandidateExposedInPublicBrief'], False)
        self.assertEqual(redaction['publicAddressRequiresStatus'], 'provider_reported')
        self.assertTrue(redaction['neverPrinted'])

class PackageHygieneTests(unittest.TestCase):
    def test_business_logic_is_not_forked_into_the_packaging_layer(self):
        definitions = {}
        for rel in package_files():
            if rel.suffix != '.py' or rel.parts[0] == 'tests':
                continue
            text = (ROOT / rel).read_text()
            for name in ('def import_fiber(', 'def import_exa_plugin(', 'def validate(', 'def build(request'):
                if name in text:
                    definitions.setdefault(name, []).append(str(rel))
        for name, owners in definitions.items():
            self.assertEqual(owners, ['scripts/contact_brief.py'],
                             f'{name} is implemented outside the canonical core: {owners}')
        skills_dir = ROOT / 'skills'
        self.assertEqual([str(p.relative_to(ROOT)) for p in skills_dir.rglob('*.py')], [],
                         'the installable skill surface must not carry executable logic')

    def test_package_carries_no_secret_material_or_absolute_user_path(self):
        offenders = []
        for rel in package_files():
            if rel.suffix not in ('.py', '.json', '.md', '.txt', '.toml', '.yaml', '.yml', '.html', '.go', '.mod', '.sum'):
                continue
            if rel.name == 'AFTERSHIP-LICENSE':
                continue
            text = (ROOT / rel).read_text(errors='ignore')
            # Test modules legitimately spell out credential-shaped detection patterns.
            if rel.parts[0] != 'tests' and SECRET_ASSIGNMENT.search(text):
                offenders.append(f'{rel}: secret-shaped assignment')
            if ABSOLUTE_USER_PATH.search(text):
                offenders.append(f'{rel}: absolute user path')
        self.assertEqual(offenders, [])

    def test_routes_and_plugin_are_documented_surfaces(self):
        readme = (ROOT / 'README.md').read_text()
        for route in json.loads((ROOT / 'routes.json').read_text())['routes']:
            self.assertIn(route, readme, f'README must document the {route} route')
        for token in ('plugin.json', 'routes.json', 'skills/contact-brief/SKILL.md'):
            self.assertIn(token, readme, f'README must document {token}')


if __name__ == '__main__':
    unittest.main()
