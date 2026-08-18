# App B — Datadog SDK

The **same** Strands agent as App A, but instrumented with Datadog's **LLM
Observability SDK** (`ddtrace`) instead of raw OpenTelemetry. Running
**agentless**, it ships spans directly to Datadog — no Datadog Agent required.

```
agent.py
  └── LLMObs.enable(ml_app=..., agentless_enabled=True)
  └── ddtrace Bedrock integration auto-captures the model calls  ─► Datadog LLM Obs
  └── @workflow / @tool decorators add the agent + tool spans
```

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

## How telemetry is configured

| Setting | Value | Purpose |
|---------|-------|---------|
| `LLMObs.enable(...)` | in `agent.py` | turns on LLM Observability + integrations |
| `DD_API_KEY` / `DD_SITE` | from `.env` | auth + region (US1) |
| `DD_LLMOBS_ML_APP` | `bedrock-agentcore-sdk` | groups traces in the UI |
| `DD_LLMOBS_AGENTLESS_ENABLED` | `1` | send directly to Datadog, no Agent |

The Bedrock model calls are captured automatically by ddtrace's Bedrock
integration; `@workflow` wraps the whole agent run and `@tool` marks the
`get_weather` call, so the trace shape matches App A.

## Contrast with App A

- **App A** produces vendor-neutral OTel `gen_ai.*` spans and Datadog maps them.
- **App B** uses Datadog-native span kinds (`workflow`, `tool`, `llm`) directly.

Same agent, same reason → tool → reason loop — two instrumentation strategies.

## Deploying to AgentCore Runtime (optional)

`agent.py` defines an `@app.entrypoint` handler. On AgentCore Runtime, set
`DISABLE_ADOT_OBSERVABILITY=true` (so the built-in CloudWatch pipeline is off)
and provide the `DD_*` env vars as runtime configuration; launch with
`ddtrace-run`.
