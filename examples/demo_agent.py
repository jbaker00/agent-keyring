"""Contest demo: an agent that needs an API key — without any .env file.

Run:
    uv run agent-keyring set demo-api-key paste-your-key-here --scope local
    uv run python examples/demo_agent.py

The agent asks agent-keyring for `demo-api-key` by name. The value is held
in memory only: never read from disk, never printed, never logged.
"""
from agent_keyring import AgentKeyring


def masked(value: str) -> str:
    return value[:3] + "***" if len(value) > 3 else "***"


def main() -> None:
    kr = AgentKeyring()
    api_key = kr.get_or_none("demo-api-key")  # local first, then shared
    if api_key is None:
        print("No 'demo-api-key' found. Store one first:")
        print("  uv run agent-keyring set demo-api-key --scope local")
        return
    # In a real agent this is where the key would go into an API client.
    # We only prove possession — the secret itself is never printed.
    print(f"Agent fetched demo-api-key ({masked(api_key)}, {len(api_key)} chars) — no .env involved.")
    print("Simulated API call: Authorization header set from memory, request would go out now.")


if __name__ == "__main__":
    main()
