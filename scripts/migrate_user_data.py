#!/usr/bin/env python3
"""
Migrate legacy user + contest history data from the old Railway-hosted PostgreSQL
(v1) into the new themecp-backend-v2 schema.

Modes
-----
Full mode (default): TRUNCATES users / contest_session / contest_session_result /
contest_session_problems_status / contest_session_seen_problem / contest_theme,
then re-inserts everything from scratch.

Single-user mode (--email <addr>): deletes only that user's rows from v2 then
re-imports just that one user's history. Idempotent.

Safety
------
- pg_dump backups of both v1 and v2 are written to scripts/backups/ before any
  destructive work.
- --confirm-backups-done is required for any non-dry-run.
- --confirm-truncate is required for full-mode non-dry-run.
- The whole import (themes + users + sessions + stats backfill) runs inside a
  single psycopg2 transaction on v2 - any failure rolls back cleanly.

Usage
-----
    # Connection strings come from .env (or the process environment):
    #   LEGACY_PG_DATABASE_URL  - the old Railway v1 DB (required)
    #   PG_DATABASE_URL         - the new v2 target DB (optional; defaults to local docker)

    # dry-run first
    poetry run python scripts/migrate_user_data.py --dry-run

    # smoke-test one user
    poetry run python scripts/migrate_user_data.py --email someone@example.com --confirm-backups-done

    # the real thing
    poetry run python scripts/migrate_user_data.py --confirm-truncate --confirm-backups-done
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any

# Add project root to path so we can import api.utils.Utils
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import execute_values

from api.utils import Utils

# Load .env at module import so env vars are visible to argparse/main.
load_dotenv()

# -----------------------------------------------------------------------------
# Constants - tweak after first dry-run if needed
# -----------------------------------------------------------------------------

USER_BATCH_SIZE = 1000
SESSION_BATCH_SIZE = 500

RATING_MIN = 0
RATING_MAX = 3500
PERF_MIN = -2000
PERF_MAX = 5500
DELTA_ABS_MAX = 1000

DEFAULT_THEME = "mixed"

THEME_ALIASES: dict[str, str] = {
    "bruteforce": "brute force",
    "ds": "data structures",
    "nt": "number theory",
    "combi": "combinatorics",
    "constructives": "constructive algorithms",
    "combine": "mixed",
}

TARGET_TABLES = [
    "users",
    "contest_session",
    "contest_session_seen_problem",
    "contest_session_problems_status",
    "contest_session_result",
    "contest_theme",
    "contest_levels",
]

# Tables wiped in full mode. Note contest_levels is NOT in this list.
TRUNCATE_TABLES = [
    "users",
    "contest_session",
    "contest_session_seen_problem",
    "contest_session_problems_status",
    "contest_session_result",
    "contest_theme",
]

SCRIPTS_DIR = PROJECT_ROOT / "scripts"
BACKUPS_DIR = SCRIPTS_DIR / "backups"
SKIPPED_CSV_PATH = SCRIPTS_DIR / "migration_skipped.csv"
REPORT_TXT_PATH = SCRIPTS_DIR / "migration_report.txt"

CSV_HEADER = ["source_id", "email", "reason", "payload_json"]


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate v1 (Railway) user + contest data into v2.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute everything against v2 then rollback. Skips backups.",
    )
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="Migrate only this user's data (skips TRUNCATE; idempotent).",
    )
    parser.add_argument(
        "--confirm-truncate",
        action="store_true",
        help="Required for full-mode non-dry-run. Confirms you want to TRUNCATE v2.",
    )
    parser.add_argument(
        "--confirm-backups-done",
        action="store_true",
        help="Required for any non-dry-run. Acknowledges backups have been taken.",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip pg_dump backups. Use only when a recent backup already exists.",
    )
    return parser.parse_args()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


class SkipLogger:
    """Append-only CSV writer for skipped rows. Always flushable from finally."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        self._writer.writerow(CSV_HEADER)
        self.counts: Counter[str] = Counter()

    def skip(
        self,
        source_id: Any,
        email: str | None,
        reason: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._writer.writerow(
            [
                "" if source_id is None else str(source_id),
                email or "",
                reason,
                json.dumps(payload or {}, default=str),
            ]
        )
        self.counts[reason] += 1

    def close(self) -> None:
        try:
            self._fh.flush()
            self._fh.close()
        except Exception:
            pass


def normalize_theme(raw: str | None) -> str:
    if raw is None:
        return DEFAULT_THEME
    t = raw.strip().lower()
    if not t:
        return DEFAULT_THEME
    return THEME_ALIASES.get(t, t)


def midnight_utc_unix_seconds(d: Any) -> int:
    """Convert a date (or datetime) to Unix seconds at 00:00 UTC."""
    if isinstance(d, datetime):
        day = d.date()
    else:
        day = d
    dt = datetime.combine(day, time(0, 0), tzinfo=timezone.utc)
    return int(dt.timestamp())


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# -----------------------------------------------------------------------------
# Phase -1 - backups
# -----------------------------------------------------------------------------


def run_pg_dump(url: str, out_path: Path, label: str) -> None:
    """Run pg_dump and gzip-compress its stdout into out_path. Aborts on non-zero exit.

    pg_dump's stdout is streamed through Python into the GzipFile so the bytes are
    actually compressed. NOTE: passing a GzipFile directly as subprocess stdout does
    NOT compress — subprocess writes to the file's raw fd (gz.fileno()), bypassing the
    gzip layer and leaving plain SQL behind a .gz name.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  pg_dump {label} -> {out_path}")
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
        returncode = proc.wait(timeout=900)
    if returncode != 0:
        out_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"pg_dump for {label} failed (exit {returncode}):\n"
            f"{stderr.decode('utf-8', errors='replace')}"
        )
    size = out_path.stat().st_size
    print(f"    -> {size:,} bytes")


def run_backups(source_url: str, target_url: str) -> tuple[Path, Path]:
    if shutil.which("pg_dump") is None:
        raise RuntimeError(
            "pg_dump not found on PATH. Install the postgres client tools or pass --skip-backup."
        )
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ts = utc_stamp()
    v1_path = BACKUPS_DIR / f"v1-source-{ts}.sql.gz"
    v2_path = BACKUPS_DIR / f"v2-target-{ts}.sql.gz"
    print("Phase -1: running pg_dump backups")
    run_pg_dump(source_url, v1_path, "v1 source")
    run_pg_dump(target_url, v2_path, "v2 target")
    return v1_path, v2_path


# -----------------------------------------------------------------------------
# Phase 0 - preflight
# -----------------------------------------------------------------------------


def fetch_columns(conn: PgConnection, table_name: str) -> list[str]:
    """Return column names of `table_name` in ordinal_position order."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )
        return [r[0] for r in cur.fetchall()]


def preflight(
    source_conn: PgConnection,
    target_conn: PgConnection,
) -> dict[int, int]:
    """Verify schema, load level->duration, sanity-check source columns."""
    print("Phase 0: preflight")

    with target_conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ANY(%s)
            """,
            (TARGET_TABLES,),
        )
        present = {r[0] for r in cur.fetchall()}
    missing = [t for t in TARGET_TABLES if t not in present]
    if missing:
        raise RuntimeError(
            f"Target DB is missing required tables: {missing}. "
            f"Run `alembic upgrade head` first."
        )

    with target_conn.cursor() as cur:
        cur.execute("SELECT level, duration_in_min FROM contest_levels")
        level_to_duration = {int(r[0]): int(r[1]) for r in cur.fetchall()}
    if not level_to_duration:
        raise RuntimeError(
            "contest_levels is empty. Run `scripts/migrate_level_table.py` first."
        )
    print(f"  loaded {len(level_to_duration)} contest_levels")

    with source_conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT contest_level FROM user_contest WHERE contest_level IS NOT NULL"
        )
        src_levels = {int(r[0]) for r in cur.fetchall()}
    unknown = sorted(src_levels - set(level_to_duration))
    if unknown:
        raise RuntimeError(
            f"user_contest references {len(unknown)} levels not in contest_levels: {unknown}. "
            f"Re-run scripts/migrate_level_table.py or fix the level data."
        )

    src_cols_list = fetch_columns(source_conn, "user_contest")
    if not src_cols_list:
        raise RuntimeError("source DB has no user_contest table")
    source_cols_lower = {c.lower() for c in src_cols_list}
    required_lower = {
        "id", "email", "date", "contest_no", "contest_level", "topic",
        "rating", "performance", "delta",
        "contestid1", "index1", "r1", "t1",
        "contestid2", "index2", "r2", "t2",
        "contestid3", "index3", "r3", "t3",
        "contestid4", "index4", "r4", "t4",
        "createdat",
    }
    missing_cols = sorted(required_lower - source_cols_lower)
    if missing_cols:
        raise RuntimeError(
            f"user_contest missing required columns (case-insensitive): {missing_cols}. "
            f"Actual: {src_cols_list}"
        )

    ud_cols = fetch_columns(source_conn, "user_data")
    if not ud_cols:
        raise RuntimeError("source DB has no user_data table")
    ud_have = {c.lower() for c in ud_cols}
    ud_missing = sorted({"email", "codeforces_username"} - ud_have)
    if ud_missing:
        raise RuntimeError(
            f"user_data missing required columns (case-insensitive): {ud_missing}. "
            f"Actual: {ud_cols}"
        )

    print("  preflight ok")
    return level_to_duration


# -----------------------------------------------------------------------------
# Phase 1 - wipe + themes
# -----------------------------------------------------------------------------


def truncate_or_delete_for_user(
    target_conn: PgConnection,
    email: str | None,
) -> None:
    with target_conn.cursor() as cur:
        if email is None:
            print("Phase 1: TRUNCATE v2 tables (CASCADE, RESTART IDENTITY)")
            cur.execute(
                f"TRUNCATE {', '.join(TRUNCATE_TABLES)} RESTART IDENTITY CASCADE;"
            )
        else:
            print(f"Phase 1: DELETE existing v2 rows for email={email!r}")
            cur.execute(
                """
                DELETE FROM contest_session_problems_status
                WHERE session_id IN (
                    SELECT id FROM contest_session
                    WHERE user_id IN (SELECT id FROM users WHERE email = %s)
                );
                """,
                (email,),
            )
            cur.execute(
                """
                DELETE FROM contest_session_seen_problem
                WHERE session_id IN (
                    SELECT id FROM contest_session
                    WHERE user_id IN (SELECT id FROM users WHERE email = %s)
                );
                """,
                (email,),
            )
            cur.execute(
                """
                DELETE FROM contest_session_result
                WHERE session_id IN (
                    SELECT id FROM contest_session
                    WHERE user_id IN (SELECT id FROM users WHERE email = %s)
                );
                """,
                (email,),
            )
            cur.execute(
                """
                DELETE FROM contest_session
                WHERE user_id IN (SELECT id FROM users WHERE email = %s);
                """,
                (email,),
            )
            cur.execute("DELETE FROM users WHERE email = %s;", (email,))


def seed_themes(source_conn: PgConnection, target_conn: PgConnection) -> int:
    """Insert all normalized + aliased + default themes; ON CONFLICT DO NOTHING."""
    with source_conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT lower(trim(topic))
            FROM user_contest
            WHERE topic IS NOT NULL AND trim(topic) <> ''
            """
        )
        raw = [r[0] for r in cur.fetchall()]
    themes = {THEME_ALIASES.get(t, t) for t in raw}
    themes.add(DEFAULT_THEME)
    rows = [(t,) for t in sorted(themes)]
    with target_conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO contest_theme (theme) VALUES %s ON CONFLICT (theme) DO NOTHING",
            rows,
            page_size=200,
        )
    print(f"  seeded {len(rows)} themes")
    return len(rows)


