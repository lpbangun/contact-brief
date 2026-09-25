"""Offline evidence gate for a host supplied contact brief."""
import argparse
import json
from pathlib import Path
import sys

from contact_brief import acceptance, validate


def preflight(auth):
    blockers = []
    if not auth or auth.get('approved') is not True or not auth.get('name') or not auth.get('company'):
        blockers.append('named contact and explicit approval')
    return {'passed': not blockers, 'blockers': blockers, 'network_calls': 0}


def verify_evidence(brief, evidence_root, provider_record):
    validate(brief)
    blockers = list(acceptance(brief)['blockers'])
    root = Path(evidence_root).resolve()
    for platform, coverage in brief['coverage'].items():
        for action in coverage['actions']:
            file = (root / action['evidence_file']).resolve()
            if root not in file.parents or not file.is_file() or not file.stat().st_size:
                blockers.append(f'{platform}: missing or unsafe evidence file')
    if not provider_record or not provider_record.get('call_id'):
        blockers.append('Provider lookup record missing')
    elif provider_record.get('request', {}).get('full_name') != brief['subject']['name']:
        blockers.append('Provider identity input does not match brief subject')
    if brief['email']['address'] and brief['email']['mailbox']['method'] != 'aftership_smtp':
        blockers.append('Enabled real SMTP check evidence missing for found address')
    if not brief['draft']:
        blockers.append('Evidence-backed draft with supplied candidate facts missing')
    return {'passed': False, 'evidence_complete': not blockers,
            'blockers': blockers + ['Live execution cannot be attested from supplied files'],
            'live_execution': 'not_verified', 'network_calls': 0,
            'scope': 'Recorded evidence completeness only; this command performs no browser or mailbox execution'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['preflight', 'verify'])
    parser.add_argument('--authorization', type=Path)
    parser.add_argument('--journal', type=Path)
    parser.add_argument('--brief', type=Path)
    parser.add_argument('--evidence-root', type=Path, default=Path('.'))
    args = parser.parse_args()
    try:
        auth = json.loads(args.authorization.read_text()) if args.authorization else None
        if args.command == 'verify':
            if not args.brief:
                parser.error('verify requires --brief')
            report = verify_evidence(json.loads(args.brief.read_text()), args.evidence_root,
                                     json.loads(args.journal.read_text()) if args.journal else None)
        else:
            report = preflight(auth)
        print(json.dumps(report, indent=2))
        return 0 if report['passed'] else 2
    except (ValueError, OSError, RuntimeError) as exc:
        print(json.dumps({'passed': False, 'blockers': [f'{type(exc).__name__}: operation failed; inspect journal, do not blindly redispatch']}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
