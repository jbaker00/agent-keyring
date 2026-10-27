# agent-keyring — paste a key once, store it everywhere, let agents use it without seeing it

Status: **idea / not started** (written 2026-10-12). Come back here to pick it up.

## The idea in one paragraph

When you create an API key or password, you paste it **once** into this tool.
It writes it to every store you've selected (macOS Keychain, GCP Secret
Manager, 1Password, Bitwarden, …), records *what the key is* (which vendor
account, which project, what it's for, read-only or not, when it expires), and
gives AI agents (Claude Code, Codex, Meta Muse, whatever comes next) a
**name** to use, never the value. The agent says "run this with
`OPENAI_ADMIN_KEY`" and the tool injects the secret at runtime. The agent
never prints it, never stores it, and never has it in its context.

## Why — what we did by hand on 2026-10-12

Tracking down a $5 OpenAI bill turned into a key-management session. Every
step below is something the tool should do in one action:

1. **Create the key** in the vendor console (OpenAI → Admin keys). The agent
   was rightly blocked from doing this itself, so a human creates it and
   clicks Copy.
2. **Store it in GCP Secret Manager** without it appearing on screen:
   `pbpaste | gcloud secrets create NAME --data-file=- && pbcopy </dev/null`
3. **Grant the reader access.** The pi5's service account
   (`reader@your-gcp-project`) is granted access per secret, so
   each new secret needs its own `add-iam-policy-binding`. This step was
   easy to forget.
4. **Copy it into the macOS Keychain** as `creds:NAME`
   (`security add-generic-password -U -s creds:NAME …`), then read it back
   and compare to confirm the copy.
5. **Add a pointer line** to `~/code/creds/secrets.h`:
   `export NAME="$(_kc NAME)"` plus a comment saying which account it lives
   in, its permissions, and when it was created.
6. **Point the consumer at it.** The pi5 monitor's `_sm_overlay` mapping
   needed the new name added.

The problems that made it a whole session, and that the tool should prevent:

- **An expired key nobody noticed.** The old `OPENAI_ADMIN_KEY` had expired,
  and the monitor skipped the 401 silently for weeks. The tool should know
  expiry dates and warn before them.
- **A key in an account nobody remembered.** The Creole voice key lived in a
  second OpenAI account (you@example.com) with $16 of prepaid credit.
  `secrets.h` said "billing: personal acct", which was wrong. The tool's
  inventory should record the *owning account* for every key, and it can
  check that automatically (an admin key can list the keys in its own
  account).
- **Copies drifting apart.** Keychain, Secret Manager, `secrets.h` and the
  pi5 each had a different idea of what was current. A single tool that
  writes every copy, and can confirm they still match, fixes that.

## Is it a skill, an MCP server, a plugin, or an app?

It's really **one program with several front ends**:

| Piece | What it is | Role here |
|---|---|---|
| **Core CLI / library** | the actual program | Writes to the stores, keeps the inventory, injects secrets into commands (`agent-keyring run --env OPENAI_ADMIN_KEY -- python3 monitor.py`) |
| **MCP server** | a standard protocol any agent can speak (Claude, Codex, and others that support MCP) | How agents *use* secrets: `list_secrets` (names + metadata only), `run_with_secrets`, `request_new_secret` (asks the human to paste). It never returns a value, which makes it agent-neutral |
| **Skill** | instructions for one agent (Claude) on *how/when* to use a tool | "Never print a key; use agent-keyring's run tool; record the owning account." Thin; it teaches the agent the habit |
| **Plugin** | a bundle (for Claude Code: skills + MCP servers + hooks packaged together) | The way to ship the skill and MCP server together for Claude Code users. Other agents would get the MCP server alone |
| **App** (Mac menu-bar, later Windows/iOS) | the human front end | The "paste once" box, store selection, expiry dashboard. On iOS, a Share-sheet extension: copy a key → Share → "Save to my vaults" |

So: **build the CLI and MCP server first** (they're useful to any agent),
add a Claude **plugin** that bundles a skill with the MCP server, and add the
**app** once the core is proven.

## Does it already exist? (from memory — verify before building)

Pieces exist; this exact combination may not:

- **Multi-store sync:** *Teller* (open-source, syncs between providers like
  Vault, AWS, GCP and 1Password), *Doppler* and *Infisical* (hosted secret
  managers with syncs to clouds and CI), *SOPS* (encrypted files).
- **Runtime injection without exposing values:** 1Password CLI
  (`op run`, `op inject`, `op://` references), Doppler (`doppler run`),
  Infisical (`infisical run`), Bitwarden Secrets Manager CLI (`bws run`).
  1Password's reference model is closest to the "agent sees a name, not a
  value" idea.
- **Agent-specific:** check whether 1Password, Doppler or Infisical now ship
  an MCP server, and search the MCP registries for "secrets"/"vault". This is
  moving fast; something may have shipped since this was written.
- **Probably missing:** a *personal* (not team/enterprise) tool that (a) fans
  out to consumer stores like Keychain/iCloud Keychain and a cloud store at
  once, (b) keeps a per-key inventory of owning account, expiry and
  permissions, and (c) has agent-safety rules built in. Most existing tools
  pick one store as the hub and sync from it.

## Store types to support (rough priority)

1. macOS Keychain (`security` CLI) — done by hand today.
2. GCP Secret Manager (`gcloud`) — done by hand today, including the
   per-secret access grant.
3. 1Password (`op`), Bitwarden (`bw` / `bws`).
4. AWS Secrets Manager, Azure Key Vault, HashiCorp Vault.
5. Windows Credential Manager (Windows app).
6. iCloud Keychain / Passwords app, through the app.
7. LastPass (`lpass` CLI; check it's still maintained).

**"Google password store":** Google Password Manager (passwords.google.com)
has **no public API for writing**, so it can't be a target. GCP Secret
Manager, which is what we used today, is a different product and does have
an API.

## Design rules (learned the hard way)

- **The agent never sees values.** The MCP tools return names and metadata
  only. Injection happens in a subprocess the agent can't read back.
- **The human creates keys.** Creating credentials and writing to secret
  stores should go through a human approval (the Claude auto-mode classifier
  blocked both today, correctly). The tool makes that step a single paste.
- **Read-only by default.** Monitoring keys should be read-only; record the
  permission level and flag any all-access key that sits on a server.
- **Inventory first.** For each key, record: owning account and email,
  project, consumers (which repos, crons and machines read it), permissions,
  created date, expires date, rotation notes.
- **Check it still works.** Periodically confirm each key with a free read
  endpoint (as the pi5 monitor's canaries do) and alert on 401 or expiry.
- **Ask before deleting.** Rotation creates the new copy everywhere,
  confirms it, and only then asks to delete the old one.

## Suggested first version (one weekend)

A Python CLI plus an MCP server, Mac only:
- `ak add NAME --stores keychain,gcp:your-gcp-project --grant reader@… --account "openai:you@example.com" --expires 2027-01-01 --note "…"`
  reads the value from the clipboard, writes it to each store, confirms each
  copy, clears the clipboard, and appends to `~/.agent-keyring/inventory.json`
  (metadata only).
- `ak run --env NAME… -- <command>` runs a command with the secrets injected.
- `ak doctor` checks every copy still matches and every key still works, and
  lists keys expiring within 30 days.
- `ak export-secrets-h` regenerates the `_kc` pointer lines in `secrets.h`.
- An MCP server exposing `list`, `run`, `doctor` and `request_new` (no tool
  that reveals a value).

## Product angle (if it becomes an app)

- **Audience:** indie developers and people running several AI agents who
  keep keys in many places. That's exactly the situation here.
- **Pitch:** "Paste a key once. It's in your Keychain, your cloud vault and
  your password manager, and your AI agents can use it without ever seeing
  it."
- **Fit with the existing portfolio:** a Mac menu-bar app, plus an iOS
  Share-sheet extension, is the same pattern as NFS Files' Mac and iOS
  builds.
- **Risk:** it's a security product, so trust is everything. Open-source
  the core and keep values local or in the user's own clouds. No server of
  ours ever sees a key.
