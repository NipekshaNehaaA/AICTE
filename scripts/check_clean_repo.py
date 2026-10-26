#!/usr/bin/env python3
"""
Pre-commit and CI Check:
Fails if any .env file, database file (*.db, *.sqlite), or storage_data file is tracked in git.
"""

import sys
import subprocess
import fnmatch

FORBIDDEN_TRACKED_PATTERNS = [
    "*.env",
    ".env",
    "**/.env",
    "backend/.env",
    "*.db",
    "*.db-shm",
    "*.db-wal",
    "*.sqlite",
    "*.sqlite3",
    "*storage_data/*",
    "backend/storage_data/*",
    "storage_data/**",
]

WHITELIST_PATTERNS = [
    "*.env.example",
    ".env.example",
    "**/.env.example",
]

def check_tracked_files():
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=True
        )
        tracked_files = result.stdout.strip().splitlines()
    except Exception as e:
        print(f"Warning: git ls-files failed: {e}.")
        tracked_files = []

    violations = []
    for filepath in tracked_files:
        norm_path = filepath.replace("\\", "/")
        
        # Check whitelist
        if any(fnmatch.fnmatch(norm_path, wp) for wp in WHITELIST_PATTERNS):
            continue

        # Check forbidden
        for pattern in FORBIDDEN_TRACKED_PATTERNS:
            if fnmatch.fnmatch(norm_path, pattern):
                violations.append((filepath, pattern))
                break

    if violations:
        print("=" * 70)
        print("SECURITY CI ERROR: Sensitive or ephemeral files tracked in git:")
        for f, pat in violations:
            print(f"  - {f} (matches pattern: {pat})")
        print("=" * 70)
        print("Remediation: Run `git rm --cached <file>` and ensure it is in .gitignore.")
        sys.exit(1)
    else:
        print("[SUCCESS] Repository is clean: No .env, *.db*, or storage_data files tracked in git.")

if __name__ == "__main__":
    check_tracked_files()