# -----------------------------------------------------------------------------
# Phase 2 - users
# -----------------------------------------------------------------------------


def insert_users(
    source_conn: PgConnection,
    target_conn: PgConnection,
    email_filter: str | None,
    skip_log: SkipLogger,
) -> dict[str, str]:
    print("Phase 2: users")
    if email_filter:
        sql = (
            "SELECT email, codeforces_username FROM user_data "
            "WHERE lower(trim(email)) = %s"
        )
        params: tuple = (email_filter,)
    else:
        sql = "SELECT email, codeforces_username FROM user_data"
        params = ()

    with source_conn.cursor() as cur:
        cur.execute(sql, params)
        raw_rows = cur.fetchall()

    email_to_user_id: dict[str, str] = {}
    used_ids: set[str] = set()
    handle_seen: set[str] = set()
    insert_rows: list[tuple] = []

    for raw_email, raw_handle in raw_rows:
        if raw_email is None:
            skip_log.skip(None, None, "EMAIL_EMPTY", {"raw_email": raw_email})
            continue
        email = raw_email.strip().lower()
        if not email:
            skip_log.skip(None, raw_email, "EMAIL_EMPTY", {"raw_email": raw_email})
            continue
        if email in email_to_user_id:
            skip_log.skip(None, email, "USER_DUPLICATE_EMAIL", {"raw_email": raw_email})
            continue

        handle: str | None
        if raw_handle is None:
            handle = None
        else:
            stripped = raw_handle.strip()
            handle = stripped if stripped else None
        if handle is not None and handle in handle_seen:
            skip_log.skip(
                None,
                email,
                "CODEFORCES_HANDLE_DUPLICATE",
                {"handle": handle, "action": "kept user with NULL handle"},
            )
            handle = None
        if handle is not None:
            handle_seen.add(handle)

        user_id = Utils.generate_id()
        while user_id in used_ids:
            skip_log.skip(None, email, "USER_ID_COLLISION_RETRY", {"id": user_id})
            user_id = Utils.generate_id()
        used_ids.add(user_id)
        email_to_user_id[email] = user_id

        insert_rows.append(
            (
                user_id,
                email,
                handle,
                None,  # contest_rating - backfilled in Phase 4
                None,  # max_contest_rating
                None,  # best_performance
                0,     # contest_attempts (NOT NULL)
            )
        )

    if not insert_rows:
        print("  no users to insert")
        return email_to_user_id

    insert_sql = (
        "INSERT INTO users "
        "(id, email, codeforces_handle, contest_rating, max_contest_rating, "
        " best_performance, contest_attempts) VALUES %s"
    )
    with target_conn.cursor() as cur:
        execute_values(cur, insert_sql, insert_rows, page_size=USER_BATCH_SIZE)
    print(f"  inserted {len(insert_rows)} users")
    return email_to_user_id


