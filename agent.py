from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from tools import load_repo, describe_repo, find_code

MODEL = "qwen2.5:7b"

llm = ChatOllama(model=MODEL, temperature=0)

agent = create_react_agent(
    model=llm,
    tools=[load_repo, describe_repo, find_code],
)


def run_agent(user_message):
    print(f'User: "{user_message}"\n')

    result = agent.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })

    for msg in result["messages"]:
        if msg.type == "ai" and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"[agent decides] call {tc['name']} with {tc['args']}")
        elif msg.type == "tool":
            preview = msg.content[:200]
            print(f"[tool result] {preview}...")

    print("\n--- FINAL ANSWER ---")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    run_agent("Load https://github.com/AltunbasYusuf/SmartVineyard-Analytics, then tell me which function loads the YOLO model.")