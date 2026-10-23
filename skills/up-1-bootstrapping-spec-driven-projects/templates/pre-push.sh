#!/bin/sh
# CI stays authoritative; unavailable local checks must never stop a push.
if ! command -v python3 >/dev/null 2>&1 || [ ! -f tools/specs/status_claims.py ]; then
    echo 'Status claims: push not checked (Python or tools/specs/status_claims.py is missing).'
    exit 0
fi
python3 tools/specs/status_claims.py --pre-push "$@"
result=$?
if [ "$result" -eq 1 ]; then
    exit 1
fi
if [ "$result" -ne 0 ]; then
    echo 'Status claims: push not checked (the check could not run).'
fi
exit 0
