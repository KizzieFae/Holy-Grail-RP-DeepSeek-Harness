"""Simple DeepSeek chat example with AutoGen."""

import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    # Check for API key
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set.")
        print("Set it with: $env:DEEPSEEK_API_KEY = 'your-key-here'")
        return

    # Create the model client directly
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

        print("\nAssistant: ", end="", flush=True)
        
        # Run the agent with streaming
        response = await Console(agent.run_stream(task=user_input))
        print()  # New line after response

    # Cleanup
    await model_client.close()
    print("\nGoodbye!")


if __name__ == "__main__":
    asyncio.run(main())
