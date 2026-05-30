# stat-tab-importer

A CLI utility for downloading statistical data cubes from the [Swiss Federal Statistical Office (BFS)](https://www.bfs.admin.ch) into local CSV files, driven by reusable named JSON config files.

## Background

The BFS publishes data through the **PxWeb API** (`pxweb.bfs.admin.ch`). Each data cube is queried via an HTTP POST with a JSON payload that specifies which dimensions and values to include. The response is in `json-stat` format and is converted to a flat CSV file.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) — or pip

## Installation

### With uv (recommended)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repo and set up the environment
git clone <repo-url>
cd stattab
uv sync
```

### With pip

```bash
git clone <repo-url>
cd stattab
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install requests pandas
```

## Usage

```bash
# Run a single import
uv run python stat-tab-imp.py <config-name>

# Run all imports in the configs/ folder
uv run python stat-tab-imp.py --all

# Show first rows of output after each import
uv run python stat-tab-imp.py <config-name> --verbose
uv run python stat-tab-imp.py --all --verbose

# With activated venv (instead of uv run)
python stat-tab-imp.py <config-name>
```

`<config-name>` is the name of a JSON file in the `configs/` directory (without the `.json` extension). Output CSVs are written to `output/<config-name>.csv`. The `output/` directory is created automatically.

When using `--all`, every `.json` file in `configs/` is imported in turn. Failures are reported per-config but do not abort the remaining imports; a summary line is printed at the end.

### Example

```bash
uv run python stat-tab-imp.py farms-bs
# → output/farms-bs.csv

uv run python stat-tab-imp.py --all
# → output/farms-bs.csv
# → output/...csv
# 2/2 imports succeeded.
```

## How it works

### 1. Find your dataset on the BFS website

Go to [https://www.pxweb.bfs.admin.ch/pxweb/de/](https://www.pxweb.bfs.admin.ch/pxweb/de/) and browse the topic tree to find the data cube you need. Click through to open it.

### 2. Configure your query interactively

The BFS Stat-Tab interface lets you select which values you want for each dimension (e.g. specific cantons, years, categories). Use the checkboxes to narrow the selection down to what you actually need — the API will return exactly what you configure here.

### 3. Generate the table and download the API query

Click **Tabelle erstellen** (Create table) to preview the result. Once the table is shown, look for the option **API-Abfrage für diese Tabelle** (API query for this table). In the dialog that opens, click **Save API query (JSON)** — this downloads a `.json` file that contains the full query configuration.

### 4. Save the downloaded file to the configs folder

Move or copy the downloaded `.json` file into the `configs/` folder. You can rename it to something descriptive (e.g. `farms-bs.json`). No further editing is needed — the importer reads the file format produced by the BFS tool directly.

### 5. Adjust and refine

Open the config file in a text editor and tweak the `values` arrays to change the scope of the import. Common adjustments:

- Remove municipality-level entries and keep only canton codes and the Switzerland total (code `0`) to get a national overview.
- Add or remove years if the cube has a time dimension.
- Remove a dimension's entry from `query` entirely to include **all** its values.

Re-run the import after each change to verify the result.

### 6. Run the import

```bash
# Single config
uv run python stat-tab-imp.py farms-bs

# All configs at once
uv run python stat-tab-imp.py --all
```

The output CSV is written to `output/<config-name>.csv` and can be opened directly in Excel, loaded into pandas, or imported into a database.

## Config file format

Two formats are supported.

### Web-export format (recommended)

After configuring your query on the BFS website and clicking **API-Abfrage für diese Tabelle**, use the **Download** option to save the JSON file. Place it directly in `configs/` — no manual editing required.

The downloaded file looks like this:

```json
{
  "queryObj": {
    "query": [
      {
        "code": "<dimension-label>",
        "selection": {
          "filter": "item",
          "values": ["<code1>", "<code2>"]
        }
      }
    ],
    "response": { "format": "json-stat" }
  },
  "tableIdForQuery": "<cube-id>.px"
}
```

The importer constructs the API URL automatically from `tableIdForQuery`. The language defaults to `de`; add a `"lang"` field at the top level to override:

```json
{
  "lang": "en",
  "queryObj": { ... },
  "tableIdForQuery": "px-x-1903020100_102.px"
}
```

### Manual format

If you prefer to write the config by hand or need full control over the URL:

```json
{
  "url": "https://www.pxweb.bfs.admin.ch/api/v1/de/<cube-id>/<cube-id>.px",
  "payload": {
    "query": [
      {
        "code": "<dimension-label>",
        "selection": {
          "filter": "item",
          "values": ["<code1>", "<code2>"]
        }
      }
    ],
    "response": { "format": "json-stat" }
  }
}
```

- `url` — full PxWeb API endpoint; language code (`de`/`fr`/`it`/`en`) is part of the path
- `payload.query` — dimension filters; omit a dimension entirely to include all its values
- `payload.response.format` — must be `"json-stat"`

## Using stat-tab-imp as a library

`stat-tab-imp.py` exposes a `fetch_dataframe(config_path)` function that downloads a cube and returns a `pandas.DataFrame` without writing any files. Use this when you want to process or store the data yourself rather than getting a CSV.

Because the filename contains hyphens, it cannot be imported with a normal `import` statement. Use `importlib` instead:

```python
import importlib.util
from pathlib import Path

def load_stattab_module():
    spec = importlib.util.spec_from_file_location(
        "stattab_imp",
        Path(__file__).parent / "stat-tab-imp.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

stattab = load_stattab_module()
config_path = Path("configs/farms-bs.json")
df = stattab.fetch_dataframe(config_path)  # returns pd.DataFrame or None on error
```

### Example: import into SQLite

`stattab_to_sqlite.py` is a ready-to-run example of this pattern. It fetches a cube and loads it into an SQLite table using `pandas.to_sql()`:

```bash
# Create/replace table (default)
uv run python stattab_to_sqlite.py farms-bs

# Custom database file and table name
uv run python stattab_to_sqlite.py farms-bs --db mydata.db --table agricultural_holdings

# Append rows instead of replacing the table
uv run python stattab_to_sqlite.py farms-bs --append
```

The config name follows the same rules as `stat-tab-imp.py` — pass the filename without `.json`, or with the full name including any `.px` suffix:

```bash
uv run python stattab_to_sqlite.py pxapi-api_table_px-x-1903020100_102.px
```

The same `load_stattab_module()` + `fetch_dataframe()` pattern works for any other target — a PostgreSQL database, an API call, a reporting pipeline, etc. Only the part after `df = stattab.fetch_dataframe(config_path)` needs to change.

## Project layout

```
stattab/
├── stat-tab-imp.py        # PxWeb importer — CLI and library
├── stattab_to_sqlite.py   # example: fetch cube → SQLite table
├── pyproject.toml         # dependencies
├── configs/
│   └── farms-bs.json      # example: agricultural holdings, Basel-Stadt
└── output/                # generated CSVs (gitignored)
```
