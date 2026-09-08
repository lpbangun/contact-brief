"""Offline Contact Brief evidence compiler. No research is inferred."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def validate(brief):
    schema = json.loads((ROOT / 'references/contact-brief.schema.json').read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(brief)
    identity, email = brief['identity'], brief['email']
    mailbox = email['mailbox']
    if identity['status'] == 'matched' and (not identity['evidence'] or identity['conflicts']):
        raise ValueError('Matched identity requires evidence and no unresolved conflicts')
    if email['attribution'] != 'unknown' and not email['address']:
        raise ValueError('Email attribution requires an address')
    if email['attribution'] == 'source_supported' and not email['evidence']:
        raise ValueError('Source-supported email requires source evidence')
    if mailbox['status'] == 'not_checked':
        if mailbox['method'] != 'none' or mailbox['checked_at'] is not None:
            raise ValueError('Unchecked mailbox cannot claim a check method or time')
    elif not email['address'] or mailbox['method'] == 'none' or not mailbox['checked_at']:
        raise ValueError('Mailbox result requires address, method and check time')
    if mailbox['status'] in ('smtp_accepted', 'rejected', 'risky') and mailbox['method'] != 'aftership_smtp':
        raise ValueError('SMTP result cannot be inferred from DNS')
    if brief['acceptance'] != acceptance(brief):
        raise ValueError('Recorded-evidence acceptance must match computed gate')



def build(request, now=None):
    now = now or datetime.now(timezone.utc).isoformat()
    result = {
        'schema_version': 'contact-brief.v1', 'generated_at': now,
        'subject': {'name': request['name'], 'company': request['company']},
        'identity': {'status': 'unresolved', 'confidence': 'unknown', 'evidence': [], 'conflicts': []},
        'email': {'address': None, 'attribution': 'unknown', 'evidence': [],
                  'mailbox': {'status': 'not_checked', 'method': 'none', 'checked_at': None,
                              'detail': 'No mailbox check performed; identity and deliverability are separate.'}},
        'coverage': {p: {'status': 'not_attempted', 'reason': 'No native evidence supplied',
                         'actions': [], 'profile_url': None, 'identity_matched': False}
                     for p in ('linkedin', 'x')},
        'signals': [], 'candidate_facts': [], 'draft': None,
        'acceptance': {'passed': False, 'blockers': ['Native search/profile/activity evidence missing on both platforms']},
    }
    for key in ('identity', 'email', 'candidate_facts'):
        if key in request:
            result[key] = deepcopy(request[key])
    for platform in result['coverage']:
        if platform in request.get('coverage', {}):
            result['coverage'][platform] = deepcopy(request['coverage'][platform])
    seen = set()
    for signal in request.get('signals', []):
        if signal['url'] not in seen and len(result['signals']) < 3:
            result['signals'].append(deepcopy(signal))
            seen.add(signal['url'])
    if result['candidate_facts'] and result['signals'] and result['identity']['status'] == 'matched':
        fact, signal = result['candidate_facts'][0], result['signals'][0]
        result['draft'] = {
            'body': f"Hi {result['subject']['name']}, I read your post: {signal['summary']} "
                    f"({signal['url']}). {fact['text']} Would you be open to a short conversation about your work?",
            'candidate_fact_ids': [fact['id']], 'signal_urls': [signal['url']], 'status': 'draft_only'}
    result['acceptance'] = acceptance(result)
    validate(result)
    return result


def acceptance(brief):
    # This checks recorded evidence, not the truth of human/agent observations.
    from urllib.parse import urlparse
    blockers = []
    identity = brief['identity']
    if identity['status'] != 'matched' or not identity['evidence'] or identity['conflicts']:
        blockers.append('Identity unresolved, conflicting, ambiguous, or stale employer')
    for platform, coverage in brief['coverage'].items():
        hosts = {'www.linkedin.com', 'linkedin.com'} if platform == 'linkedin' else {'x.com', 'www.x.com', 'twitter.com'}
        required = {'person_search', 'profile_open', 'activity_search', 'activity_inspect'}
        observed = {a['kind'] for a in coverage['actions'] if a['outcome'] == 'ok'
                    and urlparse(a['url']).hostname in hosts}
        if (coverage['status'] != 'complete' or not coverage['identity_matched']
                or urlparse(coverage['profile_url'] or '').hostname not in hosts or required - observed):
            blockers.append(f'{platform}: native person search, matched profile and authored activity not complete')
    return {'passed': not blockers, 'blockers': blockers}


def render(brief):
    lines = [f"# Contact Brief: {brief['subject']['name']}",
             f"Company: {brief['subject']['company']}",
             f"Fetched/compiled: {brief['generated_at']}",
             f"Identity: {brief['identity']['status']} ({brief['identity']['confidence']})",
             f"Email: {brief['email']['address'] or 'Unknown'} — {brief['email']['mailbox']['status']}",
             '\n## Platform coverage']
    lines += [f"- {p}: {v['status']} — {v['reason']}" for p, v in brief['coverage'].items()]
    lines += ['\n## Identity evidence']
    lines += [f"- {s['quote']} — {s['url']} (fetched {s['fetched_at']})" for s in brief['identity']['evidence']]
    lines += ['\n## Email attribution', f"{brief['email']['attribution']}; mailbox method: {brief['email']['mailbox']['method']}; checked: {brief['email']['mailbox']['checked_at'] or 'never'}", brief['email']['mailbox']['detail']]
    lines += [f"- {s['quote']} — {s['url']}" for s in brief['email']['evidence']]
    lines += ['\n## Relevant activity']
    lines += [f"- {s['summary']} — {s['url']} ({s['published_at'] or 'publication unknown'}; fetched {s['fetched_at']}). Why relevant: {s['relevance']}" for s in brief['signals']]
    if brief['draft']:
        lines += ['\n## Draft — not sent', brief['draft']['body']]
    lines += ['\n## Recorded-evidence gate — not live execution', 'Complete (supplied evidence only)' if brief['acceptance']['passed'] else 'UNPASSED']
    lines += [f'- {b}' for b in brief['acceptance']['blockers']]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'validate', 'verify-email'])
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--now', help='Explicit compilation timestamp for reproducible offline fixtures')
    parser.add_argument('--execute', action='store_true', help='Explicitly dispatch the approved email check')
    parser.add_argument('--smtp', action='store_true', help='Enable separately approved SMTP and catch-all checks')
    parser.add_argument('--adapter', type=Path, default=ROOT / 'bin/contact-brief-aftership')
    parser.add_argument('--timeout', type=float, default=20)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text())
        if args.command == 'verify-email':
            if not args.execute:
                parser.error('verify-email requires --execute and address-scoped authorization JSON')
            from cb_providers import aftership_run
            report = aftership_run(data['address'], data, adapter=args.adapter, smtp=args.smtp, timeout=args.timeout)
            encoded = json.dumps(report, indent=2) + '\n'
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(encoded)
            else:
                print(encoded, end='')
            return 2 if report['error'] else 0
        if args.command == 'validate':
            validate(data)
            print('Valid contact-brief.v1')
        else:
            if not args.out:
                parser.error('build requires --out PREFIX')
            result = build(data, now=args.now)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
            args.out.with_suffix('.md').write_text(render(result))
            print(f'Wrote {args.out.with_suffix(".json")} and {args.out.with_suffix(".md")}')
    except (ValueError, KeyError, OSError, jsonschema.ValidationError) as exc:
        print(f'Invalid evidence ({type(exc).__name__}); check schema and input.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
