# Testing agent-keyring — try it yourself

> **Where we are:** v1 core is built and working locally.
> The CLI is `agent-keyring get / set / delete / edit / backends`.
> Local Keychain is verified. Shared (Secret Manager) code is written but not yet live-tested against your project.

---

## How it "logs in" — it doesn't; it borrows yours

### 🔐 Keychain (local)

- No login code at all.
- The `keyring` library talks to the **macOS Security framework** as your user.
- Your login keychain is already unlocked because you're logged into the Mac, so reads/writes just work.
- Entries are namespaced under service **`agent-keyring`** so they don't collide with your other passwords.
- Nothing is stored by us in plaintext — macOS encrypts it.

### ☁️ gcloud / Secret Manager (shared)

Also no login code. The Google client library auto-discovers credentials in this order:

1. `GOOGLE_APPLICATION_CREDENTIALS`
2. `~/.config/gcloud/application_default_credentials.json` — created by `gcloud auth application-default login`

On your machine that's whatever account you used for `gcloud auth application-default login`.

**Project is resolved in this order:**

1. `--project` flag
2. `AGENT_KEYRING_GCP_PROJECT`
3. `GOOGLE_CLOUD_PROJECT`
4. `gcloud config get-value project`

**Permissions are pure GCP IAM:** that account needs the Secret Manager API enabled plus e.g. `roles/secretmanager.admin` (or narrower accessor/creator roles) on the project. If either is missing, `shared` commands fail — local ones never touch Google.

---

## Setup (once)

```bash
uv venv && uv pip install -e ".[gcp,dev]"
```

> ⚠️ `.[dev]` alone is **not** enough — without `.[gcp]` every `--scope shared` command fails with `google-cloud-secret-manager not installed`.

## 1. Local CRUD cycle (zero setup — start here)

Run from the project directory:

```bash
# CREATE
uv run agent-keyring set demo-key local-secret-123 --scope local

# READ — this is what an agent captures
uv run agent-keyring get demo-key --scope local

# MODIFY — set again overwrites locally; in shared it adds a new secret version
uv run agent-keyring set demo-key local-secret-456 --scope local
uv run agent-keyring get demo-key --scope local

# EDIT (human side) — opens Keychain Access; find service "agent-keyring"
uv run agent-keyring edit --scope local

# DELETE, then confirm it's gone (should error)
uv run agent-keyring delete demo-key --scope local
uv run agent-keyring get demo-key --scope local
```

**What to check:**

- [ ] `get` after the second `set` prints `local-secret-456`
- [ ] Keychain Access shows an `agent-keyring` entry while the key exists
- [ ] Final `get` errors with `Secret not found` and exit code 1

---

## 2. Shared CRUD cycle (one-time setup first)

```bash
# One-time setup
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable secretmanager.googleapis.com

# Same cycle, shared
uv run agent-keyring set demo-key shared-secret-123 --scope shared
uv run agent-keyring get demo-key                        # auto: local first, then shared
uv run agent-keyring edit demo-key --scope shared        # opens Cloud Console (no native editor exists)
uv run agent-keyring delete demo-key --scope shared
```

**What to check:**

- [ ] Secret appears under **Secret Manager** in Cloud Console for your project
- [ ] Plain `get` (no `--scope`) finds it via the `auto` fallback, even with nothing stored locally
- [ ] Re-running `set` creates a **new version** instead of overwriting — visible in Console

---

## 3. The agent (Python) view

```bash
uv run python -c "from agent_keyring import AgentKeyring; print(AgentKeyring().get('demo-key'))"
```

---

## 4. Things worth testing deliberately

| Test | Command | Expected |
| --- | --- | --- |
| Missing key | `uv run agent-keyring get nope --scope local` | Clean `Secret not found` error, exit 1 |
| Auto fallback | Store only as `shared`, then `get` with no `--scope` | Still finds it |
| Backend list | `uv run agent-keyring backends` | `keychain`, `secret-manager`, plus future stubs |

---

## Cleanup

```bash
uv run agent-keyring delete demo-key --scope local
uv run agent-keyring delete demo-key --scope shared
```
