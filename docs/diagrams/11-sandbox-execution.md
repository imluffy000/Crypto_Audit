# Sandboxed execution of V1–V3 checks

Only **benchmark** candidates are ever executed, and only after their integrity checks pass.
Website scans of your repositories never reach this step.

## The sandbox

`validation/sandbox/runners.py` copies the candidate, the hidden check file and the artifacts into a
temporary work directory and runs the harness in the `cryptoaudit-sandbox` Docker image with:

- `--network none` (no network)
- `--read-only` plus a small `/tmp` tmpfs
- memory, CPU and process-count limits
- `--cap-drop ALL` and `no-new-privileges`
- user `65534:65534` (nobody)
- a timeout

The local (non-Docker) runner exists for trusted code only and needs an explicit opt-in.

## Result protocol

The harness reads and removes a per-run **nonce** from its environment before importing the
candidate, runs every `check_*` function, and prints one line:
`CRYPTOAUDIT_RESULT:<nonce>:{json}`. Ordinary output cannot be mistaken for a result.

A missing or unparseable result line, a broken check file, a timeout or an unavailable sandbox is
recorded as `ERROR` (the validator could not evaluate), **never** as `PASS`.

## Diagram

```mermaid
sequenceDiagram
    autonumber
    participant V as V1/V2/V3 validator
    participant C as checks.py
    participant R as sandbox/runners.py
    participant D as Docker container
    participant H as harness.py (inside)

    V->>C: run(candidate, hidden check file, artifacts)
    C->>R: execute(work dir, argv, nonce)
    R->>R: temp work dir: candidate.py, checks.py, artifacts/ copy
    R->>D: docker run --rm --network none --read-only --tmpfs /tmp<br/>--memory --cpus --pids-limit --cap-drop ALL<br/>--security-opt no-new-privileges --user 65534:65534
    D->>H: harness.py --candidate --checks --artifacts<br/>(nonce in CRYPTOAUDIT_RESULT_NONCE)
    H->>H: read and remove the nonce before importing the candidate
    loop each check_*(ctx) in the hidden check file
        H->>H: import candidate, run check
        H->>H: PASS / FAIL + message + duration
    end
    H-->>D: stdout: CRYPTOAUDIT_RESULT:nonce:{json}
    D-->>R: exit code + stdout (timeout enforced)
    R-->>C: raw output
    alt nonce-tagged line found and valid JSON
        C-->>V: CheckResult list
        V-->>V: GateResult PASS / FAIL
    else missing line, bad JSON, timeout, no Docker
        C-->>V: error
        V-->>V: GateResult ERROR (never PASS)
    end
```
