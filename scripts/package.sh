#!/usr/bin/env bash
# Package script for SIH26262 AICTE Prototype
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Executing pre-packaging clean check..."
python3 "$SCRIPT_DIR/check_clean_repo.py" || true

echo "Packaging clean repository zip..."
python3 "$SCRIPT_DIR/package.py"
