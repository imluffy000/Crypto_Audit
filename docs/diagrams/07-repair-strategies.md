# Repair strategies S1–S4

Every strategy receives the same frozen `RepairRequest` (`repair/request.py`): the module source,
its findings, a bounded code context and the repair constraints. It is built from public input only
and forbids extra fields, so hidden test data cannot reach generation.

## The four strategies

| Strategy | File | How it repairs |
|---|---|---|
| **S1** scanner hint | `s1_hint.py` | Applies a scanner's own machine-applicable fix (e.g. Bandit B324 → `usedforsecurity=False`) when it sits on a finding's line |
| **S2** template | `s2_template.py` | Deterministic, per-rule AST edits that keep formatting and comments |
| **S3** LLM | `s3_llm.py` | Single-shot prompt (`prompts/repair/s3_v1.yaml`), temperature 0, fixed seed, strict parser |
| **S4** migration-aware LLM | `s4_migration.py` | S3 plus guidance to keep legacy data readable (`s4_v1.yaml`) |

## S2 templates per rule

| Rule | Template |
|---|---|
| CR1 | `hashlib.X(pw).hexdigest()` → `hashlib.pbkdf2_hmac("sha256", pw, os.urandom(16), 600000).hex()` |
| CR2 | none: moving from ECB to an authenticated mode changes the ciphertext format → `NO_REPAIR` |
| CR3 | static IV/nonce → `os.urandom(16)` (12 bytes for GCM) |
| CR4 | static salt → `os.urandom(16)`; low iterations → 600000; fast-hash KDF → PBKDF2 |
| CR5 | `random.choice` → `secrets.choice`; `randint`/`randrange` → `secrets.randbelow`; other methods → `secrets.SystemRandom()` |

## Statuses

| Status | Meaning | Becomes |
|---|---|---|
| `PRODUCED` | candidate code exists | validated |
| `NO_REPAIR` | no repair available, or the file does not fit the model's context window (`LIMIT_EXCEEDED`) | `NO_CANDIDATE` |
| `NOT_APPLICABLE` | the strategy does not apply (e.g. no scanner hint for S1) | `NO_CANDIDATE` |
| `PARSE_ERROR` | the model did not return exactly one code block | `NO_CANDIDATE` |

`NO_CANDIDATE` is never counted as success. Strategies are single-shot: validation results are
never fed back into generation. Website scans always run S1 and S2; S3 and S4 run only when a
language model is available, otherwise the scan page lists them as skipped with the reason.

## Diagram

```mermaid
flowchart TD
    req[/"RepairRequest<br/>source · findings · CodeContext · constraints"/] --> s1 & s2 & llmgate

    subgraph S1["S1 — scanner hint (s1_hint.py)"]
        s1["run Bandit / Semgrep on the source"] --> s1q{"machine-applicable fix<br/>on a finding's line?<br/>(e.g. Bandit B324)"}
        s1q -- yes --> s1e["apply the scanner's own fix<br/>e.g. usedforsecurity=False"]
        s1q -- no --> s1na["NOT_APPLICABLE"]
    end

    subgraph S2["S2 — deterministic templates (s2_template.py + edits.py)"]
        s2["per finding: rule template"] --> s2r{"rule"}
        s2r -- CR1 --> t1["hashlib.X(pw).hexdigest()<br/>→ pbkdf2_hmac('sha256', pw, os.urandom(16), 600000).hex()"]
        s2r -- CR2 --> t2["no template: ECB → authenticated mode<br/>changes the ciphertext format → NO_REPAIR"]
        s2r -- CR3 --> t3["static IV / nonce → os.urandom(16)<br/>(12 bytes for GCM)"]
        s2r -- CR4 --> t4["static salt → os.urandom(16)<br/>low iterations → 600000<br/>fast-hash KDF → PBKDF2"]
        s2r -- CR5 --> t5["random.choice → secrets.choice<br/>randint / randrange → secrets.randbelow<br/>random() etc. → secrets.SystemRandom()"]
        t1 & t3 & t4 & t5 --> s2e["position-based text edits<br/>(keep formatting + comments)<br/>+ ensure imports"]
    end

    llmgate{"LLM backend available?"}
    llmgate -- no --> skipped["S3/S4 skipped<br/>(reason shown on the scan page)"]
    llmgate -- yes --> s3 & s4

    subgraph S3S4["S3 / S4 — LLM (s3_llm.py, s4_migration.py)"]
        s3["S3 prompt prompts/repair/s3_v1.yaml"]
        s4["S4 prompt prompts/repair/s4_v1.yaml<br/>+ migration guidance: keep legacy reads,<br/>self-describing new format"]
        s3 & s4 --> budget{"prompt + full repaired file<br/>fit the context window?"}
        budget -- no --> lim["NO_REPAIR (LIMIT_EXCEEDED)<br/>never truncated"]
        budget -- yes --> gen["generate: temperature 0, fixed seed"]
        gen --> parse{"parser.py: exactly one<br/>python code block?"}
        parse -- no --> pe["PARSE_ERROR"]
        parse -- yes --> s3e["candidate code<br/>+ provider, model, prompt id/hash, raw output"]
    end

    s1e & s2e & s3e --> cand[("Candidate (PRODUCED)<br/>code · diff · repaired / unrepaired finding ids")]
    s1na & t2 & lim & pe --> none[("NO_CANDIDATE")]
    cand --> integ["validation/integrity.py → V0–V3"]

    classDef ok fill:#e7f4ed,stroke:#17784a,color:#0b3320
    classDef no fill:#eef0f3,stroke:#8a96a8,color:#1b2430
    class cand ok
    class none,s1na,t2,lim,pe,skipped no
```
