# App B — Datadog SDK (zero decoration)

The **same** Strands agent as App A, observed with Datadog's **LLM Observability
SDK** (`ddtrace`), running **agentless**, with **no manual decorators**.

Datadog [officially supports Strands Agents](https://docs.datadoghq.com/llm_observability/instrumentation/auto_instrumentation/)
(`strands-agents >= 1.11.0`, ddtrace version: *Any*). Support is **not** a
`ddtrace/contrib` patch — Strands emits OpenTelemetry GenAI spans natively, and
the SDK ingests them via ddtrace's **OpenTelemetry bridge**:

```
agent.py
  └── DD_TRACE_OTEL_ENABLED=1      # ddtrace becomes the OTel tracer provider
  └── LLMObs.enable(agentless)     # ship to Datadog LLM Obs, no Agent
  └── Strands emits native gen_ai.* spans ──► ddtrace ──► Datadog LLM Obs
```

No `@workflow` / `@tool` annotations anywhere — the full agent trace (agent
invocation, event-loop cycles, LLM calls, tool calls) is captured automatically.

## Run

```bash
aws sso login --profile ese-sandbox   # if not already logged in

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then paste your DD_API_KEY
python agent.py "What's the weather in Tokyo, and is it a good day to run?"
```

Then open [Datadog LLM Observability](https://app.datadoghq.com/llm/traces) and
search `ml_app:bedrock-agentcore-sdk` (allow 3–5 minutes).

## The bridge is what matters

| `DD_TRACE_OTEL_ENABLED` | What the SDK captures (zero decoration) |
|-------------------------|-----------------------------------------|
| `0` (off) | Only the auto-instrumented **Bedrock** calls (the `llm` spans). Strands' agent/tool/event-loop spans are missing. |
| `1` (on, default here) | ddtrace ingests Strands' **native OTel** spans → full trace: `agent` + `execute_event_loop_cycle` + `llm` + `tool`. |

This is the key insight: because there's no Strands `ddtrace` contrib patch, the
SDK relies on the OTel bridge to relay Strands' own instrumentation. With the
bridge on, App B reaches parity with App A — same spans, different transport
(Datadog SDK vs raw OTLP exporter).

## Contrast with App A

- **App A**: Strands native OTel → **OTLP exporter** → Datadog OTLP intake.
- **App B**: Strands native OTel → **ddtrace OTel bridge** → Datadog LLM Obs.

Same source spans; the difference is who ships them.

## Deploying to AgentCore Runtime (optional)

`agent.py` defines an `@app.entrypoint` handler. On AgentCore Runtime, set
`DISABLE_ADOT_OBSERVABILITY=true` and provide the `DD_*` env vars (including
`DD_TRACE_OTEL_ENABLED=1`) as runtime configuration; launch with `ddtrace-run`.
