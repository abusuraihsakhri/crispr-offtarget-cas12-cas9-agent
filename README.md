# CRISPR Offtarget Cas12 Cas9 Agent

### [Open the Live Application →](https://abusuraihsakhri.github.io/crispr-offtarget-cas12-cas9-agent/)

Research-use Cas9/Cas12a supplied-candidate mismatch scoring, browser execution, CLI utilities, and audit/API components.

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-optional-009688.svg?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-supported-2496ED.svg?logo=docker&logoColor=white)

</div>

## What it does

The repository compares a supplied SpCas9 or AsCas12a guide with supplied candidate protospacer sequences using simplified position-weighted mismatch heuristics.

It provides:

- Cas9/Cas12a candidate-sequence assessment with mismatch and seed-mismatch summaries
- Aggregate heuristic specificity scoring and candidate risk tiers
- A static browser application that runs the Python engine client-side with Pyodide
- Command-line workflows for single and batch evaluation
- Optional FastAPI endpoints, Prometheus-style metrics, HMAC-SHA256 audit records, and input-safety checks
- Automated Python, browser, packaging, dependency-audit, and container smoke tests

### Model scope

This is a **research-use supplied-candidate scorer**. It does not search a genome, discover genomic loci, reproduce a complete published CFD implementation, model all sequence/genomic-context effects, or provide clinical decision support. Results should be independently validated before experimental use.

## Live browser application

The GitHub Pages application runs the core Python scoring engine in the browser through a pinned Pyodide runtime. Entered guide/candidate sequences are processed client-side by the application; the repository does not provide a server endpoint for the Pages workflow.

The browser interface supports:

- SpCas9 20-nt guides
- AsCas12a 23-nt guides
- One or more supplied candidate sequences
- Per-candidate mismatch, seed-mismatch, cleavage-score, and risk-tier output
- JSON result download

## Installation

```bash
git clone https://github.com/abusuraihsakhri/crispr-offtarget-cas12-cas9-agent.git
cd crispr-offtarget-cas12-cas9-agent

python -m pip install -e .
```

For the REST API:

```bash
python -m pip install -e ".[api]"
```

For development and repository checks:

```bash
python -m pip install -e ".[api,dev]"
```

### Requirements

- Python >= 3.10
- Pydantic v2
- FastAPI and Uvicorn only for the optional API server
- A modern browser with WebAssembly support for the Pages application

## Usage

### Core CRISPR engine CLI

```bash
# Evaluate a SpCas9 guide
crispr-offtarget eval --seq GACACCGTGGACAGCAACAT --nuclease SpCas9

# Evaluate an AsCas12a guide with JSON output
crispr-offtarget eval --seq ATGCGATCGATCGATCGATCGAT --nuclease AsCas12a --json

# Batch process CSV records
crispr-offtarget batch -i sample.csv -o results.csv
```

The module can also be invoked directly:

```bash
python crispr_cas12_cas9.py --help
```

### Agent/audit CLI

```bash
# Run a single audit task
crispr-agent audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch process CSV records
crispr-agent batch -i sample.csv -o results.csv

# Verify the audit log
crispr-agent verify-audit
```

### REST API server

Set a secret for signed audit records, then start the optional API:

```bash
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
crispr-agent serve --host 127.0.0.1 --port 8000
```

Main endpoints:

- `GET /health`
- `GET /metrics`
- `POST /api/audit`
- `POST /api/chat`
- `GET /api/audit/logs`

## Core modules

- `crispr_cas12_cas9.py` — main Cas9/Cas12a supplied-candidate scoring engine and CLI
- `crispr_offtarget_scan/` — secondary packaged scan workflow
- `agents/` — API, audit, metrics, supervisor, worker, and safety utilities
- `enrichment.py` — enrichment utilities
- `simulator.py` — simulation/high-throughput helper
- `index.html` and `web/` — GitHub Pages/Pyodide browser application

## Security and data handling

The repository includes input/path validation, outbound PHI-pattern guards in the agent subsystem, and HMAC-SHA256 audit-record integrity checks. These controls are implementation safeguards, not a compliance certification.

For the GitHub Pages application, sequence assessment is performed in the browser after loading Pyodide from the pinned jsDelivr URL configured in `index.html`/`web/app.js`. Do not enter sensitive information into any research tool unless its deployment environment and data-handling requirements have been independently reviewed.

## Testing and quality checks

The CI workflow currently exercises:

```bash
python -m pytest -q
ruff check .
python -m build
pip-audit
node --check web/app.js
```

It also smoke-tests:

- Python 3.10, 3.11, and 3.12
- installed CLI entry points
- the Pyodide browser workflow in Chromium
- Docker Compose configuration
- image build, API health, metrics, and audit endpoint behavior

## Docker

```bash
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
docker compose up --build
```

Or:

```bash
docker build -t crispr-offtarget-cas12-cas9-agent .
docker run --rm -p 8000:8000 \
  -e AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  crispr-offtarget-cas12-cas9-agent
```

## Project structure

```text
.
├── agents/                     # API, audit, metrics, supervisor, workers
├── crispr_offtarget_scan/      # Packaged secondary scan workflow
├── tests/                      # Unit, security/edge-case, and browser smoke tests
├── web/                        # Browser JavaScript, styles, and redirect page
├── .github/workflows/          # CI and GitHub Pages deployment
├── cli.py                      # Agent/audit CLI
├── crispr_cas12_cas9.py        # Core scoring engine and CLI
├── enrichment.py
├── simulator.py
├── index.html                  # GitHub Pages entry point
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

## Browser compatibility

The browser application depends on WebAssembly and a current JavaScript runtime. Chromium is exercised in CI. Other modern evergreen browsers are expected to work but are not currently covered by the automated browser smoke test.

## License

MIT. See [LICENSE](LICENSE).
