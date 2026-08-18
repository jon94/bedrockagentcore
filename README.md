# Bedrock AgentCore → Datadog observability

Two minimal, **identical** AWS Bedrock AgentCore agents that send telemetry to
Datadog two different ways. The agent logic is the same in both; only the
observability wiring differs. The goal is to *understand the mechanisms*.

| App | Folder | How telemetry reaches Datadog |
|-----|--------|-------------------------------|
| **App A — OTEL SDK** | [`app-otlp/`](app-otlp/) | Agent emits OpenTelemetry GenAI spans (Strands native telemetry) and exports them **directly to Datadog's OTLP intake** (no Datadog Agent). This is the path AgentCore's built-in observability uses. |
| **App B — DD SDK** | [`app-datadog-sdk/`](app-datadog-sdk/) | Agent is auto-instrumented with the **Datadog LLM Observability SDK** (`ddtrace`), running agentless. |

Both run the **identical agent** with **zero observability decorators** and
surface in **Datadog Agent Observability** — so you can compare what each
instrumentation path captures on its own.

> **Key finding:** with zero decoration, **App A (OTEL SDK)** produces the full
> agent trace (agent invocation + event-loop cycles + LLM calls + tool), while
> **App B (DD SDK)** captures the auto-instrumented **Bedrock LLM calls** only.
> `ddtrace` has no Strands `contrib` integration — Datadog's official Strands
> support is delivered via Strands' native OpenTelemetry (the OTLP path, App A).

## The agent

A tiny [Strands](https://strandsagents.com) agent that answers a prompt and can
call one tool, `get_weather(city)` (returns fake data). That reason → tool →
reason loop is what produces a rich, multi-span trace worth observing:

```
agent invocation                 ← root span
├── LLM call #1                   ← gen_ai span (prompt, model, tokens)
│   └── decision: call get_weather
├── tool: get_weather("Tokyo")    ← tool span (input/output, latency)
└── LLM call #2                   ← gen_ai span (final answer, tokens)
```

## Prerequisites (one-time)

1. **AWS access** — this repo assumes an SSO profile. Log in:
   ```bash
   aws sso login --profile ese-sandbox
   aws sts get-caller-identity --profile ese-sandbox   # sanity check
   ```
2. **Enable Bedrock model access** for Claude Sonnet in **`ap-southeast-1`**
   (Bedrock console → Model access). This is per-region.
3. **Confirm the exact model id** available to you (the default is an APAC
   inference profile; verify it exists in your account):
   ```bash
   aws bedrock list-foundation-models \
     --profile ese-sandbox --region ap-southeast-1 \
     --by-provider anthropic \
     --query "modelSummaries[?contains(modelId,'sonnet')].modelId" --output text
   ```
   Put the id you want into each app's `.env` as `BEDROCK_MODEL_ID`.
4. **Datadog API key** — you'll paste this into each app's `.env` as `DD_API_KEY`.
   Site is US1 (`datadoghq.com`).

## Running

Each app is self-contained. See the per-app README:

- [`app-otlp/README.md`](app-otlp/README.md)
- [`app-datadog-sdk/README.md`](app-datadog-sdk/README.md)

Quick version (from inside an app folder):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in DD_API_KEY etc.
python agent.py "What's the weather in Tokyo, and is it a good day to run?"
```

## Notes

- **Local-first.** Both apps run on your machine and still send real telemetry
  to Datadog. Deploying to AgentCore Runtime is an optional next step (an
  `agentcore` entrypoint is included in each `agent.py`).
- Secrets live in `.env` (gitignored). Nothing sensitive is committed.
