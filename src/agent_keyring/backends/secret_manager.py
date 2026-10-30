from __future__ import annotations

import os
import re
import subprocess

from agent_keyring.errors import BackendUnavailableError, SecretNotFoundError


def _default_project() -> str | None:
    if p := os.environ.get("AGENT_KEYRING_GCP_PROJECT"):
        return p
    if p := os.environ.get("GOOGLE_CLOUD_PROJECT"):
        return p
    try:
        out = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True, text=True, timeout=5,
        )
        v = out.stdout.strip()
        return v or None
    except Exception:
        return None


def _secret_id(key: str) -> str:
    # GCP secret IDs: [a-zA-Z0-9_-], 1-255 chars, cannot start with a digit issue is fine but keep safe
    sid = re.sub(r"[^a-zA-Z0-9_-]", "-", key).strip("-")
    if not sid:
        raise ValueError(f"key {key!r} maps to an empty GCP secret id")
    return sid[:255]


class SecretManagerBackend:
    """Shared secrets via Google Cloud Secret Manager.

    Synced across machines through GCP IAM. There is no end-user
    password-style editor; `edit_url` points humans at Cloud Console.
    Agents authenticate via ADC (`gcloud auth application-default login`).
    """

    name = "secret-manager"

    def __init__(self, project: str | None = None):
        self.project = project or _default_project()
        if not self.project:
            raise BackendUnavailableError(
                "No GCP project. Set AGENT_KEYRING_GCP_PROJECT or run "
                "`gcloud config set project <PROJECT>`."
            )
        try:
            from google.cloud import secretmanager  # noqa: F401
        except ImportError as e:
            raise BackendUnavailableError(
                "google-cloud-secret-manager not installed. "
                "Install with: uv pip install -e \".[gcp]\"  (or pip install 'agent-keyring[gcp]')"
            ) from e

    def _client(self):
        from google.cloud import secretmanager

        return secretmanager.SecretManagerServiceClient()

    def _parent(self) -> str:
        return f"projects/{self.project}"

    def _name(self, key: str) -> str:
        return f"{self._parent()}/secrets/{_secret_id(key)}"

    def get(self, key: str) -> str | None:
        from google.api_core import exceptions as gexc

        client = self._client()
        try:
            resp = client.access_secret_version(
                request={"name": f"{self._name(key)}/versions/latest"}
            )
            return resp.payload.data.decode("utf-8")
        except gexc.NotFound:
            return None

    def set(self, key: str, value: str) -> None:
        from google.api_core import exceptions as gexc

        client = self._client()
        parent = self._parent()
        sid = _secret_id(key)
        try:
            client.create_secret(
                request={"parent": parent, "secret_id": sid,
                         "secret": {"replication": {"automatic": {}}}}
            )
        except gexc.AlreadyExists:
            pass
        client.add_secret_version(
            request={"parent": self._name(key),
                     "payload": {"data": value.encode("utf-8")}}
        )

    def delete(self, key: str) -> bool:
        from google.api_core import exceptions as gexc

        client = self._client()
        try:
            client.delete_secret(request={"name": self._name(key)})
            return True
        except gexc.NotFound:
            return False

    def edit_url(self, key: str | None = None) -> str | None:
        base = (
            "https://console.cloud.google.com/security/secret-manager"
            f"?project={self.project}"
        )
        if key:
            return f"https://console.cloud.google.com/security/secret-manager/secret/{_secret_id(key)}/versions?project={self.project}"
        return base
