# Crispr Offtarget Cas12 Cas9 Agent

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

## 📖 What It Does

**Crispr Offtarget Cas12 Cas9 Agent** is an advanced analytical and computational platform implementing Cas9/Cas12a Cutting Frequency Determination (CFD) off-target scoring agent.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`MismatchDetail`**: Individual nucleotide mismatch between on-target guide and candidate off-target site.
- **`OffTargetAssessment`**: Evaluation of a single potential off-target genomic site.
- **`NucleaseComparisonResult`**: Complete comparative analysis between Cas9 and Cas12a architectures.
- **`CRISPRCas12Cas9Engine`**: Engine for comparative Cas9 vs Cas12a off-target modeling.

---

## 📐 Mathematical Formulation & Logic

```text
  Calculate SpCas9 cleavage probability based on Hsu-Zhang position weighting.
  Calculate AsCas12a cleavage probability.
  prob, mm_list = cls.calculate_spcas9_cleavage_prob(on_target_sequence, s_seq)
  prob, mm_list = cls.calculate_cas12a_cleavage_prob(on_target_sequence, s_seq)
  risk = "HIGH_RISK_CLEAVAGE"
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --task-id <value> --target <value> --primary <value> --secondary <value>
```

### Parameter Reference
- `--task-id`: Specifies input measurement or parameter value.
- `--target`: Specifies input measurement or parameter value.
- `--primary`: Specifies input measurement or parameter value.
- `--secondary`: Specifies input measurement or parameter value.
- `--critical`: Specifies input measurement or parameter value.
- `--status`: Specifies input measurement or parameter value.
- `--input`: Specifies input measurement or parameter value.
- `--output`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `task_id` | Parameter / observation metric | Required |
| `target_identifier` | Parameter / observation metric | Required |
| `primary_metric` | Parameter / observation metric | Required |
| `secondary_metric` | Parameter / observation metric | Required |
| `is_critical_flag` | Parameter / observation metric | Required |
| `status_descriptor` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t crispr-offtarget-cas12-cas9-agent .
docker run -p 8000:8000 crispr-offtarget-cas12-cas9-agent
```
