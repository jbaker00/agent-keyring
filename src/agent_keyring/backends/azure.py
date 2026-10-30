from __future__ import annotations

import json
import os
import shutil
import subprocess

from agent_keyring.backends._names import encode_key
from agent_keyring.errors import BackendUnavailableError


def _vault_name(vault: str | None) -> str:
    v = vault or os.environ.get("AGENT_KEYRING_AZURE_VAULT")
    if not v:
        raise BackendUnavailableError(
            "No Azure Key Vault configured. Set AGENT_KEYRING_AZURE_VAULT=<vault-name> "
            "(create one in YOUR subscription: az keyvault create -n <name> -g <rg>)."
        )
    return v


class AzureKeyVaultBackend:
    """Shared secrets via Azure Key Vault, driven by the `az` CLI.

    Uses your own `az login` session and RBAC on your vault — no embedded
    credentials, mirroring the gcloud model. Vault names/secrets: secret
    names are [0-9a-zA-Z-]; other keys are collision-safely encoded.
    """

    name = "azure-key-vault"
    kind = "shared"

    def __init__(self, vault_name: str | None = None):
        if shutil.which("az") is None:
            raise BackendUnavailableError("`az` CLI not installed (Azure CLI).")
        self.vault = _vault_name(vault_name)

    def _run(self, args: list[str]) -> str:
        out = subprocess.run(["az", *args], capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            err = (out.stderr or out.stdout).strip()
            if "az login" in err or "AADSTS" in err or "not logged in" in err.lower():
                raise BackendUnavailableError(f"Azure CLI not logged in. Run: az login. ({err[:200]})")
            raise BackendUnavailableError(f"az {' '.join(args[:3])} failed: {err[:300]}")
        return out.stdout

    def _name(self, key: str) -> str:
        return encode_key(key, allow_underscore=False)

    def get(self, key: str) -> str | None:
        try:
            out = self._run(["keyvault", "secret", "show", "--vault-name", self.vault,
                             "--name", self._name(key), "-o", "json"])
        except BackendUnavailableError as e:
            if "not found" in str(e).lower() or "SecretNotFound" in str(e):
                return None
            raise
        return json.loads(out).get("value")

    def set(self, key: str, value: str) -> None:
        self._run(["keyvault", "secret", "set", "--vault-name", self.vault,
                   "--name", self._name(key), "--value", value, "-o", "json"])

    def delete(self, key: str) -> bool:
        try:
            self._run(["keyvault", "secret", "delete", "--vault-name", self.vault,
                       "--name", self._name(key)])
            return True
        except BackendUnavailableError as e:
            if "not found" in str(e).lower():
                return False
            raise

    def list_keys(self) -> list[str]:
        out = self._run(["keyvault", "secret", "list", "--vault-name", self.vault, "-o", "json"])
        return sorted(item["name"] for item in json.loads(out))

    def edit_url(self, key: str | None = None) -> str | None:
        return f"https://portal.azure.com/#browse/Microsoft.KeyVault%2Fvaults" \
               f"?vault={self.vault}" if not key else \
               f"https://portal.azure.com/#asset/Microsoft_Azure_KeyVault/Secret/{self.vault}/{self._name(key)}"
