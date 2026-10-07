# Language model routing and context budgeting

The language model only writes S3/S4 candidates and the optional plain-language summary. It never
detects misuse and never decides a verdict (`llm/`).

## Choosing a backend

| `CRYPTOAUDIT_LLM_PROVIDER` | Backends tried | Notes |
|---|---|---|
| `ollama` | Ollama | Code never leaves the machine |
| `openrouter` | OpenRouter | Code is sent to OpenRouter and the model provider |
| `auto` (default) | Ollama, then OpenRouter | OpenRouter is added only when a non-blank API key is set |

`RoutingLLMClient` uses the first backend that reports itself available (cached for 30 seconds).
The backend and model that actually answered are recorded on every result
(`generation.provider`, `generation.model`).

## Context budget

The answer must contain the **whole repaired file**, so before calling the model
`llm/budget.py` estimates:

- prompt tokens ≈ characters ÷ 3
- answer tokens ≈ original file tokens × 1.3 + 256

If prompt + answer exceed the context window (Ollama: `CRYPTOAUDIT_LLM_NUM_CTX`, default 8192;
OpenRouter: 32768), the file is recorded as `NO_REPAIR` (`LIMIT_EXCEEDED`). Prompts are never
silently truncated.

## Calls

| Backend | Endpoint | Sent |
|---|---|---|
| Ollama | `POST /api/generate` | prompt, `num_ctx`, `num_predict`, seed, temperature 0 |
| OpenRouter | `POST /api/v1/chat/completions` | system + user messages, seed, temperature 0, max tokens |

## Diagram

```mermaid
flowchart TD
    call(["S3 / S4 / AI summary needs a completion"]) --> factory["pipeline/factory.py: build_llm(settings)"]
    factory --> prov{"LLM_PROVIDER"}
    prov -- ollama --> b1["backends = [Ollama]"]
    prov -- openrouter --> b2["backends = [OpenRouter]"]
    prov -- auto --> key{"OPENROUTER_API_KEY<br/>set and not blank?"}
    key -- no --> b1
    key -- yes --> b3["backends = [Ollama, OpenRouter]"]

    b1 & b2 & b3 --> router["router.py — RoutingLLMClient<br/>active = first backend whose is_available() is true"]
    router --> avail{"any backend available?"}
    avail -- no --> unavailable["unavailable_reason()<br/>scan: S3/S4 skipped · AI button disabled"]
    avail -- yes --> win["context window<br/>Ollama: LLM_NUM_CTX (8192)<br/>OpenRouter: 32768"]
    win --> fits{"budget.module_budget<br/>prompt + answer ≤ window?"}
    fits -- no --> nr["NO_REPAIR (LIMIT_EXCEEDED)"]
    fits -- yes --> which{"active backend"}
    which -- Ollama --> ol["ollama_client.py<br/>POST /api/generate<br/>num_ctx + num_predict, seed, temperature 0"]
    which -- OpenRouter --> orc["openrouter_client.py<br/>POST /api/v1/chat/completions<br/>system + user messages, seed, temperature 0"]
    ol & orc --> resp[("LLMResponse<br/>text · provider · model")]
    resp --> parser["repair/parser.py (S3/S4)<br/>or reporting/ai_explanation.py"]

    prompts[("prompts/<br/>repair/s3_v1.yaml · repair/s4_v1.yaml<br/>explanation/explain_v1.yaml")] -.-> router

    classDef warn fill:#fdf1e3,stroke:#c98a1b,color:#3a2a05
    class unavailable,nr warn
```
