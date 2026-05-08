"""Simple DeepSeek chat example with AutoGen."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "rp_app"))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console

from model_client import create_deepseek_client


async def main() -> None:
    # Check for API key
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set.")
        print("Set it with: $env:DEEPSEEK_API_KEY = 'your-key-here'")
        return

    model_client = create_deepseek_client(api_key=api_key)

    # Create an assistant agent
    agent = AssistantAgent(
        name="deepseek_assistant",
        model_client=model_client,
        system_message="You are a helpful AI assistant powered by DeepSeek. Be concise and clear.",
    )

    # Run a simple conversation
    print("=" * 50)
    print("DeepSeek Chat Example")
    print("=" * 50)
    print("Type 'exit' to quit\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        await Console(agent.run_stream(task=user_input))

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
