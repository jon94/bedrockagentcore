# App A — OTEL SDK / OTLP-native → Datadog

The agent emits **OpenTelemetry GenAI spans** (Strands' built-in telemetry) and
exports them **directly to Datadog's OTLP intake**. No Datadog Agent, no Datadog
SDK, and **no observability decorators** (only Strands' functional `@tool`). This
is the same OTLP mechanism AgentCore's built-in observability uses — here we just
point it at Datadog instead of CloudWatch.

```
agent.py
  └── sets OTEL_EXPORTER_OTLP_TRACES_* env vars (endpoint + dd-api-key header)
  └── StrandsTelemetry().setup_otlp_exporter()
  └── Strands emits gen_ai.* spans  ──OTLP/http-protobuf──►  Datadog LLM Obs
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
search `ml_app:bedrock-agentcore-otlp` (allow 3–5 minutes for traces to appear).

## How telemetry is configured

`agent.py` sets these before importing Strands:

| Variable | Value | Purpose |
|----------|-------|---------|
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | `https://trace.agent.datadoghq.com/v1/traces` | Datadog US1 OTLP intake |
| `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL` | `http/protobuf` | required by the intake |
| `OTEL_EXPORTER_OTLP_TRACES_HEADERS` | `dd-api-key=...,dd-otlp-source=llmobs` | auth + route to LLM Obs |
| `OTEL_SEMCONV_STABILITY_OPT_IN` | `gen_ai_latest_experimental` | make Strands emit v1.37+ GenAI semconv |
| `OTEL_SERVICE_NAME` | `bedrock-agentcore-otlp` | becomes `ml_app` in Datadog |

The endpoint and headers are derived automatically from `DD_SITE` + `DD_API_KEY`.

## Deploying to AgentCore Runtime (optional)

`agent.py` also defines an `@app.entrypoint` handler. On AgentCore Runtime you'd
set the same OTEL env vars as runtime configuration and set
`DISABLE_ADOT_OBSERVABILITY=true` so telemetry flows to Datadog instead of the
built-in CloudWatch pipeline.
