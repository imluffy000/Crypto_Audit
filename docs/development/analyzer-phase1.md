# CryptoAudit Phase 1 Implementation Documentation

> Historical record of the Phase 1 analyzer. Module paths have since moved (`analyzer/` → `analysis/` + `rules/`, `core/` → `models/`, `config/`, `utils/`); see [../architecture/system-design.md](../architecture/system-design.md).

## Overview

CryptoAudit is a Python-focused cryptographic misuse analysis framework. Phase 1 provides the foundational project structure, core domain models, Python AST parser, import and call analyzers, context evaluator, and the CR1 rule detector vertical slice.

## Architecture & Pipeline

The CryptoAudit static analyzer operates as a deterministic pipeline without using LLMs or external baseline scanners (Bandit/Semgrep):

```
Source File (.py)
    │
    ▼
AST Parser (ast_parser.py) ──► Parses Python code into AST & tracks line text
    │
    ▼
Import Analyzer (imports.py) ──► Tracks module imports & aliasing (e.g. hashlib as hl)
    │
    ▼
Call Analyzer (calls.py) ──► Extracts target function calls, args, line/col numbers
    │
    ▼
Context Analyzer (context.py) ──► Evaluates credential context (variable/func/arg names)
    │
    ▼
CR1 Rule (rules/cr1.py) ──► Applies rule configuration from YAML & generates Findings
    │
    ▼
Report Formatter / CLI (reporting/ & cli/) ──► Outputs formatted findings (console/JSON)
```

## CR1 Rule Definition

**Rule ID**: `CR1`  
**Category**: `WEAK_HASH_CREDENTIALS`  
**Severity**: `HIGH`  

### Detection Criteria
- Matches direct calls to `hashlib.md5(...)` or `hashlib.sha1(...)` (including aliased imports such as `import hashlib as hl` -> `hl.md5()` or `from hashlib import md5` -> `md5()`).
- Evaluates contextual indicators (variable names, argument identifiers, enclosing function names) for password or credential handling (e.g., `password`, `passwd`, `pwd`, `secret`, `credential`, `user_pass`, `hash_password`).
- Preserves context to avoid false positives on non-credential operations (e.g. `checksum = hashlib.md5(file_bytes)`).

## Domain Models

Implemented using Pydantic v2 (`pydantic.BaseModel`):
- `Location`: Source file, line, and column range.
- `Finding`: Structured representation of a misuse finding (rule_id, category, severity, location, matched_api, evidence, explanation, remediation, analyzer_version, rule_version).
- `AnalysisResult`: Aggregated findings, summary counts, execution metadata, and determinism metrics.

## CLI Usage

```bash
# Human-readable output
cryptoaudit analyze <path-to-python-file>

# Structured JSON output
cryptoaudit analyze <path-to-python-file> --json
```
