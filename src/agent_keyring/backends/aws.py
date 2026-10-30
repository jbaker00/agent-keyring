from __future__ import annotations

import json
import os
import shutil
import subprocess

from agent_keyring.errors import BackendUnavailableError


class AwsSecretsManagerBackend:
    """Shared secrets via AWS Secrets Manager, driven by the `aws` CLI.

    Uses your own AWS credentials (SSO / `aws configure`) and IAM on your
    account — no embedded credentials. Secret values are stored as plain
    SecretString under the key name (AWS allows [A-Za-z0-9/_+=.@-]).
    """

    name = "aws-secrets-manager"
    kind = "shared"

    def __init__(self, region: str | None = None, profile: str | None = None):
        if shutil.which("aws") is None:
            raise BackendUnavailableError(
                "`aws` CLI not installed. Install AWS CLI v2, then run: aws configure (or aws sso login)."
            )
        self.region = region or os.environ.get("AGENT_KEYRING_AWS_REGION") or os.environ.get("AWS_REGION")
        self.profile = profile or os.environ.get("AGENT_KEYRING_AWS_PROFILE") or os.environ.get("AWS_PROFILE")

    def _base(self) -> list[str]:
        args = ["secretsmanager"]
        if self.region:
            args += ["--region", self.region]
        if self.profile:
            args += ["--profile", self.profile]
        return args

    def _run(self, args: list[str]) -> str:
        out = subprocess.run(["aws", *self._base(), *args],
                             capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            err = (out.stderr or out.stdout).strip()
            if "ResourceNotFoundException" in err:
                raise _NotFound(err)
            if "Unable to locate credentials" in err or "ExpiredToken" in err or "AuthFailure" in err:
                raise BackendUnavailableError(
                    f"AWS credentials missing/expired. Run: aws configure / aws sso login. ({err[:200]})"
                )
            raise BackendUnavailableError(f"aws secretsmanager failed: {err[:300]}")
        return out.stdout

    def get(self, key: str) -> str | None:
        try:
            out = self._run(["get-secret-value", "--secret-id", key, "--query", "SecretString",
                             "--output", "json"])
        except _NotFound:
            return None
        v = json.loads(out)
        return v if isinstance(v, str) else None

    def set(self, key: str, value: str) -> None:
        try:
            self._run(["put-secret-value", "--secret-id", key, "--secret-string", value])
        except _NotFound:
            self._run(["create-secret", "--name", key, "--secret-string", value])

    def delete(self, key: str) -> bool:
        try:
            self._run(["delete-secret", "--secret-id", key, "--force-delete-without-recovery"])
            return True
        except _NotFound:
            return False

    def list_keys(self) -> list[str]:
        out = self._run(["list-secrets", "--query", "SecretList[].Name", "--output", "json"])
        return sorted(json.loads(out))

    def edit_url(self, key: str | None = None) -> str | None:
        base = "https://console.aws.amazon.com/secretsmanager/listsecrets"
        return f"{base}?search={key}" if key else base


class _NotFound(BackendUnavailableError):
    pass
