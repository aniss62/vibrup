#!/usr/bin/env bash
# Rebuilds the site from templates/+i18n/, then deploys to Vercel production.
# No inputs beyond an authenticated `vercel` CLI session. Prints the
# production deployment URL.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 equipment/build.py
exec vercel --prod
