#!/usr/bin/env bash
# Regenerate the hub page and push it, so GitHub Actions redeploys Pages.
# For a full graph rebuild (new data or GEXF/Java changes), run the relevant
# build_*.py / Java steps from README.md first, then this script.
set -euo pipefail
cd "$(dirname "$0")"

python build_index.py

cd ..
git add prtr-grafos
if git diff --cached --quiet; then
    echo "Nothing to commit."
    exit 0
fi
git commit -m "${1:-Update prtr-grafos site}"
git push origin jc_local
