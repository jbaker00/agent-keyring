# Agent Keyring — macOS app

Native SwiftUI manager for the same stores the Python core uses. Secrets are never stored in the app itself.

## Build & run

```bash
cd apps/macos
swift build -c release
./make-app.sh          # assembles dist/AgentKeyring.app
open dist/AgentKeyring.app
# or, during development: swift run
```

## How each store works

| Store | Mechanism | Auth |
| --- | --- | --- |
| Local Keychain | Security framework, service `agent-keyring` — the exact items the CLI writes, so CLI and app see the same secrets | Your Mac login; Touch ID / password required before reveal |
| Google Cloud | `gcloud` CLI under **your own** login and project (`secrets list / versions access / versions add / delete`). Values go on stdin, never argv | Whatever `gcloud auth` you already did; IAM on your project decides |
| 1Password / LastPass / Chrome | Shown as planned; will implement the Python `SecretBackend` contract natively | Per-backend sign-in, never app-embedded keys |

Design constraints honored (from `docs/SECURITY-REVIEW.md`): no ADC JSON or service-account keys embedded in the bundle, clipboard auto-clears after 30s, list views never fetch values, reveal is behind device-owner authentication.

Known v1 bridge: shared access shells out to `gcloud` instead of direct Secret Manager REST + OAuth. That reuses your existing own-account login honestly; a direct OAuth client is the follow-up, not a silent credential copy.
