# CRISPR Offtarget Cas12 Cas9 Agent

> **Domain:** Computational Biology & AI Drug Discovery
> **Reference Guidelines & Standards:** `wwPDB, IUPAC & CLSI Computational Guidelines`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## Overview

CRISPR Offtarget Cas12 Cas9 Agent is an advanced analytical and computational platform implementing Cas9/Cas12a Cutting Frequency Determination (CFD) off-target scoring. The system provides:

- **Comparative off-target analysis** between SpCas9 and AsCas12a nucleases
- **Position-dependent mismatch cleavage penalties** using Hsu-Zhang and CFD models
- **Aggregate specificity scoring** (0-100) with genomic fidelity tier classification
- **Enterprise-grade security** with Zero-PHI outbound interception and HMAC-SHA256 audit trails

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/crispr-offtarget-cas12-cas9-agent.git
cd crispr-offtarget-cas12-cas9-agent

# Install dependencies
pip install -e .

# For development (includes testing dependencies)
pip install -e ".[dev]"
```

### Requirements
- Python >= 3.9
- FastAPI & uvicorn (for REST API server)
- Pydantic v2

---

## Usage

### Core CRISPR Engine CLI

Evaluate guide sequences against off-target candidates:

```bash
# Evaluate a SpCas9 guide
python crispr_cas12_cas9.py eval --seq GACACCGTGGACAGCAACAT --nuclease SpCas9

# Evaluate an AsCas12a guide with JSON output
python crispr_cas12_cas9.py eval --seq ATGCGATCGATCGATCGATCGAT --nuclease AsCas12a --json

# Batch process CSV records
python crispr_cas12_cas9.py batch -i sample.csv -o results.csv

# Interactive chat about Cas9 vs Cas12a
python crispr_cas12_cas9.py chat "What is the difference between Cas9 and Cas12a?"
```

### Enterprise Agent CLI

Run the multi-agent supervisor system:

```bash
# Run single task evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch process CSV records
python cli.py batch -i sample.csv -o results.csv

# Verify HMAC audit trail integrity
python cli.py verify-audit

# Launch FastAPI REST server
python cli.py serve --host 127.0.0.1 --port 8000
```

### REST API Server

```bash
# Start the API server
python cli.py serve

# Or using Docker
docker-compose up --build
```

API Endpoints:
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `POST /api/audit` - Submit task for evaluation
- `POST /api/chat` - Query the supervisory chat
- `GET /api/audit/logs` - Retrieve audit trail

---

## Core Algorithmic Modules

### CRISPRCas12Cas9Engine
The main engine for comparative Cas9 vs Cas12a off-target modeling:

- **`calculate_spcas9_cleavage_prob()`**: SpCas9 cleavage probability using Hsu-Zhang position weighting
- **`calculate_cas12a_cleavage_prob()`**: AsCas12a cleavage probability with 5' seed modeling
- **`evaluate_guide()`**: Complete guide specificity evaluation across off-target candidates

### Data Models
- **`MismatchDetail`**: Individual nucleotide mismatch between guide and off-target
- **`OffTargetAssessment`**: Evaluation of a single potential off-target site
- **`NucleaseComparisonResult`**: Complete comparative analysis between Cas9 and Cas12a

---

## Security Features

### Zero-PHI Outbound Interceptor
Active regex inspection blocking:
- Medical Record Numbers (MRN)
- Social Security Numbers
- Phone numbers and email addresses
- Patient names and dates of birth
- Credit card numbers

### HMAC-SHA256 Audit Trail
- Cryptographically chained, tamper-evident logs
- Every evaluation and state transition is signed
- Integrity verification via `verify-audit` command

### Path Traversal Protection
- All file path inputs are validated to prevent directory traversal attacks
- Paths containing `..` segments are rejected

---

## Testing

```bash
# Run the full test suite
python -m pytest -v

# Run with coverage
python -m pytest -v --cov=. --cov-report=term-missing
```

The test suite includes:
- SpCas9 and Cas12a cleavage probability modeling tests
- Seed mismatch sensitivity validation
- Specificity score aggregation tests
- CLI command integration tests
- PHI guard enforcement tests
- HMAC audit trail integrity tests
- Path traversal protection tests

---

## Docker Deployment

```bash
# Build and run with Docker Compose
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
docker-compose up --build

# Or build and run manually
docker build -t crispr-offtarget-cas12-cas9-agent .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") crispr-offtarget-cas12-cas9-agent
```

---

## Project Structure

```
crispr-offtarget-cas12-cas9-agent/
├── agents/                     # Enterprise agent system
│   ├── __init__.py
│   ├── api.py                  # FastAPI REST endpoints
│   ├── base.py                 # Security, PHI guard, audit trail
│   ├── learning.py             # Bayesian calibration engine
│   ├── llm_factory.py          # LLM client factory
│   ├── metrics.py              # Prometheus metrics
│   ├── models.py               # Pydantic data models
│   ├── streamer.py             # WebSocket telemetry
│   ├── supervisor.py           # Multi-agent supervisor
│   └── workers.py              # Specialized worker agents
├── crispr_offtarget_scan/      # CRISPR-Scan Pro module
│   ├── __init__.py
│   ├── agents.py               # Sub-agent coordination
│   ├── cli.py                  # CLI interface
│   ├── engine.py               # Domain engine
│   ├── models.py               # Data models
│   └── server.py               # FastAPI server factory
├── tests/                      # Test suite
│   ├── test_crispr_offtarget_cas12_cas9_agent.py
│   ├── test_crispr_offtarget_scan.py
│   └── test_enrichment.py
├── web/                        # Web operations console
│   └── index.html
├── cli.py                      # Main CLI entry point
├── crispr_cas12_cas9.py        # Core CRISPR engine
├── enrichment.py               # Enrichment feature suite
├── simulator.py                # High-throughput simulator
├── pyproject.toml              # Project configuration
├── Dockerfile                  # Docker build config
└── docker-compose.yml          # Docker Compose config
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
