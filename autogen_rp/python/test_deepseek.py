"""Quick automated test for DeepSeek integration."""

import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def test() -> None:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY not set")
        return 1

    print("Creating DeepSeek client...")
    model_client = OpenAIChatCompletionClient(
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        api_key=api_key,
        model_info={
            "function_calling": True,
            "json_output": True,
            "vision": False,
            "family": "unknown",
            "structured_output": True,
        },
    )

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
    exit(asyncio.run(test()))
