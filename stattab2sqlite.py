"""
stattab2sqlite.py — download a BFS PxWeb cube and load it into SQLite.

Usage:
    uv run python stattab2sqlite.py <config> [--db PATH] [--table NAME] [--append]

Example:
    uv run python stattab2sqlite.py criminal-stats
    uv run python stattab2sqlite.py criminal-stats --db mydata.db --table theft_by_age
    uv run python stattab2sqlite.py criminal-stats --append
"""

import argparse
import sqlite3
from pathlib import Path

import stimp


def main():
    """CLI entry point.

    Reads a named config from ``configs/``, downloads the corresponding BFS
    PxWeb cube via :func:`stimp.fetch_dataframe`, and writes the result into
    an SQLite table using ``pandas.to_sql``.

    Args (CLI):
        config: Config name (without ``.json``), e.g. ``criminal-stats`` or
            ``pxapi-api_table_px-x-1903020100_102.px``.
        --db: Path to the SQLite database file. Created if it does not exist.
            Defaults to ``stattab.db`` in the current directory.
        --table: Name of the target table. Defaults to the config name.
        --append: Append rows to an existing table instead of replacing it.
    """
    parser = argparse.ArgumentParser(
        description="Download a BFS PxWeb cube and import it into an SQLite database."
    )
    parser.add_argument("config", help="Config name (reads configs/<config>.json)")
    parser.add_argument("--db", default="stattab.db", help="SQLite database file (default: stattab.db)")
    parser.add_argument("--table", help="Target table name (default: config name)")
    parser.add_argument("--append", action="store_true", help="Append rows instead of replacing the table")
    args = parser.parse_args()

    config_name = args.config.removesuffix(".json")
    config_path = Path(__file__).parent / "configs" / f"{config_name}.json"
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    df = stimp.fetch_dataframe(config_path)
    if df is None:
        raise SystemExit("Download failed — see error above.")

    table_name = args.table or config_name
    db_path = Path(args.db)
    if_exists = "append" if args.append else "replace"

    con = sqlite3.connect(db_path)
    try:
        df.to_sql(table_name, con, if_exists=if_exists, index=False)
        con.commit()
        print(f"[{config_name}] Loaded {len(df)} rows → table '{table_name}' in {db_path}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
