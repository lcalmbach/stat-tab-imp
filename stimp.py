import argparse
import json
import requests
import pandas as pd
from itertools import product
from pathlib import Path


BASE_URL = "https://www.pxweb.bfs.admin.ch/api/v1"


def resolve_config(config: dict, config_name: str) -> tuple[str, dict] | None:
    """Derive the API endpoint URL and POST payload from a config dict.

    Supports two config formats:
    - Web-export format: keys ``queryObj`` and ``tableIdForQuery`` (downloaded
      directly from the BFS Stat-Tab interface). The URL is constructed from
      ``tableIdForQuery`` and the optional ``lang`` field (defaults to ``"de"``).
    - Manual format: explicit ``url`` and ``payload`` keys.

    Returns a ``(url, payload)`` tuple, or ``None`` if neither format is
    recognised (a warning is printed in that case).
    """
    if "queryObj" in config and "tableIdForQuery" in config:
        table_id = config["tableIdForQuery"]          # e.g. "px-x-1903020100_102.px"
        folder = table_id.removesuffix(".px")         # e.g. "px-x-1903020100_102"
        lang = config.get("lang", "de")
        url = f"{BASE_URL}/{lang}/{folder}/{table_id}"
        payload = config["queryObj"]
        return url, payload

    if "url" in config and "payload" in config:
        return config["url"], config["payload"]

    print(f"[{config_name}] Skipped: config must have either 'url'+'payload' or 'queryObj'+'tableIdForQuery'")
    return None


def fetch_dataframe(config_path: Path) -> pd.DataFrame | None:
    """Download a BFS PxWeb cube and return it as a flat DataFrame.

    Reads the JSON config at *config_path*, calls the PxWeb API, and unpacks
    the ``json-stat`` response into one row per cell of the data cube. Each
    dimension becomes a column (using the dimension's display label), and the
    measured value is in a final ``value`` column. Missing cells are ``None``.

    Does not write any files — use :func:`run_import` for CSV output or pass
    the returned DataFrame to your own storage layer.

    Returns the DataFrame on success, or ``None`` if the config is invalid or
    the API call fails (an explanatory message is printed in that case).
    """
    config_name = config_path.stem
    config = json.loads(config_path.read_text())

    resolved = resolve_config(config, config_name)
    if resolved is None:
        return None
    url, payload = resolved

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.HTTPError:
        if response.status_code == 403:
            print(
                f"[{config_name}] 403 Forbidden — the result set is likely too large. "
                "Add dimension filters (e.g. restrict 'Jahr') to reduce the number of cells below the API limit (~10,000)."
            )
        else:
            print(f"[{config_name}] API error {response.status_code}: {response.text[:300]}")
        return None

    data = response.json()
    ds = data["dataset"]
    dim_ids = ds["dimension"]["id"]
    dim_sizes = ds["dimension"]["size"]
    dimensions = ds["dimension"]
    values = iter(ds["value"])

    index_maps = {}
    for dim_id in dim_ids:
        cat = dimensions[dim_id]["category"]
        index_maps[dim_id] = {v: k for k, v in cat["index"].items()}

    rows = []
    for combo in product(*[range(s) for s in dim_sizes]):
        row = {}
        for i, idx in enumerate(combo):
            dim_id = dim_ids[i]
            cat = dimensions[dim_id]["category"]
            key = index_maps[dim_id][idx]
            row[dim_id] = cat.get("label", {}).get(key, key)
        raw = next(values)
        row["value"] = None if raw is None else raw
        rows.append(row)

    return pd.DataFrame(rows)


def run_import(config_path: Path, verbose: bool = False) -> bool:
    """Fetch a BFS PxWeb cube and write the result to a CSV file.

    Delegates data retrieval to :func:`fetch_dataframe`, then writes the
    DataFrame to ``output/<config-name>.csv`` relative to the project root.
    The ``output/`` directory is created if it does not exist.

    Args:
        config_path: Path to the JSON config file.
        verbose: If ``True``, print the first few rows of the DataFrame after saving.

    Returns:
        ``True`` on success, ``False`` if the download or config parsing failed.
    """
    config_name = config_path.stem
    df = fetch_dataframe(config_path)
    if df is None:
        return False

    out = config_path.parents[1] / "output" / f"{config_name}.csv"
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    print(f"[{config_name}] Saved {len(df)} rows to {out}")

    if verbose:
        print(df.head())

    return True


def main():
    """CLI entry point.

    Parses arguments and runs one or all imports:

    - ``stimp.py <config>`` — import a single named config.
    - ``stimp.py --all`` — import every ``*.json`` file in ``configs/``.
    - ``-v / --verbose`` — print the first rows of each output DataFrame.
    """
    parser = argparse.ArgumentParser(description="Import data from the BFS PxWeb API.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("config", nargs="?", help="Config name (reads configs/<config>.json, writes output/<config>.csv)")
    group.add_argument("--all", action="store_true", help="Run all imports in the configs/ folder")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print first rows of output")
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    configs_dir = base_dir / "configs"

    if args.all:
        config_files = sorted(configs_dir.glob("*.json"))
        if not config_files:
            raise SystemExit(f"No config files found in {configs_dir}")
        ok = sum(run_import(p, args.verbose) for p in config_files)
        print(f"\n{ok}/{len(config_files)} imports succeeded.")
    else:
        config_name = args.config.removesuffix(".json")
        config_path = configs_dir / f"{config_name}.json"
        if not config_path.exists():
            raise SystemExit(f"Config file not found: {config_path}")
        run_import(config_path, args.verbose)


if __name__ == "__main__":
    main()
