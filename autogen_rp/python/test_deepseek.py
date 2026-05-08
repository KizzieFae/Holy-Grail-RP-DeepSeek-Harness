"""Quick automated test for DeepSeek integration."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "rp_app"))

from autogen_agentchat.agents import AssistantAgent

from model_client import create_deepseek_client


async def test() -> int:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY not set")
        return 1

    print("Creating DeepSeek client...")
    model_client = create_deepseek_client(api_key=api_key)

    print("Creating agent...")
    agent = AssistantAgent(
        name="test_assistant",
        model_client=model_client,
        system_message="You are a test assistant. Reply with exactly: 'Test successful. DeepSeek is working.'",
    )

    print("Running test query...")
    result = await agent.run(task="Say the test confirmation message.")

    # Get the last message content
    last_message = result.messages[-1].content if result.messages else "No response"
    print(f"\nResponse: {last_message}")

    await model_client.close()
    print("\nTest completed successfully!")
    return 0


if __name__ == "__main__":
    code = asyncio.run(test())
    raise SystemExit(code if code is not None else 0)
