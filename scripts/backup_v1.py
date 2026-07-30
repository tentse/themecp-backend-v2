#!/usr/bin/env python3
"""
On-demand pg_dump backup of the legacy (v1) PostgreSQL database.

Writes a gzipped SQL dump to scripts/backups/ named with a UTC timestamp down to
the second, matching the existing v1-source-*.sql.gz backups, e.g.:

    scripts/backups/v1-source-20260604T130501Z.sql.gz

Connection string comes from .env (or the process environment):
    LEGACY_PG_DATABASE_URL  - the old Railway v1 DB (required)

Usage:
    poetry run python scripts/backup_v1.py
    ./scripts/backup_v1.py          # if marked executable
"""

from __future__ import annotations

import gzip
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

BACKUPS_DIR = Path(__file__).resolve().parent / "backups"
PG_DUMP_TIMEOUT_SECONDS = 900


def utc_stamp() -> str:
    """UTC timestamp to the second, e.g. 20260604T130501Z (matches existing backups)."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def unique_backup_path(ts: str) -> Path:
    """v1-source-<ts>.sql.gz, with a numeric suffix if that name already exists,
    so two runs in the same second never clobber an existing dump."""
    path = BACKUPS_DIR / f"v1-source-{ts}.sql.gz"
    counter = 2
    while path.exists():
        path = BACKUPS_DIR / f"v1-source-{ts}-{counter}.sql.gz"
        counter += 1
    return path


def run_pg_dump(url: str, out_path: Path) -> None:
    """Run pg_dump and gzip-compress its stdout into out_path.

    pg_dump's stdout is streamed through Python into the GzipFile so the bytes are
    actually compressed. NOTE: passing a GzipFile directly as subprocess stdout
    does NOT compress — subprocess writes to the file's raw fd (gz.fileno()),
    bypassing the gzip layer and leaving plain SQL behind a .gz name.
    Deletes the partial file and raises on any non-zero exit.
    """
    print(f"pg_dump v1 source -> {out_path}")
    with gzip.open(out_path, "wb") as gz:
        proc = subprocess.Popen(
            ["pg_dump", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            shutil.copyfileobj(proc.stdout, gz)  # compresses as it streams
        finally:
            proc.stdout.close()
        stderr = proc.stderr.read()
        proc.stderr.close()
        returncode = proc.wait(timeout=PG_DUMP_TIMEOUT_SECONDS)
    if returncode != 0:
        out_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"pg_dump failed (exit {returncode}):\n"
            f"{stderr.decode('utf-8', errors='replace')}"
        )


def main() -> int:
    load_dotenv()

    source_url = os.environ.get("LEGACY_PG_DATABASE_URL")
    if not source_url:
        print(
            "ERROR: LEGACY_PG_DATABASE_URL is not set.\n"
            "Set it in .env (or the environment) to the old (v1) Railway DB "
            "connection string.",
            file=sys.stderr,
        )
        return 1

    if shutil.which("pg_dump") is None:
        print(
            "ERROR: pg_dump not found on PATH. Install the postgres client tools "
            "(e.g. `brew install libpq`, then add it to PATH).",
            file=sys.stderr,
        )
        return 1

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = unique_backup_path(utc_stamp())

    try:
        run_pg_dump(source_url, out_path)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    size = out_path.stat().st_size
    print(f"Backup written: {out_path}  ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
