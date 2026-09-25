"""Address-scoped mailbox verification boundary."""
from datetime import datetime, timezone
import json
from pathlib import Path


def aftership_run(address, authorization, *, adapter, smtp=False, timeout=20):
    """Explicit address-scoped dispatch; adapter path is trusted local code."""
    if (authorization.get('approved') is not True
            or authorization.get('address') != address
            or not address or not isinstance(address, str)
            or (smtp and authorization.get('smtp_approved') is not True)):
        raise ValueError('Exact address approval required; SMTP needs separate approval')
    import subprocess
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
        raise ValueError('Timeout must be in (0, 60] seconds')
    raw, error = {}, None
    try:
        run = subprocess.run([str(Path(adapter).resolve())], input=json.dumps({
            'address': address, 'approved': True, 'smtp': smtp,
            'smtp_approved': authorization.get('smtp_approved') is True,
            'timeout_seconds': timeout}), text=True, capture_output=True, timeout=timeout + 1)
        if run.returncode:
            raise ValueError('Adapter failed')
        response = json.loads(run.stdout)
        if (not isinstance(response, dict) or response.get('smtp_enabled') is not smtp
                or not isinstance(response.get('raw'), dict)
                or response['raw'].get('email') != address):
            raise ValueError('Invalid adapter envelope')
        raw, error = response['raw'], response.get('error')
        if not isinstance(raw.get('syntax'), dict) or not isinstance(raw.get('smtp') or {}, dict):
            raise ValueError('Invalid adapter result')
    except (OSError, subprocess.TimeoutExpired, ValueError):
        raw, error = {}, 'adapter_error_or_timeout'
    checked_at = datetime.now(timezone.utc).isoformat()
    return {'address': address, 'raw': raw, 'error': error,
            'smtp_enabled': smtp, 'mailbox': aftership_result(raw, checked_at, smtp, error=error)}


def aftership_result(raw, checked_at, smtp_enabled=False, *, error=None):
    """Normalize actual AfterShip JSON, never infer identity from a mailbox."""
    status = 'unknown'
    detail = 'No conclusive mailbox result; MX alone does not verify a mailbox.'
    smtp = raw.get('smtp') or {}
    if error:
        detail = 'Verifier timeout/error/blocked; mailbox status remains unknown.'
    elif raw.get('syntax', {}).get('valid') is False:
        status, detail = 'invalid', 'Verifier reported invalid address syntax.'
    elif smtp_enabled and smtp:
        if smtp.get('catch_all') or smtp.get('full_inbox'):
            status, detail = 'risky', 'Catch-all or full inbox; do not treat as verified.'
        elif smtp.get('disabled'):
            status, detail = 'rejected', 'Verifier reported disabled mailbox; not identity evidence.'
        elif (smtp.get('host_exists') is True and smtp.get('deliverable') is True
              and smtp.get('catch_all') is False and smtp.get('full_inbox') is False
              and smtp.get('disabled') is False):
            status, detail = 'smtp_accepted', 'SMTP recipient accepted; not a delivery guarantee or identity proof.'
    return {'status': status, 'method': 'aftership_smtp' if smtp_enabled else 'aftership_dns',
            'checked_at': checked_at, 'detail': detail}
