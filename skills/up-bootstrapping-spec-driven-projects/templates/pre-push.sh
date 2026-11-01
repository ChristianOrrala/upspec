#!/bin/sh
# Reports the Status claims of the pushed commits and lets the push go ahead.
# Unavailable local checks never stop a push. To stop a push on problems, add
# --strict to the status_claims.py line below: the check then exits 1.
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
