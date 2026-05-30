"""
stattab_to_sqlite.py — download a BFS PxWeb cube and load it into SQLite.

Usage:
    uv run python stattab_to_sqlite.py <config> [--db PATH] [--table NAME] [--append]

Example:
    uv run python stattab_to_sqlite.py farms-bs
    uv run python stattab_to_sqlite.py farms-bs --db mydata.db --table agricultural_holdings
    uv run python stattab_to_sqlite.py farms-bs --append
"""

import argparse
import importlib.util
import sqlite3
from pathlib import Path


def load_stattab_module():
    # importlib needed because the filename contains hyphens
    spec = importlib.util.spec_from_file_location(
        "stattab_imp",
        Path(__file__).parent / "stat-tab-imp.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
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

    stattab = load_stattab_module()
    df = stattab.fetch_dataframe(config_path)
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
