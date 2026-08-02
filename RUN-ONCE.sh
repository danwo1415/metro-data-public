#!/usr/bin/env bash
set -euo pipefail

if ! python -c 'import requests, bs4' >/dev/null 2>&1; then
  python -m pip install -q requests beautifulsoup4
fi

python -u update_hk_service_hours.py 2>&1 | tee service-hours-run.log
python -m json.tool hong-kong-data.json >/dev/null
python -m json.tool version.json >/dev/null

git add hong-kong-data.json version.json service-hours-report.json update_hk_service_hours.py RUN-ONCE.sh
git commit -m "Update Hong Kong official first and last train data" || true
git pull --rebase origin main
git push origin main

echo "DONE: official Hong Kong service-hours data validated and pushed."
