#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
read -r -s -p "Paste the Instagram access token: " IG_ACCESS_TOKEN
echo

if [[ -z "$IG_ACCESS_TOKEN" ]]; then
  echo "No token entered."
  exit 1
fi

export IG_ACCESS_TOKEN
PYTHONPATH="$project_dir/services/api" "$project_dir/.venv/bin/python" - <<'PY'
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from reelpilot.database import SessionLocal
from reelpilot.models import InstagramAccount

database = SessionLocal()
try:
    accounts = database.scalars(select(InstagramAccount)).all()
    if len(accounts) == 0:
        raise SystemExit("No Instagram account is connected in the local database.")
    if len(accounts) > 1:
        raise SystemExit("More than one Instagram account exists; update the token through the correct workspace first.")

    account = accounts[0]
    account.access_token = os.environ["IG_ACCESS_TOKEN"]
    account.token_expires_at = datetime.now(UTC) + timedelta(days=60)
    account.updated_at = datetime.now(UTC)
    database.commit()
    print(f"Updated Instagram token for @{account.username}.")
finally:
    database.close()
PY

unset IG_ACCESS_TOKEN
