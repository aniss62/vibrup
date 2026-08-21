#!/usr/bin/env bash
# Rebuilds the site from templates/+i18n/, then serves it on localhost:4173.
# No inputs. Runs until Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 equipment/build.py
exec python3 -m http.server 4173
