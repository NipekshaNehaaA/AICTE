#!/usr/bin/env python3
"""
Packaging Script for SIH26262 AICTE Prototype.
Builds the delivery archive (Ai.zip) while strictly excluding:
- .env files (except .env.example)
- Database files (*.db, *.db-shm, *.db-wal, *.sqlite*)
- storage_data contents
- node_modules
- .next build artifacts
- __pycache__ and .pytest_cache
- .git
"""

import os
import sys
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = ROOT_DIR / "Ai.zip"

EXCLUDE_DIRS = {
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".git",
    "storage_data",
    ".tempmediaStorage",
    ".system_generated",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".db-shm",
    ".db-wal",
    ".sqlite",
    ".sqlite3",
}

def should_exclude(rel_path: Path) -> bool:
    # Check directory components
    for part in rel_path.parts[:-1]:
        if part in EXCLUDE_DIRS:
            return True

    # Check filename
    name = rel_path.name
    if name in EXCLUDE_DIRS:
        return True

    # Exclude zip itself
    if name == "Ai.zip" or name.endswith(".zip"):
        return True

    # Exclude .env files except .env.example
    if name.startswith(".env") and not name.endswith(".env.example"):
        return True

    # Exclude database files by extension or pattern
    if rel_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return True
    if ".db" in name:
        return True

    return False

def package_project():
    print(f"Building clean distribution archive: {OUTPUT_ZIP.name}")
    print(f"Source Directory: {ROOT_DIR}")

    file_count = 0
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(ROOT_DIR):
            rel_dir = Path(root).relative_to(ROOT_DIR)

            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                rel_file = rel_dir / file
                if not should_exclude(rel_file):
                    abs_file = Path(root) / file
                    zipf.write(abs_file, arcname=str(rel_file))
                    file_count += 1

    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print(f"[SUCCESS] Packaged {file_count} files into {OUTPUT_ZIP.name} ({zip_size_mb:.2f} MB)")
    print("Clean build verified: .env, *.db*, storage_data, node_modules, .next, and __pycache__ excluded.")

if __name__ == "__main__":
    package_project()
