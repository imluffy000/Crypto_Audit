# Integrity checks, validation gates and the verdict

Validation is the authority on whether a repair is acceptable (`validation/`). It runs every gate
independently of anything the strategy claims.

## 1. Integrity (before anything could execute the candidate)

`integrity.py` rejects a candidate that:

- does not parse,
- imports modules outside the allow-list (the case's allowed libraries, or for user code the
  crypto standard library `hashlib`, `hmac`, `secrets`, `os`, `base64`, `binascii`, plus modules the
  original file already imported),
- touches denied surfaces: `subprocess`, `socket`, `ctypes`, `pickle`, `urllib`, `requests`,
  `importlib`, `eval`/`exec`/`compile`/`__import__`, `os.system`/`popen`/`exec*`/`spawn*`/file
  deletion, or `open()` for writing,
- is larger than 100 000 characters.

## 2. Gates

| Gate | File | Checks | Decides the verdict? |
|---|---|---|---|
| **V0** | `v0_scanner.py` | CryptoAudit, Bandit and Semgrep re-scan | No, evidence only |
| **V1** | `v1_functional.py` | Syntax, public interface preserved, functional checks | Yes |
| **V2** | `v2_security.py` | Security properties in the sandbox: salted slow KDF, no ECB / authenticated encryption, unique IVs, CSPRNG | Yes |
| **V3** | `v3_compatibility.py` | Data written by the original code still works (CR1–CR4; not applicable to CR5) | Where the case says so |

## 3. Verdict (`gates.py: decide()`)

| Verdict | When |
|---|---|
| **NO_CANDIDATE** | The strategy produced no code |
| **FAILED** | Integrity failed, or a gating gate failed |
| **UNVERIFIED** | No gating failure, but a gating gate is `NOT_RUN` or `ERROR`, or V1/V2 are missing |
| **VERIFIED** | V1 and V2 pass, and V3 passes where it is gating |

`NOT_APPLICABLE`, `NOT_RUN` and `ERROR` are never treated as a pass. V0 only adds reasons such as
"scanners report the candidate clean, but validation did not verify it". Website scans have no
hidden tests, so V2/V3 are `NOT_RUN` and **Unverified is the best possible verdict** there.

## Diagram

```mermaid
flowchart TD
    cand[/"Candidate"/] --> produced{"repair status<br/>PRODUCED?"}
    produced -- no --> NC(["NO_CANDIDATE"])
    produced -- yes --> integ

    subgraph INT["integrity.py — before anything could execute it"]
        integ["parse candidate"] --> i1{"syntax OK?"}
        i1 -- yes --> i2{"imports allowed?<br/>case allow-list or crypto stdlib<br/>(hashlib, hmac, secrets, os, base64, binascii)<br/>+ modules the original already used"}
        i2 -- yes --> i3{"no denied surfaces?<br/>subprocess, socket, ctypes, pickle, urllib, requests,<br/>importlib, eval/exec/compile/__import__,<br/>os.system/popen/exec*/spawn*/remove…, open() for write"}
        i3 -- yes --> i4{"size ≤ 100 000 chars?"}
    end
    i1 -- no --> FAIL
    i2 -- no --> FAIL
    i3 -- no --> FAIL
    i4 -- no --> FAIL
    i4 -- yes --> gates

    subgraph GATES["runner.py — gates"]
        gates["run V0–V3"] --> v0["V0 v0_scanner.py<br/>CryptoAudit + Bandit + Semgrep re-scan<br/>evidence only"]
        gates --> v1["V1 v1_functional.py<br/>syntax · public interface preserved<br/>· hidden functional checks (sandbox)"]
        gates --> v2["V2 v2_security.py<br/>security properties in the sandbox:<br/>salted slow KDF, no ECB / authenticated,<br/>unique IVs, CSPRNG"]
        gates --> v3["V3 v3_compatibility.py<br/>legacy artifacts still usable<br/>(CR1–CR4; NOT_APPLICABLE for CR5)"]
    end

    v1 & v2 & v3 --> decide{"gates.py decide()"}
    v0 -. "never decides" .-> note["reasons only:<br/>'scanners say clean but not verified'<br/>'verified but still flagged by a scanner'"]
    decide -- "a gating gate FAILED" --> FAIL(["FAILED"])
    decide -- "V1 or V2 not gating / missing" --> UNV(["UNVERIFIED"])
    decide -- "a gating gate NOT_RUN or ERROR" --> UNV
    decide -- "all gating gates PASS" --> VER(["VERIFIED"])

    FAIL & UNV & VER & NC --> outcome[("CaseOutcome<br/>verdict · reasons · gates · scanner_results")]
    outcome --> why["reporting/explanation.py<br/>headline · limitations · sections"]

    classDef ok fill:#e7f4ed,stroke:#17784a,color:#0b3320
    classDef warn fill:#fdf1e3,stroke:#c98a1b,color:#3a2a05
    classDef bad fill:#fbe9e6,stroke:#bf3120,color:#4a120b
    classDef none fill:#eef0f3,stroke:#8a96a8,color:#1b2430
    class VER ok
    class UNV warn
    class FAIL bad
    class NC none
```