# -----------------------------------------------------------------------------
# Phase 3 - contest sessions, results, statuses, seen_problems
# -----------------------------------------------------------------------------


SESSION_INSERT_SQL = (
    'INSERT INTO contest_session '
    '(id, user_id, level, theme, duration_in_min, status, starts_at, ends_at, '
    ' "p1_cf_contestID", p1_cf_index, "p2_cf_contestID", p2_cf_index, '
    ' "p3_cf_contestID", p3_cf_index, "p4_cf_contestID", p4_cf_index) '
    'VALUES %s'
)

RESULT_INSERT_SQL = (
    "INSERT INTO contest_session_result "
    "(session_id, solved_count, performance, rating_before, rating_after, rating_delta) "
    "VALUES %s"
)

STATUS_INSERT_SQL = (
    'INSERT INTO contest_session_problems_status '
    '(session_id, problem_number, "problem_contestID", problem_index, problem_rating, '
    ' status, accepted_at, solved_in_min) '
    'VALUES %s'
)

SEEN_INSERT_SQL = (
    'INSERT INTO contest_session_seen_problem '
    '(session_id, "cf_problem_contestID", cf_problem_index) '
    'VALUES %s'
)


def _validate_problem_refs(row: dict[str, Any]) -> bool:
    for k in (1, 2, 3, 4):
        cid = row[f"contestId{k}"]
        idx = row[f"index{k}"]
        if cid is None or idx is None:
            return False
        if isinstance(cid, str) and cid.strip() == "":
            return False
        if isinstance(idx, str) and idx.strip() == "":
            return False
    return True


