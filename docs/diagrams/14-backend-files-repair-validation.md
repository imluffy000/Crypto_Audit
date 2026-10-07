# Backend files (2/3): repair, language model and validation

Every file in `repair/`, `llm/` and `validation/`, plus the versioned prompts in `backend/prompts/`.

Generation (`repair/`, `llm/`) and judgement (`validation/`) are separate packages. Generation-side
packages may not import `validation`; an import-boundary test enforces it.

| Package | Responsibility |
|---|---|
| `repair/` | Build the `RepairRequest`, run S1–S4, apply edits, render prompts and parse model output |
| `llm/` | Model backends (Ollama, OpenRouter), routing between them, token budgeting, prompt loading |
| `prompts/` | Versioned prompt files: `repair/s3_v1.yaml`, `repair/s4_v1.yaml`, `explanation/explain_v1.yaml` |
| `validation/` | Integrity checks, V0–V3 gates, the verdict, hidden-test access, sandbox and scanner wrappers |

See [07 repair strategies](07-repair-strategies.md), [08 LLM routing](08-llm-routing.md),
[09 validation](09-validation-and-verdict.md) and [11 sandbox](11-sandbox-execution.md) for how
these files work together.

## Diagram

```mermaid
flowchart LR
    subgraph REPAIR["repair/ — untrusted candidate generation"]
        direction TB
        rp_base["base.py<br/>RepairStrategy interface (repair → RepairResult)"]
        rp_reg["registry.py<br/>StrategyId → strategy"]
        rp_req["request.py<br/>build_repair_request: public input only"]
        rp_edits["edits.py<br/>position-based edits that keep formatting,<br/>innermost-call lookup, ensure_import"]
        rp_s1["s1_hint.py<br/>S1: apply scanner's machine-applicable fix"]
        rp_s2["s2_template.py<br/>S2: per-rule AST templates (CR1, CR3, CR4, CR5)"]
        rp_s3["s3_llm.py<br/>S3: single-shot LLM repair, budget-checked"]
        rp_s4["s4_migration.py<br/>S4: S3 + migration guidance"]
        rp_prompt["prompt_builder.py<br/>render versioned prompt from a RepairRequest"]
        rp_parser["parser.py<br/>strict: exactly one python code block"]
        rp_s2 --> rp_edits
        rp_s4 --> rp_s3
        rp_s3 --> rp_prompt & rp_parser
        rp_s1 & rp_s2 & rp_s3 -.-> rp_base
        rp_reg --> rp_s1 & rp_s2 & rp_s3 & rp_s4
    end

    subgraph LLM["llm/ — generation backends"]
        direction TB
        l_client["client.py<br/>LLMClient protocol"]
        l_schemas["schemas.py<br/>LLMRequest, LLMResponse"]
        l_ollama["ollama_client.py<br/>local Ollama /api/generate, /api/tags"]
        l_or["openrouter_client.py<br/>OpenRouter chat completions, clear errors (401/402/429)"]
        l_router["router.py<br/>RoutingLLMClient: first available backend"]
        l_budget["budget.py<br/>token estimate, fits / num_predict"]
        l_prompts["prompt_loader.py<br/>load prompts/&lt;category&gt;/&lt;id&gt;.yaml"]
        l_router --> l_ollama & l_or
        l_ollama & l_or -.-> l_client
    end

    subgraph PROMPTS["backend/prompts/"]
        direction TB
        p_s3["repair/s3_v1.yaml"]
        p_s4["repair/s4_v1.yaml"]
        p_ex["explanation/explain_v1.yaml"]
    end

    subgraph VALID["validation/ — the authority on correctness"]
        direction TB
        v_integ["integrity.py<br/>syntax, import allow-list, denied calls, size"]
        v_runner["runner.py<br/>ValidationPipeline: run V0–V3"]
        v0["v0_scanner.py<br/>V0 re-scan (evidence only)"]
        v1["v1_functional.py<br/>V1 syntax, interface, functional checks"]
        v2["v2_security.py<br/>V2 executable security properties"]
        v3["v3_compatibility.py<br/>V3 legacy artifacts still usable"]
        v_gates["gates.py<br/>decide(): verdict + reasons, build_outcome()"]
        v_oracle["oracle.py<br/>HiddenOracle: the only reader of expected/ + artifacts/"]
        v_checks["checks.py<br/>run hidden check files in the sandbox"]
        subgraph SANDBOX["sandbox/"]
            v_sbx_r["runners.py<br/>Docker / local runner, nonce, timeout"]
            v_sbx_h["harness.py<br/>runs check_* inside the sandbox"]
        end
        subgraph SCANNERS["scanners/"]
            v_bandit["bandit.py<br/>Bandit wrapper"]
            v_semgrep["semgrep.py<br/>Semgrep wrapper"]
            v_proc["process.py<br/>run a tool on a temporary copy"]
        end
        v_runner --> v0 & v1 & v2 & v3
        v1 & v2 & v3 --> v_checks --> v_sbx_r --> v_sbx_h
        v0 --> v_bandit & v_semgrep --> v_proc
        v3 --> v_oracle
    end

    rp_s3 --> l_router
    rp_s3 --> l_budget
    rp_prompt --> l_prompts
    l_prompts --> p_s3 & p_s4 & p_ex
    rp_s1 --> v_bandit
    rp_req -. "produces" .-> rp_base
    v1 -. "public interface" .-> sym["context/symbol_resolver.py"]
```
