# App B — Datadog SDK (zero decorators)

The **same** Strands agent as App A, observed with Datadog's **LLM Observability
SDK** (`ddtrace`), running **agentless**, with **no observability decorators**
(only Strands' functional `@tool`, same as App A).

```
agent.py
  └── LLMObs.enable(agentless)     # ship to Datadog Agent Observability, no Agent
  └── ddtrace auto-instruments the Amazon Bedrock calls ──► Agent Observability
```

## Run

```bash
aws sso login --profile ese-sandbox   # if not already logged in

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then paste your DD_API_KEY
python agent.py "What's the weather in Tokyo, and is it a good day to run?"
```

Then open [Datadog Agent Observability](https://app.datadoghq.com/llm/traces) and
search `ml_app:bedrock-agentcore-sdk` (allow 3–5 minutes).

## What you get (and what you don't)

With zero decorators, the Datadog SDK captures what it **auto-instruments**: the
underlying **Amazon Bedrock** model calls (the `llm` spans, service
`aws.bedrock-runtime`).

It does **not** capture Strands' agent-orchestration spans (`invoke_agent`,
event-loop cycles, tool execution). That's because `ddtrace` has no Strands
`contrib` integration — Datadog's [official Strands support](https://docs.datadoghq.com/llm_observability/instrumentation/auto_instrumentation/)
is delivered through Strands' **native OpenTelemetry** emission, i.e. the OTLP
path used by **App A**.

## Contrast with App A

| | App A — OTEL SDK | App B — DD SDK |
|---|---|---|
| Instrumentation | Strands native OpenTelemetry | `ddtrace` auto-instrumentation |
| Transport | OTLP exporter → Datadog `/v1/traces` | Datadog SDK (agentless) |
| Zero-decoration result | Full agent tree (`agent` + event-loop + `llm` + `tool`) | Bedrock `llm` spans only |

Takeaway: for a Strands agent, the **OTEL SDK path (App A)** is what surfaces the
full agent trace in Agent Observability with zero decoration.

## Deploying to AgentCore Runtime (optional)

`agent.py` defines an `@app.entrypoint` handler. On AgentCore Runtime, set
`DISABLE_ADOT_OBSERVABILITY=true` and provide the `DD_*` env vars as runtime
configuration; launch with `ddtrace-run`.
