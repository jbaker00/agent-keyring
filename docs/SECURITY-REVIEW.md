# Security review — agent-keyring v1 (2026-10-28)

Scope: Python core, CLI, Keychain backend, Secret Manager backend. Reviewer pass over all source in `src/`. Three issues were fixed in code during this review; the rest are documented residual risks and design constraints for the SwiftUI app.

## Trust boundary (read this first)

`agent-keyring` does **not** protect against malicious code running as your OS user. Any process running as you can ask the keychain for the same items, and your ADC credentials grant whatever your GCP IAM roles grant. The model is: *the agent is trusted like you are*. What the tool buys you is narrower — no plaintext secrets in `.env` files, repos, shell history (when prompted), or agent prompts/logs by default, and per-secret IAM control on the shared side. Claims beyond that would be dishonest.

## Fixed during this review

| # | Severity | Issue | Fix |
| --- | --- | --- | --- |
| 1 | High | Key collision in shared store: `_secret_id("a/b") == _secret_id("a-b")`, so distinct keys silently aliased to one GCP secret | Valid GCP IDs pass through; other keys are now encoded (`_`→`__`, others →`_xx_` hex) so distinct keys cannot collide. Added regression test. |
| 2 | Medium | `set KEY VALUE` exposes the value in shell history and `ps` | CLI still accepts it (scripting), but now prints an explicit warning and recommends the no-echo prompt. |
| 3 | Medium | `get --scope auto` swallowed `BackendUnavailableError`, reporting "not found" when a store was actually misconfigured (observed live with the missing `[gcp]` install) | Auto now surfaces unavailability when the key wasn't found in the reachable store. |

## Residual risks (accepted, documented)

- **`get` prints to stdout by design.** If a caller logs stdout, the secret is in the log. Agents should hold values in memory, never log them. A trailing newline is added by the CLI; Python callers get the exact value.
- **ADC credential file** (`~/.config/gcloud/application_default_credentials.json`) is plaintext on disk with broad `cloud-platform` scope. Mitigation is IAM least-privilege on the project, not file encryption. Enable Secret Manager **Data Access audit logs** in GCP if you need a read trail — off by default.
- **Shared `set` adds a new version every time; old versions stay readable** until destroyed. Rotation therefore doesn't revoke the old value. A `--destroy-old-versions` option is future work.
- **Local keychain has no read audit trail** on macOS for same-user access.
- **Listing (updated after the swap work).** Python `list_keys` exists per store: Secret Manager enumerates via `list_secrets` (names only); the Keychain backend raises a clear error because the `keyring` API cannot enumerate — the SwiftUI app lists natively via the Security framework filtered to service `agent-keyring`. Never shell out to `security dump-keychain` (would expose unrelated passwords).

## Design constraints for the SwiftUI full-manager app

- App must do its own OAuth for Secret Manager (REST) — do not embed ADC JSON or a service-account key in the app bundle.
- Reveal/copy actions should auto-clear the clipboard (~30s) and require device auth (Touch ID / password) before reveal, since the app aggregates *all* stores in one window — a bigger prize than any single store.
- Backend swapping (other clouds / local managers) must go through the same `SecretBackend` contract so the UI never special-cases a vendor; credentials for each backend stay in that backend, never in app preferences/plists.

## Hygiene

- Dependencies pinned via committed `uv.lock`. Run `pip-audit` in CI before public release (not yet wired).
- No secret values in code, tests (fake backends only), or this repo's history — verified by grep for the account/project identifiers during open-source scrub.
