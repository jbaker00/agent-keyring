# agent-keyring

Paste-once secrets for humans and AI agents.

- **Local** secrets live in the OS keychain (macOS Keychain on Mac, Windows Credential Vault on Windows) — never leave the machine.
- **Shared** secrets live in Google Cloud Secret Manager — synced across machines via GCP, for keys an agent needs everywhere.

Humans paste a secret once; agents fetch it by name. No `.env` files full of plaintext keys.

## Install

```bash
uv venv && uv pip install -e ".[gcp,dev]"
# or: python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[gcp,dev]"
gcloud auth application-default login   # for shared secrets
```

## For agents (Python)

```python
from agent_keyring import AgentKeyring

kr = AgentKeyring()  # project from AGENT_KEYRING_GCP_PROJECT or `gcloud config`
api_key = kr.get("openai-api-key", scope="shared")   # or "local" / "auto"
kr.set("my-token", "abc123", scope="local")
```

`scope="auto"` (default for `get`) tries local first, then shared.

## For humans (CLI)

```bash
agent-keyring set openai-api-key --scope shared   # prompts without echo
agent-keyring get openai-api-key                  # prints value (agents capture this)
agent-keyring delete openai-api-key --scope local
agent-keyring backends

# No editor exists for Secret Manager — this opens Cloud Console:
agent-keyring edit openai-api-key --scope shared
# Local on Mac opens Keychain Access:
agent-keyring edit --scope local
```

## Roadmap

- Backends: 1Password, LastPass, Google Password Manager, Chrome extension and native Mac/Windows apps that launch each store's own editor (see `backends/future.py`).
- Today Chrome/Windows human passwords have no agent API — the app will deep-link to their editors rather than scrape them.
