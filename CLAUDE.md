# stat-tab-importer (STI)

A CLI utility for importing data from the Swiss Federal Statistical Office (BFS) into local files or databases, with reusable named import configurations.

## Project purpose

The Swiss Federal Statistical Office publishes statistical data cubes through two distinct APIs:

- **PxWeb API** — `https://www.pxweb.bfs.admin.ch/api/v1/` — returns JSON-stat format; used for most stat-tab data cubes (e.g., agricultural, demographic tables). Queried via HTTP POST with a JSON payload specifying dimension filters.
- **Swiss Stats Explorer (SSE) / SDMX API** — `https://disseminate.stats.swiss/rest` — returns SDMX-CSV; used for time-series dataflows identified by a `dataflow` key (e.g., vital statistics, national accounts).

Each import is defined by a named JSON config file. The config file drives which API and which cube/dataflow to query, with what filters. The importer reads the config, calls the API, and writes a CSV output.

## Repository layout

```
stattab/
├── CLAUDE.md
├── pyproject.toml        # uv-managed project and dependencies
├── uv.lock
├── .venv/
├── stattab_imp.py        # PxWeb API importer
├── swiss-stats-explorer.py  # SSE / SDMX importer
├── configs/
│   ├── farms-bs.json     # example PxWeb config (agricultural holdings, Basel-Stadt)
│   └── births_sse.json   # example SSE config (vital statistics)
└── *.csv                 # generated output files (gitignored)
```

## Config file formats

### PxWeb config (`<name>.json`)

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

### SSE / SDMX config (`<name>.json`)

```json
{
  "dataflow": "<agency>.<provider>,<dataflow-id>,<version>",
  "key": "<dimension-key-string>",
  "params": {
    "startPeriod": "YYYY",
    "endPeriod": "YYYY"
  }
}
```

`key` follows SDMX conventions: `_T` means "all", dimensions separated by `.`.

## Running an import

```bash
# PxWeb cube
python stattab_imp.py farms-bs

# SSE / SDMX dataflow
python swiss-stats-explorer.py births_sse
```

Both scripts accept the config name (without `.json`) as a positional argument and write `<name>.csv` to the same directory.

## Environment

- Python 3.12+, managed with [uv](https://docs.astral.sh/uv/)
- `uv sync` to create the virtual environment and install dependencies
- `uv run python stattab_imp.py <config>` to run without activating the venv

Dependencies (`pyproject.toml`):
  - `requests` — HTTP calls to BFS APIs
  - `pandas` — data manipulation and CSV export

## API notes

- PxWeb API returns `json-stat` format. Dimension categories are looked up via `dataset.dimension[id].category.{index,label}`. Values are iterated in row-major order over the cartesian product of dimension sizes.
- SSE API returns SDMX-CSV when the `Accept: application/vnd.sdmx.data+csv;version=1.0.0` header is set. `lang` and `format` query params are not supported and must be stripped before the request.
- The SSE API does not expose all BFS datasets — some cubes (e.g., births by municipality) are only available through PxWeb.

## Claude permissions

Claude has full autonomy within this repository:

- May read, create, edit, and delete any file without asking for confirmation.
- May run any command needed to build, test, or maintain the project.
- May commit changes directly once satisfied with the result.
- May push to the remote once git is configured — no need to ask for confirmation before pushing.

## Development conventions

- Keep each importer as a self-contained script; no shared library layer unless there are at least three callers.
- Config files are the user-facing interface — keep their schema simple and stable.
- Output is always CSV by default; do not change the default output format without a clear user request.
- Do not hardcode language (`de`/`fr`/`it`/`en`) — make it a config field when needed.
