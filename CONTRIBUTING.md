# Contributing

```bash
uv venv && uv pip install -e ".[gcp,dev]"
uv run pytest -q
```

## Ground rules

- Never commit a real secret. Local test keys go in your OS keychain (`--scope local`); shared tests use a throwaway GCP project.
- New backends implement the `SecretBackend` protocol in `src/agent_keyring/backends/base.py` and register in `backends/__init__.py`.
- Keep the agent-facing API stable: `AgentKeyring.get/set/delete` with `scope="local" | "shared" | "auto"`.
