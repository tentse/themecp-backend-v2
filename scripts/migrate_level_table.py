#!/usr/bin/env python3
"""
Migrate level table data from source Railway PostgreSQL to the current backend database.

Usage:
    # Set target DB via env (default: local themecp_v2)
    export PG_DATABASE_URL="postgresql://..."

    # Run migration (source DB from env)
    SOURCE_DATABASE_URL="postgresql://user:password@host:port/dbname" \\
        python scripts/migrate_level_table.py

    # Dry run (no writes)
    SOURCE_DATABASE_URL="..." python scripts/migrate_level_table.py --dry-run
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
from psycopg2.extras import execute_values

# Target schema: contest_levels (id, level, duration_in_min, performance, p1_rating, p2_rating, p3_rating, p4_rating)
TARGET_TABLE = "contest_levels"
TARGET_COLUMNS = [
    "level",
    "duration_in_min",
    "performance",
    "p1_rating",
    "p2_rating",
    "p3_rating",
    "p4_rating",
]

# Possible source table names (try in order)
SOURCE_TABLE_CANDIDATES = ["level_sheet", "level", "contest_levels", "contest_level"]

# Column name mapping: source_name -> target_name (for when old DB uses different names)
# level_sheet uses: level, time, Performance, P1, P2, P3, P4
COLUMN_MAPPING = {
    "level": "level",
    "duration_in_min": "duration_in_min",
    "duration": "duration_in_min",
    "time": "duration_in_min",
    "duration_in_minutes": "duration_in_min",
    "performance": "performance",
    "Performance": "performance",
    "p1_rating": "p1_rating",
    "p1": "p1_rating",
    "P1": "p1_rating",
    "p2_rating": "p2_rating",
    "p2": "p2_rating",
    "P2": "p2_rating",
    "p3_rating": "p3_rating",
    "p3": "p3_rating",
    "P3": "p3_rating",
    "p4_rating": "p4_rating",
    "p4": "p4_rating",
    "P4": "p4_rating",
}


def get_source_table_name(conn) -> str | None:
    """Discover which level-related table exists in the source DB."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('level_sheet', 'level', 'contest_levels', 'contest_level')
            ORDER BY CASE table_name
                WHEN 'level_sheet' THEN 1
                WHEN 'level' THEN 2
                WHEN 'contest_levels' THEN 3
                WHEN 'contest_level' THEN 4
                ELSE 5
            END
        """)
        row = cur.fetchone()
        return row[0] if row else None


def get_source_columns(conn, table_name: str) -> list[str]:
    """Get column names from source table."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = %s
            AND column_name != 'id'
            ORDER BY ordinal_position
        """, (table_name,))
        return [r[0] for r in cur.fetchall()]


def map_row_to_target(row_dict: dict, source_columns: list[str]) -> tuple | None:
    """Map a source row to target (level, duration_in_min, performance, p1..p4)."""
    mapped = []
    for col in TARGET_COLUMNS:
        # Find source column that maps to this target column (check exact and lowercase)
        value = None
        for src_col in source_columns:
            target = COLUMN_MAPPING.get(src_col) or COLUMN_MAPPING.get(src_col.lower())
            if target == col:
                value = row_dict.get(src_col)
                break
        if value is None:
            return None
        # Convert to int (source may have varchar with BOM/whitespace)
        try:
            cleaned = str(value).strip().strip("\ufeff")  # strip BOM
            mapped.append(int(cleaned))
        except (ValueError, TypeError):
            return None
    return tuple(mapped)


def migrate(
    source_url: str,
    target_url: str,
    dry_run: bool = False,
) -> int:
    """Migrate all rows from source level table to target contest_levels."""
    if dry_run:
        print("DRY RUN - no data will be written to target")

    source_conn = psycopg2.connect(source_url)
    target_conn = psycopg2.connect(target_url)

    try:
        # Discover source table
        source_table = get_source_table_name(source_conn)
        if not source_table:
            raise RuntimeError(
                f"No level table found in source. Looked for: {SOURCE_TABLE_CANDIDATES}"
            )
        print(f"Source table: {source_table}")

        source_columns = get_source_columns(source_conn, source_table)
        print(f"Source columns: {source_columns}")

        # Build SELECT - exclude id, include all mapped columns
        select_cols = ", ".join(f'"{c}"' for c in source_columns)
        select_sql = f'SELECT {select_cols} FROM "{source_table}"'

        with source_conn.cursor() as cur:
            cur.execute(select_sql)
            col_names = [d[0] for d in cur.description]
            rows = cur.fetchall()

        print(f"Fetched {len(rows)} rows from source")

        if not rows:
            print("No rows to migrate.")
            return 0

        # Map rows to target schema
        target_rows = []
        for row in rows:
            row_dict = dict(zip(col_names, row))
            mapped = map_row_to_target(row_dict, source_columns)
            if mapped is None:
                print("Skipping row (incomplete mapping):", row_dict)
                continue
            target_rows.append(mapped)

        if not target_rows:
            raise RuntimeError("No rows could be mapped to target schema")

        print(f"Mapped {len(target_rows)} rows for insert")

        if dry_run:
            for i, r in enumerate(target_rows[:5]):
                print(f"  Sample {i + 1}: {r}")
            if len(target_rows) > 5:
                print(f"  ... and {len(target_rows) - 5} more")
            return len(target_rows)

        # Insert into target
        insert_sql = f"""
            INSERT INTO {TARGET_TABLE} ({", ".join(TARGET_COLUMNS)})
            VALUES %s
            ON CONFLICT (level) DO UPDATE SET
                duration_in_min = EXCLUDED.duration_in_min,
                performance = EXCLUDED.performance,
                p1_rating = EXCLUDED.p1_rating,
                p2_rating = EXCLUDED.p2_rating,
                p3_rating = EXCLUDED.p3_rating,
                p4_rating = EXCLUDED.p4_rating
        """
        with target_conn.cursor() as cur:
            execute_values(cur, insert_sql, target_rows, page_size=100)
        target_conn.commit()
        print(f"Inserted/updated {len(target_rows)} rows into {TARGET_TABLE}")

        return len(target_rows)

    finally:
        source_conn.close()
        target_conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate level table from source PostgreSQL to current backend."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and report only, do not write to target DB",
    )
    args = parser.parse_args()

    source_url = os.environ.get("SOURCE_DATABASE_URL")
    if not source_url:
        print(
            "Error: SOURCE_DATABASE_URL is required.\n"
            "Example: postgresql://user:pass@host:port/dbname",
            file=sys.stderr,
        )
        sys.exit(1)

    target_url = os.environ.get(
        "PG_DATABASE_URL",
        "postgresql://themecp:themecp@localhost:5432/themecp_v2",
    )

    try:
        count = migrate(
            source_url=source_url,
            target_url=target_url,
            dry_run=args.dry_run,
        )
        print(f"Migration complete. Total rows: {count}")
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
