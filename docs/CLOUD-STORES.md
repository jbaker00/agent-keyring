# Cloud secret stores — research note (2026-10-29)

Question asked: do other CSPs have an equivalent of Google Cloud Secret Manager? Yes — every major cloud does. We had not checked before; the registry only had consumer managers (1Password/LastPass/Chrome). All CSP stores below are now **implemented** as CLI-driven shared backends (`aws-secrets-manager`, `azure-key-vault`, `oci-vault`) behind the same `SecretBackend` contract — each uses the user's own cloud CLI login (`aws`/`az`/`oci`), so nothing is embedded. The macOS app still drives GCP natively; AWS/Azure/OCI appear there as "backend ready — app wiring pending".

| Store | Cloud | Auth model | Pricing shape* | Human editor | Agent access path for us |
| --- | --- | --- | --- | --- | --- |
| Secret Manager | GCP | GCP IAM / ADC | Per active secret version + accesses | Cloud Console (no native editor) | **Implemented** (Python SDK + `gcloud` in app) |
| Secrets Manager | AWS | AWS IAM | ~$0.40/secret/month + ~$0.05 per 10k calls; auto-rotation (Lambda/RDS) | AWS Console | **Implemented** (`aws` CLI). Needs AWS CLI v2 installed |
| Parameter Store | AWS | AWS IAM | Standard tier free, lower limits | AWS Console | Same AWS CLI; cheaper fallback, fewer rotation features |
| Key Vault (secrets) | Azure | Entra ID (Azure AD) + RBAC / access policies | Per-operation (+ per-key/HSM tiers) | Azure Portal | **Implemented** (`az keyvault secret`). Set `AGENT_KEYRING_AZURE_VAULT`; needs `az login` |
| Vault (HCP or self-hosted) | Multi-cloud | Tokens / AppRole / cloud IAM | Self-hosted (source-available) or HCP SaaS tiers | Web UI | `vault` CLI / API — cloud-agnostic option |
| OCI Vault / Secret Management | Oracle (OCI) | OCI IAM + compartments | Per-secret/operation in your tenancy | OCI Console (cloud.oracle.com) | **Implemented** (`oci` CLI). Set `AGENT_KEYRING_OCI_VAULT_ID` + `AGENT_KEYRING_OCI_COMPARTMENT_ID` (+ `AGENT_KEYRING_OCI_KEY_ID` to create); the app never creates vaults/keys |

\* Shapes summarized from vendor/secondary pricing guides at research time; verify current vendor pricing pages before quoting.

Also relevant (consumer/SaaS, already stubbed): 1Password, LastPass, Doppler, Infisical, Akeyless — different trust model from CSP-native stores.

## Implication for agent-keyring

The own-account model generalizes cleanly: on AWS the app would shell/SDK to the user's own AWS account (`aws` CLI, their IAM), on Azure their own tenant/vault (`az` CLI). No store changes the facade: `AgentKeyring(shared_backend="aws-secrets-manager")` is the whole switch once that backend is implemented. Priority order for implementation: AWS Secrets Manager first (largest ask), then Azure Key Vault, then Vault if multi-cloud demand appears.
