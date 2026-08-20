#!/usr/bin/env bash
# Serves the static site on localhost:4173. No inputs. Runs until Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m http.server 4173
