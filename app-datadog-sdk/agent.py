"""App B — Bedrock AgentCore agent observed with the Datadog SDK (zero decorators).

The same Strands agent as App A, observed with Datadog's LLM Observability SDK
(`ddtrace`) running agentless. There are NO observability decorators — only
Strands' functional `@tool` (which defines the tool, same as App A).

What the SDK captures with zero decoration: ddtrace auto-instruments the
underlying Amazon Bedrock calls, so the LLM spans appear in Agent Observability
automatically.

Run locally:
    python agent.py "What's the weather in Tokyo, and is it a good day to run?"
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from ddtrace.llmobs import LLMObs  # noqa: E402

# Enable LLM Observability before any Bedrock client is created so ddtrace can
# auto-instrument the Bedrock (botocore) calls. Reads DD_API_KEY / DD_SITE.
LLMObs.enable(
    ml_app=os.getenv("DD_LLMOBS_ML_APP", "bedrock-agentcore-sdk"),
    agentless_enabled=True,
)

from strands import Agent, tool  # noqa: E402
from strands.models import BedrockModel  # noqa: E402

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
        app.run()
    else:
        prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
        print(f"\n>>> Prompt: {prompt}\n")
        answer = invoke(prompt)
        print(f"\n>>> Answer:\n{answer}\n")
        LLMObs.flush()
        print("Telemetry flushed. Look in Datadog Agent Observability "
              f"(ml_app:{os.getenv('DD_LLMOBS_ML_APP', 'bedrock-agentcore-sdk')}). Allow 3-5 minutes.")