def _build_problem_status_and_seen(
    session_id: str,
    starts_at: int,
    row: dict[str, Any],
) -> tuple[list[tuple], list[tuple], int]:
    statuses: list[tuple] = []
    seens: list[tuple] = []
    solved_count = 0
    for k in (1, 2, 3, 4):
        cid = str(row[f"contestId{k}"])
        idx = str(row[f"index{k}"])
        rating = int(row[f"R{k}"]) if row[f"R{k}"] is not None else 0
        t_val = row[f"T{k}"]
        if t_val is None:
            status = "UNSOLVED"
            solved_in_min = None
            accepted_at = None
        elif int(t_val) == -1:
            status = "UPSOLVED"
            solved_in_min = None
            accepted_at = None
        else:
            t_int = int(t_val)
            status = "SOLVED"
            solved_in_min = t_int
            accepted_at = str(starts_at + t_int * 60)
            solved_count += 1
        statuses.append(
            (
                session_id,
                k,
                cid,
                idx,
                rating,
                status,
                accepted_at,
                solved_in_min,
            )
        )
        seens.append((session_id, cid, idx))
    return statuses, seens, solved_count


def _row_payload(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id", "email", "date", "contest_no", "contest_level", "topic",
        "rating", "performance", "delta",
        "contestId1", "index1", "R1", "T1",
        "contestId2", "index2", "R2", "T2",
        "contestId3", "index3", "R3", "T3",
        "contestId4", "index4", "R4", "T4",
    )
    return {k: row.get(k) for k in keys}


