from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess

from agent_keyring.errors import BackendUnavailableError


class OciVaultBackend:
    """Shared secrets via OCI Vault (Secret Management), driven by `oci` CLI.

    Uses your own ~/.oci/config tenancy. Secrets live in a vault you own,
    encrypted with your vault master key. Required config (env or args):
      AGENT_KEYRING_OCI_VAULT_ID, AGENT_KEYRING_OCI_COMPARTMENT_ID
    Creating a secret additionally needs the encryption key:
      AGENT_KEYRING_OCI_KEY_ID
    The app never creates vaults/keys for you — key ownership stays yours.
    """

    name = "oci-vault"
    kind = "shared"

    def __init__(self, vault_id: str | None = None, compartment_id: str | None = None,
                 key_id: str | None = None):
        if shutil.which("oci") is None:
            raise BackendUnavailableError("`oci` CLI not installed (Oracle Cloud CLI).")
        self.vault_id = vault_id or os.environ.get("AGENT_KEYRING_OCI_VAULT_ID")
        self.compartment_id = compartment_id or os.environ.get("AGENT_KEYRING_OCI_COMPARTMENT_ID")
        self.key_id = key_id or os.environ.get("AGENT_KEYRING_OCI_KEY_ID")
        if not self.vault_id or not self.compartment_id:
            raise BackendUnavailableError(
                "OCI Vault not configured. Set AGENT_KEYRING_OCI_VAULT_ID and "
                "AGENT_KEYRING_OCI_COMPARTMENT_ID (find them: oci kms management vault list "
                "--compartment-id <compartment>)."
            )

    def _run(self, args: list[str]) -> dict:
        out = subprocess.run(["oci", *args], capture_output=True, text=True, timeout=90)
        if out.returncode != 0:
            err = (out.stderr or out.stdout).strip()
            if "NotAuthorizedOrNotFound" in err or "not authorized" in err.lower():
                raise BackendUnavailableError(f"OCI IAM denied this call. Check vault policies. ({err[:250]})")
            if "ConfigFile" in err or "No config" in err:
                raise BackendUnavailableError("OCI CLI not configured. Run: oci setup config.")
            raise BackendUnavailableError(f"oci {' '.join(args[:3])} failed: {err[:300]}")
        raw = out.stdout.strip()
        return json.loads(raw) if raw else {}

    def _find(self, key: str) -> dict | None:
        data = self._run(["vault", "secret", "list", "--compartment-id", self.compartment_id,
                          "--vault-id", self.vault_id, "--all"])
        for item in data.get("data", []):
            if item.get("secret-name") == key:
                return item
        return None

    def get(self, key: str) -> str | None:
        try:
            data = self._run(["secrets", "secret-bundle", "get-secret-bundle-by-name",
                              "--vault-id", self.vault_id, "--secret-name", key])
        except BackendUnavailableError as e:
            if "NotAuthorizedOrNotFound" in str(e) or "404" in str(e):
                return None
            raise
        content = data.get("data", {}).get("secret-bundle-content", {}).get("content")
        return base64.b64decode(content).decode("utf-8") if content else None

    def set(self, key: str, value: str) -> None:
        encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
        existing = self._find(key)
        if existing:
            self._run(["vault", "secret", "update-base64", "--secret-id", existing["id"],
                       "--secret-content-content", encoded])
            return
        if not self.key_id:
            raise BackendUnavailableError(
                "Creating an OCI secret needs AGENT_KEYRING_OCI_KEY_ID (your vault master key OCID)."
            )
        self._run(["vault", "secret", "create-base64", "--compartment-id", self.compartment_id,
                   "--vault-id", self.vault_id, "--key-id", self.key_id,
                   "--secret-name", key, "--secret-content-content", encoded])

    def delete(self, key: str) -> bool:
        existing = self._find(key)
        if not existing:
            return False
        # OCI deletes by scheduling; earliest allowed window is used by default.
        self._run(["vault", "secret", "schedule-secret-deletion", "--secret-id", existing["id"]])
        return True

    def list_keys(self) -> list[str]:
        data = self._run(["vault", "secret", "list", "--compartment-id", self.compartment_id,
                          "--vault-id", self.vault_id, "--all"])
        return sorted(item["secret-name"] for item in data.get("data", []))

    def edit_url(self, key: str | None = None) -> str | None:
        return "https://cloud.oracle.com/security/vaults"
