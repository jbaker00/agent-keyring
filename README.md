# agent-keyring

Paste-once secrets for humans and AI agents.

Humans paste a password or API key **once** into a real store. Agents then fetch it **by name** — no `.env` files full of plaintext keys, nothing for the agent to scrape or leak.

Built for the **Meta Global AI Developer Hackathon** (Cerebral Valley × Meta) and intended for open-source release under MIT.

## The model: your accounts, your stores

Everything runs on **the user's own accounts**. There is no central server and no shared project.

| Scope | Default store | Lives where | Good for |
| --- | --- | --- | --- |
| `local` | OS Keychain (`keychain`) | This machine only — macOS Keychain, Windows Credential Vault | Machine-specific tokens |
| `shared` | Google Cloud Secret Manager (`secret-manager`) | Your own GCP project, synced by Google, IAM-controlled | Keys an agent needs on every machine |

Stores are **swappable per scope** behind one `SecretBackend` contract — see [Swapping backends](#swapping-backends). Planned stores (1Password, LastPass, Chrome Passwords) appear as `planned` in `agent-keyring backends` and need no caller changes once implemented.

## Install

```bash
uv venv && uv pip install -e ".[gcp,dev]"
# or: python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[gcp,dev]"

gcloud auth application-default login        # YOUR account, for shared secrets
gcloud config set project YOUR_PROJECT_ID    # YOUR project
gcloud services enable secretmanager.googleapis.com

uv run agent-keyring doctor                  # verify your setup (prints no secrets)
```

`doctor` confirms the local keychain, your gcloud account/project, and that Secret Manager answers under your IAM permissions.

## For agents (Python)

```python
from agent_keyring import AgentKeyring

kr = AgentKeyring()  # project from AGENT_KEYRING_GCP_PROJECT or `gcloud config`
api_key = kr.get("openai-api-key", scope="shared")   # or "local" / "auto"
kr.set("my-token", "abc123", scope="local")
```

`scope="auto"` (default for `get`) tries local first, then shared. Secrets are returned in memory — hold them there, never log them.

Demo: [examples/demo_agent.py](examples/demo_agent.py) fetches a key and proves possession masked (`sk-***`), never printing it.

## For humans

**CLI** — `get` prints to stdout (that's the agent capture path); `set` without a value prompts without echo:

```bash
agent-keyring set openai-api-key --scope shared
agent-keyring get openai-api-key
agent-keyring list --scope shared        # key names only, never values
agent-keyring delete openai-api-key --scope local
agent-keyring backends                   # stores, kinds, ready vs planned
agent-keyring edit demo-key --scope shared   # opens Cloud Console (Secret Manager has no native editor)
```

**macOS app** — native SwiftUI full manager in [apps/macos](apps/macos/README.md): browse/search both stores, add/edit/delete, reveal behind Touch ID with 30-second clipboard clearing. It reads the *same* Keychain items the CLI writes (verified both directions) and drives shared secrets through your own `gcloud` login — no credentials embedded in the app.

```bash
cd apps/macos && ./make-app.sh && open dist/AgentKeyring.app
```

Step-by-step manual checks: [TESTING.md](TESTING.md).

## Swapping backends

```python
kr = AgentKeyring(shared_backend="onepassword")   # once implemented
```

```bash
export AGENT_KEYRING_SHARED_BACKEND=onepassword   # or AGENT_KEYRING_LOCAL_BACKEND
agent-keyring --shared-backend onepassword get my-key --scope shared
```

Defaults are `keychain` (local) and `secret-manager` (shared). Every store implements `get / set / delete / list_keys / edit_url` with a `kind` of `local` or `shared` and registers in `backends/__init__.py` (`REGISTRY` + `BACKEND_INFO`); construction goes through the single `create_backend` factory, so core, CLI, and app never special-case a vendor.

## Security

Read [docs/SECURITY-REVIEW.md](docs/SECURITY-REVIEW.md) before trusting this with real keys. Headlines:

- **Trust boundary:** this does not protect against malicious code running as your OS user. It removes plaintext secrets from files/prompts and adds per-secret GCP IAM — nothing more, and it says so.
- Three reviewed bugs were fixed in code: shared key-name collisions (`a/b` vs `a-b`), argv secrets leaking to shell history (CLI now warns), and `auto` masking store misconfiguration as "not found".
- Secrets are never hardcoded in this repo; test keys only ever live in a keychain or a throwaway GCP project.

Second-account verification of the own-gcloud model: [docs/SECOND-ACCOUNT-TEST.md](docs/SECOND-ACCOUNT-TEST.md). That test needs a Gmail account the maintainer doesn't own, running the same `doctor` + CRUD script against **their own** project — deliberately a future, human-in-the-loop step.

## Status & roadmap

Done: Python core + CLI (`get/set/delete/list/edit/backends/doctor`), Keychain + Secret Manager backends, swap contract, contest demo, security review with fixes, native macOS app, open-source scrub + MIT license.

Next: implement 1Password / LastPass behind the existing contract, direct Secret Manager REST + OAuth in the macOS app (replacing the `gcloud` bridge), Windows app, Chrome extension that deep-links to each store's own editor (Chrome/Windows human passwords have no agent API — linking, not scraping, is the design).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed — [LICENSE](LICENSE).
