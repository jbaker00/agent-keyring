"""Stubs for future backends. Each raises until its SDK/CLI is wired up.

Planned: 1Password (op CLI / Connect), LastPass (lpass CLI),
Google Password Manager (no official API — human-edit link only),
Microsoft / Windows vault (covered by KeychainBackend via keyring).

To implement one: give it real get/set/delete/list_keys/edit_url members
satisfying `SecretBackend`, then flip its `implemented` flag in
`BACKEND_INFO` (backends/__init__.py). No caller changes are needed —
that is the point of the swap contract.
"""
from __future__ import annotations

from agent_keyring.errors import BackendUnavailableError


class _Stub:
    kind = "shared"

    def __init__(self, *a, **k):
        raise BackendUnavailableError(
            f"Backend '{self.name}' is not implemented yet. "
            "Use 'keychain' (local) or 'secret-manager' (shared) today."
        )


class AwsSecretsManagerBackend(_Stub):
    name = "aws-secrets-manager"
    kind = "shared"


class AzureKeyVaultBackend(_Stub):
    name = "azure-key-vault"
    kind = "shared"


class OnePasswordBackend(_Stub):
    name = "onepassword"
    kind = "shared"


class LastPassBackend(_Stub):
    name = "lastpass"
    kind = "shared"


class ChromePasswordBackend(_Stub):
    name = "chrome-passwords"
    kind = "local"