def stream_and_insert_sessions(
    source_conn: PgConnection,
    target_conn: PgConnection,
    email_to_user_id: dict[str, str],
    level_to_duration: dict[int, int],
    email_filter: str | None,
    skip_log: SkipLogger,
) -> dict[str, int]:
    print("Phase 3: contest sessions / results / statuses / seen_problems")

    select_sql = """
        SELECT DISTINCT ON (email, date, contest_no)
               id, email, date, contest_no, contest_level, topic,
               rating, performance, delta,
               "contestId1","index1","R1","T1",
               "contestId2","index2","R2","T2",
               "contestId3","index3","R3","T3",
               "contestId4","index4","R4","T4",
               "createdAt"
        FROM user_contest
        WHERE (%(email)s::text IS NULL OR lower(trim(email)) = %(email)s)
        ORDER BY email, date, contest_no, "createdAt" DESC NULLS LAST, id DESC
    """

    col_names = [
        "id", "email", "date", "contest_no", "contest_level", "topic",
        "rating", "performance", "delta",
        "contestId1", "index1", "R1", "T1",
        "contestId2", "index2", "R2", "T2",
        "contestId3", "index3", "R3", "T3",
        "contestId4", "index4", "R4", "T4",
        "createdAt",
    ]

    src_cur = source_conn.cursor(name="contest_stream")
    src_cur.itersize = 5000
    src_cur.execute(select_sql, {"email": email_filter})

    sessions_batch: list[tuple] = []
    results_batch: list[tuple] = []
    statuses_batch: list[tuple] = []
    seen_batch: list[tuple] = []

    counters: Counter[str] = Counter()
    kept = 0

    def flush() -> None:
        if not sessions_batch:
            return
        with target_conn.cursor() as tcur:
            execute_values(tcur, SESSION_INSERT_SQL, sessions_batch, page_size=SESSION_BATCH_SIZE)
            if results_batch:
                execute_values(tcur, RESULT_INSERT_SQL, results_batch, page_size=SESSION_BATCH_SIZE)
            if statuses_batch:
                execute_values(tcur, STATUS_INSERT_SQL, statuses_batch, page_size=SESSION_BATCH_SIZE * 4)
            if seen_batch:
                execute_values(tcur, SEEN_INSERT_SQL, seen_batch, page_size=SESSION_BATCH_SIZE * 4)
        sessions_batch.clear()
        results_batch.clear()
        statuses_batch.clear()
        seen_batch.clear()

    try:
        for raw in src_cur:
            counters["total"] += 1
            row = dict(zip(col_names, raw))
            src_id = row["id"]
            raw_email = row["email"]
            email = raw_email.strip().lower() if isinstance(raw_email, str) else None

            if not _validate_problem_refs(row):
                skip_log.skip(src_id, email, "PROBLEMS_MISSING", _row_payload(row))
                continue

            rating = row["rating"]
            performance = row["performance"]
            delta = row["delta"]
            try:
                rating = int(rating) if rating is not None else None
                performance = int(performance) if performance is not None else None
                delta = int(delta) if delta is not None else None
            except (TypeError, ValueError):
                skip_log.skip(src_id, email, "RATING_OUT_OF_RANGE", _row_payload(row))
                continue

            if rating is None or rating < RATING_MIN or rating > RATING_MAX:
                skip_log.skip(src_id, email, "RATING_OUT_OF_RANGE", _row_payload(row))
                continue
            if performance is None or performance < PERF_MIN or performance > PERF_MAX:
                skip_log.skip(src_id, email, "PERFORMANCE_OUT_OF_RANGE", _row_payload(row))
                continue
            if delta is None or abs(delta) > DELTA_ABS_MAX:
                skip_log.skip(src_id, email, "DELTA_OUT_OF_RANGE", _row_payload(row))
                continue

            level = row["contest_level"]
            if level is None or int(level) not in level_to_duration:
                skip_log.skip(src_id, email, "LEVEL_UNKNOWN", _row_payload(row))
                continue
            level = int(level)
            duration = level_to_duration[level]

            t_corrupt = False
            t_exceeds = False
            for k in (1, 2, 3, 4):
                tv = row[f"T{k}"]
                if tv is None:
                    continue
                try:
                    tv_int = int(tv)
                except (TypeError, ValueError):
                    t_corrupt = True
                    break
                if tv_int < -1:
                    t_corrupt = True
                    break
                if tv_int != -1 and tv_int > duration:
                    t_exceeds = True
                    break
            if t_corrupt:
                skip_log.skip(src_id, email, "T_CORRUPT", _row_payload(row))
                continue
            if t_exceeds:
                skip_log.skip(src_id, email, "T_EXCEEDS_DURATION", _row_payload(row))
                continue

            user_id = email_to_user_id.get(email) if email else None
            if not user_id:
                skip_log.skip(src_id, email, "USER_NOT_FOUND", _row_payload(row))
                continue

            session_id = Utils.generate_id()
            theme = normalize_theme(row["topic"])
            starts_at = midnight_utc_unix_seconds(row["date"])
            ends_at = starts_at + duration * 60

            sessions_batch.append(
                (
                    session_id,
                    user_id,
                    level,
                    theme,
                    duration,
                    "FINISHED",
                    starts_at,
                    ends_at,
                    str(row["contestId1"]), str(row["index1"]),
                    str(row["contestId2"]), str(row["index2"]),
                    str(row["contestId3"]), str(row["index3"]),
                    str(row["contestId4"]), str(row["index4"]),
                )
            )

            statuses, seens, solved_count = _build_problem_status_and_seen(
                session_id=session_id,
                starts_at=starts_at,
                row=row,
            )
            statuses_batch.extend(statuses)
            seen_batch.extend(seens)

            rating_before = rating - delta
            results_batch.append(
                (
                    session_id,
                    solved_count,
                    performance,
                    rating_before,
                    rating,        # rating_after
                    delta,         # rating_delta
                )
            )

            kept += 1
            if len(sessions_batch) >= SESSION_BATCH_SIZE:
                flush()

        flush()
    finally:
        src_cur.close()

    counters["kept"] = kept
    counters["skipped"] = sum(skip_log.counts.values())
    print(f"  kept {kept} sessions, skipped {counters['skipped']} rows total (across phases)")
    return dict(counters)


