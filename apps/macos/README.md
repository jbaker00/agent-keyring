# Agent Keyring — macOS app

Native SwiftUI manager for the same stores the Python core uses. Secrets are never stored in the app itself.

## Build & run

**Xcode (preferred):** open `AgentKeyring.xcodeproj`, pick your signing team
(Signing & Capabilities → Team; bundle ID `dev.agent-keyring.app`), then Run.
Verify from CLI with:

```bash
xcodebuild -project apps/macos/AgentKeyring.xcodeproj -target AgentKeyring \
  -configuration Release CODE_SIGN_IDENTITY="-" CODE_SIGN_STYLE=Manual build
```

**SwiftPM (headless fallback):**

```bash
cd apps/macos
./make-app.sh          # assembles dist/AgentKeyring.app
open dist/AgentKeyring.app
```

Signing/entitlements: `AgentKeyring.entitlements` deliberately sets
`app-sandbox=false` — the app must spawn the user's own `gcloud`/`aws`/`az`/`oci`
CLIs, which a sandbox forbids. Keychain and Touch ID need no extra entitlement
in an unsandboxed macOS app. Before any App Store step this must be
re-architected around direct REST + OAuth per `docs/SECURITY-REVIEW.md`.

## How each store works

| Store | Mechanism | Auth |
| --- | --- | --- |
| Local Keychain | Security framework, service `agent-keyring` — the exact items the CLI writes, so CLI and app see the same secrets | Your Mac login; Touch ID / password required before reveal |
| Google Cloud | `gcloud` CLI under **your own** login and project (`secrets list / versions access / versions add / delete`). Values go on stdin, never argv | Whatever `gcloud auth` you already did; IAM on your project decides |
| 1Password / LastPass / Chrome | Shown as planned; will implement the Python `SecretBackend` contract natively | Per-backend sign-in, never app-embedded keys |

Design constraints honored (from `docs/SECURITY-REVIEW.md`): no ADC JSON or service-account keys embedded in the bundle, clipboard auto-clears after 30s, list views never fetch values, reveal is behind device-owner authentication.

Known v1 bridge: shared access shells out to `gcloud` instead of direct Secret Manager REST + OAuth. That reuses your existing own-account login honestly; a direct OAuth client is the follow-up, not a silent credential copy.
