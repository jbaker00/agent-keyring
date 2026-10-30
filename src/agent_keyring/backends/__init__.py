from __future__ import annotations

from typing import Any

from agent_keyring.backends.base import SecretBackend
from agent_keyring.backends.future import (
    AwsSecretsManagerBackend,
    AzureKeyVaultBackend,
    ChromePasswordBackend,
    LastPassBackend,
    OnePasswordBackend,
)
from agent_keyring.backends.keychain import KeychainBackend
from agent_keyring.backends.secret_manager import SecretManagerBackend
from agent_keyring.errors import BackendUnavailableError

REGISTRY: dict[str, type] = {
    "keychain": KeychainBackend,
    "secret-manager": SecretManagerBackend,
    "aws-secrets-manager": AwsSecretsManagerBackend,
    "azure-key-vault": AzureKeyVaultBackend,
    "onepassword": OnePasswordBackend,
    "lastpass": LastPassBackend,
    "chrome-passwords": ChromePasswordBackend,
}

# kind: which scope the store serves. implemented: usable today vs planned stub.
BACKEND_INFO: dict[str, dict[str, Any]] = {
    "keychain": {"kind": "local", "implemented": True},
    "secret-manager": {"kind": "shared", "implemented": True},
    "aws-secrets-manager": {"kind": "shared", "implemented": False},
    "azure-key-vault": {"kind": "shared", "implemented": False},
    "onepassword": {"kind": "shared", "implemented": False},
    "lastpass": {"kind": "shared", "implemented": False},
    "chrome-passwords": {"kind": "local", "implemented": False},
}


def create_backend(
    name: str, *, project: str | None = None, service: str | None = None
) -> SecretBackend:
    """Single construction point for every store.

    Callers (core, CLI, UI bridges) never special-case a vendor: they pass a
    registry name plus generic config, and swapping stores is a name change.
    """
    cls = REGISTRY.get(name)
    if cls is None:
        known = ", ".join(sorted(REGISTRY))
        raise BackendUnavailableError(f"Unknown backend {name!r}. Known: {known}")
    if name == "secret-manager":
        return cls(project=project)  # type: ignore[return-value]
    if name == "keychain":
        return cls(service=service) if service else cls()  # type: ignore[return-value]
    return cls()  # planned stubs raise BackendUnavailableError with guidance


__all__ = [
    "SecretBackend",
    "KeychainBackend",
    "SecretManagerBackend",
    "AwsSecretsManagerBackend",
    "AzureKeyVaultBackend",
    "OnePasswordBackend",
    "LastPassBackend",
    "ChromePasswordBackend",
    "REGISTRY",
    "BACKEND_INFO",
    "create_backend",
]