# -----------------------------------------------------------------------------
# Phase 4 - user stats backfill
# -----------------------------------------------------------------------------


def backfill_user_stats(
    target_conn: PgConnection,
    email_filter: str | None,
) -> None:
    print("Phase 4: backfill user stats")

    where_user = ""
    params: tuple = ()
    if email_filter:
        where_user = "AND u.email = %s"
        params = (email_filter,)

    sql_attempts = f"""
        UPDATE users u SET contest_attempts = COALESCE(s.cnt, 0)
        FROM (
            SELECT user_id, COUNT(*) AS cnt
            FROM contest_session
            WHERE status = 'FINISHED'
            GROUP BY user_id
        ) s
        WHERE u.id = s.user_id {where_user}
    """

    sql_max = f"""
        UPDATE users u
        SET max_contest_rating = s.max_rating,
            best_performance   = s.best_perf
        FROM (
            SELECT cs.user_id,
                   MAX(csr.rating_after) AS max_rating,
                   MAX(csr.performance)  AS best_perf
            FROM contest_session cs
            JOIN contest_session_result csr ON csr.session_id = cs.id
            WHERE cs.status = 'FINISHED'
            GROUP BY cs.user_id
        ) s
        WHERE u.id = s.user_id {where_user}
    """

    sql_current = f"""
        UPDATE users u
        SET contest_rating = s.rating_after
        FROM (
            SELECT DISTINCT ON (cs.user_id) cs.user_id, csr.rating_after
            FROM contest_session cs
            JOIN contest_session_result csr ON csr.session_id = cs.id
            WHERE cs.status = 'FINISHED'
            ORDER BY cs.user_id, cs.starts_at DESC, csr.id DESC
        ) s
        WHERE u.id = s.user_id {where_user}
    """

    with target_conn.cursor() as cur:
        cur.execute(sql_attempts, params)
        print(f"  contest_attempts: {cur.rowcount} rows updated")
        cur.execute(sql_max, params)
        print(f"  max_rating + best_perf: {cur.rowcount} rows updated")
        cur.execute(sql_current, params)
        print(f"  contest_rating: {cur.rowcount} rows updated")


