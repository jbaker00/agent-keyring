# Second-account test — the own-gcloud model

## The model

`agent-keyring` runs **entirely on the user's own accounts**:

- Local secrets → the user's OS keychain, under their OS login.
- Shared secrets → the user's **own GCP project**, under their own `gcloud` login (ADC).

There is no central server, no shared project, and no invite into the developer's project. The earlier idea of inviting a second Gmail account into the maintainer's project tests *cross-user sharing*, which is **not** the product model — it's an optional future feature, out of scope for this test.

## What this test proves

A person who is not the maintainer, with a Gmail/Google account the maintainer does not own, can:

1. Install and run `agent-keyring doctor` green against **their own** project.
2. Do a full shared CRUD cycle in **their own** Secret Manager (the maintainer has zero access to it — that's the point).
3. Do a local CRUD cycle in their own keychain.

## Tester steps (on their machine)

```bash
git clone <repo> && cd agent-keyring
uv venv && uv pip install -e ".[gcp,dev]"

gcloud auth application-default login          # THEIR account
gcloud config set project <THEIR_PROJECT_ID>   # THEIR project
gcloud services enable secretmanager.googleapis.com

uv run agent-keyring doctor                    # all lines OK
uv run agent-keyring set demo-key hello --scope shared
uv run agent-keyring get demo-key
uv run agent-keyring delete demo-key --scope shared
uv run agent-keyring set demo-key hello --scope local
uv run agent-keyring get demo-key --scope local
uv run agent-keyring delete demo-key --scope local
```

## Pass criteria

- [ ] `doctor` exits 0 with their account/project shown.
- [ ] Shared + local CRUD all succeed; `demo-key` visible only in *their* Cloud Console.
- [ ] Maintainer confirms they cannot see the tester's secret (no access was ever granted).

## Optional later: cross-user sharing

If sharing is ever wanted, the owner — never the app by default — grants a narrow role on a single secret in *their* project, e.g. `roles/secretmanager.secretAccessor` on that secret only. The app would surface this as an explicit per-secret action, not a project-wide invite.
