"""App A — Bedrock AgentCore agent with OTLP-native telemetry to Datadog.

Mechanism: the agent emits OpenTelemetry GenAI spans (via Strands' built-in
telemetry) and exports them straight to Datadog's OTLP intake. No Datadog Agent
and no Datadog SDK are involved. This is the same OTLP path that AgentCore's
built-in observability uses.

Run locally:
    python agent.py "What's the weather in Tokyo, and is it a good day to run?"
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# --- Configure OpenTelemetry export to Datadog's OTLP intake -----------------
# Must happen before importing Strands so the exporter picks these up.
DD_SITE = os.getenv("DD_SITE", "datadoghq.com")
DD_API_KEY = os.getenv("DD_API_KEY", "")

# US1 (datadoghq.com) -> https://trace.agent.datadoghq.com/v1/traces
os.environ.setdefault(
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    f"https://trace.agent.{DD_SITE}/v1/traces",
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_TRACES_PROTOCOL", "http/protobuf")
os.environ.setdefault(
    "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
    f"dd-api-key={DD_API_KEY},dd-otlp-source=llmobs",
)
# Strands < 1.37 semconv opt-in: required for Datadog's GenAI mapping.
os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental")
# service.name becomes the `ml_app` you search on in Datadog LLM Observability.
os.environ.setdefault("OTEL_SERVICE_NAME", os.getenv("ML_APP", "bedrock-agentcore-otlp"))

from strands import Agent, tool  # noqa: E402
from strands.models import BedrockModel  # noqa: E402
from strands.telemetry import StrandsTelemetry  # noqa: E402

# Wire Strands' OpenTelemetry tracer to the OTLP exporter configured above.
StrandsTelemetry().setup_otlp_exporter()

DEFAULT_PROMPT = "What's the weather in Tokyo, and is it a good day to run?"
SYSTEM_PROMPT = "You are a helpful assistant. Use the available tools when they help answer the question."


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The name of the city to look up.
    """
    # Fake data — this is a demo. Swap for a real API when you like.
    return f"{city}: 22 C, clear skies, light breeze, humidity 55%"


def build_agent() -> Agent:
    model = BedrockModel(
        model_id=os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0"),
        region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
    )
    return Agent(model=model, tools=[get_weather], system_prompt=SYSTEM_PROMPT)


def invoke(prompt: str) -> str:
    agent = build_agent()
    result = agent(prompt)
    return str(result)


def _flush_telemetry() -> None:
    """Force-export buffered spans before the process exits."""
    try:
        from opentelemetry import trace as otel_trace

        otel_trace.get_tracer_provider().force_flush()
    except Exception:  # best-effort flush; never crash on shutdown
        pass


# --- AgentCore Runtime entrypoint (used only when deployed) ------------------
try:
    from bedrock_agentcore.runtime import BedrockAgentCoreApp

    app = BedrockAgentCoreApp()

    @app.entrypoint
    def agentcore_handler(payload):
        return invoke(payload.get("prompt", DEFAULT_PROMPT))

except ImportError:
    app = None


if __name__ == "__main__":
    if os.getenv("RUN_AGENTCORE_SERVER") == "1" and app is not None:
        # Start the AgentCore Runtime HTTP server (for container/deploy use).
        app.run()
    else:
        prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
        print(f"\n>>> Prompt: {prompt}\n")
        answer = invoke(prompt)
        print(f"\n>>> Answer:\n{answer}\n")
        _flush_telemetry()
        print("Telemetry flushed. Look in Datadog LLM Observability "
              f"(ml_app:{os.environ['OTEL_SERVICE_NAME']}). Allow 3-5 minutes.")