# -----------------------------------------------------------------------------
# Phase 5 - report
# -----------------------------------------------------------------------------


def write_report(
    args: argparse.Namespace,
    skip_log: SkipLogger,
    counters: dict[str, int],
    user_count: int,
    backup_paths: tuple[Path, Path] | None,
    committed: bool,
) -> None:
    lines: list[str] = []
    lines.append(f"themecp v1 -> v2 migration report  ({utc_stamp()})")
    lines.append("=" * 72)
    mode = f"single-user ({args.email})" if args.email else "full"
    lines.append(f"mode               : {mode}")
    lines.append(f"dry-run            : {args.dry_run}")
    lines.append(f"committed          : {committed}")
    if backup_paths:
        lines.append(f"v1 backup          : {backup_paths[0]}")
        lines.append(f"v2 backup          : {backup_paths[1]}")
        lines.append('restore (v2)       : gunzip -c <v2 backup> | psql "$PG_DATABASE_URL"')
    else:
        lines.append("v1 backup          : (skipped)")
        lines.append("v2 backup          : (skipped)")
    lines.append("")
    lines.append("totals")
    lines.append("-" * 72)
    lines.append(f"users inserted          : {user_count}")
    lines.append(f"user_contest rows seen  : {counters.get('total', 0)}")
    lines.append(f"sessions kept           : {counters.get('kept', 0)}")
    lines.append(f"rows skipped (all)      : {sum(skip_log.counts.values())}")
    lines.append("")
    lines.append("skipped breakdown")
    lines.append("-" * 72)
    if skip_log.counts:
        for reason, count in sorted(skip_log.counts.items(), key=lambda kv: -kv[1]):
            lines.append(f"  {reason:<32} {count}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append(f"skipped rows CSV   : {SKIPPED_CSV_PATH}")
    REPORT_TXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_TXT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {REPORT_TXT_PATH}")


# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------


def main() -> int:
    args = parse_args()

    source_url = os.environ.get("LEGACY_PG_DATABASE_URL")
    target_url = os.environ.get("PG_DATABASE_URL")
    missing = [
        name for name, val in (
            ("LEGACY_PG_DATABASE_URL", source_url),
            ("PG_DATABASE_URL", target_url),
        ) if not val
    ]
    if missing:
        print(
            f"error: missing required env var(s): {', '.join(missing)}.\n"
            "  set them in .env (recommended) or export in your shell:\n"
            "    LEGACY_PG_DATABASE_URL = connection string for the old (v1) Railway DB\n"
            "    PG_DATABASE_URL        = connection string for the new (v2) target DB",
            file=sys.stderr,
        )
        return 2

    if not args.dry_run:
        if not args.confirm_backups_done:
            print(
                "refusing to run: --confirm-backups-done is required for non-dry-run.\n"
                "  re-run with --dry-run first, or pass --confirm-backups-done if you "
                "have backups in hand.",
                file=sys.stderr,
            )
            return 2
        if args.email is None and not args.confirm_truncate:
            print(
                "refusing to run: full-mode non-dry-run requires --confirm-truncate "
                "(this will TRUNCATE all v2 user-related tables).",
                file=sys.stderr,
            )
            return 2

    if args.email:
        args.email = args.email.strip().lower()

    skip_log = SkipLogger(SKIPPED_CSV_PATH)
    source_conn: PgConnection | None = None
    target_conn: PgConnection | None = None
    backup_paths: tuple[Path, Path] | None = None
    counters: dict[str, int] = {}
    user_count = 0
    committed = False

    try:
        if args.dry_run or args.skip_backup:
            if args.skip_backup and not args.dry_run:
                print("WARNING: --skip-backup specified; not running pg_dump")
        else:
            backup_paths = run_backups(source_url, target_url)

        source_conn = psycopg2.connect(source_url)
        # readonly=True prevents writes; autocommit must be False so the server-side
        # (named) cursor in Phase 3 has a surrounding transaction.
        source_conn.set_session(readonly=True, autocommit=False)
        target_conn = psycopg2.connect(target_url)
        target_conn.autocommit = False

        level_to_duration = preflight(source_conn, target_conn)

        truncate_or_delete_for_user(target_conn, args.email)
        seed_themes(source_conn, target_conn)

        email_to_user_id = insert_users(source_conn, target_conn, args.email, skip_log)
        user_count = len(email_to_user_id)

        counters = stream_and_insert_sessions(
            source_conn=source_conn,
            target_conn=target_conn,
            email_to_user_id=email_to_user_id,
            level_to_duration=level_to_duration,
            email_filter=args.email,
            skip_log=skip_log,
        )

        backfill_user_stats(target_conn, args.email)

        if args.dry_run:
            target_conn.rollback()
            print("DRY RUN -- rolled back")
        else:
            target_conn.commit()
            committed = True
            print(
                f"Migration complete: {user_count} users, "
                f"{counters.get('kept', 0)} sessions"
            )
        return 0

    except Exception as exc:
        if target_conn is not None:
            try:
                target_conn.rollback()
            except Exception:
                pass
        print(f"\nmigration failed: {exc}", file=sys.stderr)
        return 1

    finally:
        try:
            skip_log.close()
        except Exception:
            pass
        try:
            write_report(args, skip_log, counters, user_count, backup_paths, committed)
        except Exception as exc:
            print(f"  (failed to write report: {exc})", file=sys.stderr)
        if source_conn is not None:
            try:
                source_conn.close()
            except Exception:
                pass
        if target_conn is not None:
            try:
                target_conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
