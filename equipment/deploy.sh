#!/usr/bin/env bash
# Deploys the site to Vercel production. No inputs beyond an authenticated
# `vercel` CLI session. Prints the production deployment URL.
set -euo pipefail
cd "$(dirname "$0")/.."
exec vercel --prod
