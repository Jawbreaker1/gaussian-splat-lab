#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "repo_root=${repo_root}"
echo "machine=$(uname -a)"

if command -v git >/dev/null 2>&1; then
  echo "git=$(git --version)"
else
  echo "missing git"
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  echo "python3=$(python3 --version)"
else
  echo "missing python3"
  exit 1
fi

if command -v node >/dev/null 2>&1; then
  echo "node=$(node --version)"
else
  echo "node=not installed; ok for Stage 0 unless viewer work starts"
fi

test -d "${repo_root}/data/manifests"
echo "stage0_mac_smoke=ok"
