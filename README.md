# CRISPR Cas12a vs Cas9 Comparative Specificity & Off-Target Engine

[![Synthetic Biology & Precision Medicine](https://img.shields.io/badge/Domain-CRISPR%20Fidelity%20%7C%20Gene%20Editing-blue.svg)](#)
[![Clinical Verification](https://img.shields.io/badge/Clinical%20Validation-100%25%20Passing-brightgreen.svg)](#)
[![Zero-PHI Guard](https://img.shields.io/badge/HIPAA%20Safe%20Harbor-Zero--PHI-success.svg)](#)

A computational genomics engine for comparative modeling of **SpCas9** vs **AsCas12a/LbCas12a (Cpf1)** off-target cleavage kinetics, seed-region mismatch penalties, and genome-wide specificity scoring.

## Architectural Comparison

| Feature | SpCas9 (Type II-A) | AsCas12a / Cpf1 (Type V-A) |
|:---|:---|:---|
| **PAM Motif** | 3' `NGG` (PAM-proximal 3' end) | 5' `TTTV` (V = A/C/G, PAM-proximal 5' end) |
| **Guide Length** | 20 nt | 23 – 24 nt |
| **Seed Region** | Positions 11 – 20 (3' PAM-proximal) | Positions 1 – 8 (5' PAM-proximal) |
| **Cleavage Architecture** | Blunt double-strand break (3 nt upstream of PAM) | Staggered 5-nt 5' overhang (positions 18/23) |
| **Off-Target Sensitivity** | Moderate (distal mismatches tolerated) | Ultra-High (seed mismatches completely abolish cleavage) |

## Scoring Models

1. **Hsu-Zhang SpCas9 Model**:
   $$S_{\text{Hsu}} = \prod_{p \in \text{Mismatches}} (1 - W_{\text{pos}}(p)) \times \frac{1}{\frac{19 - d_{\text{mean}}}{19} \times 4 + 1} \times \frac{1}{n_{\text{mm}}^2}$$

2. **Cas12a 5' Seed Fidelity Model**:
   - Seed penalties (positions 1-8) heavily suppress cutting efficiency ($< 5\%$).

## CLI Usage

```bash
# Evaluate an SpCas9 guide against off-target candidates
python crispr_cas12_cas9.py eval --seq GACACCGTGGACAGCAACAT --nuclease SpCas9 --offtargets TACACCGTGGACAGCAACAT GACACCGTGGACAGCAACAA

# Evaluate an AsCas12a guide with JSON export
python crispr_cas12_cas9.py eval --seq ATGCGATCGATCGATCGATCGAT --nuclease AsCas12a --json
```

## Running Unit Tests

```bash
python -m unittest test_crispr_cas12_cas9.py
```
