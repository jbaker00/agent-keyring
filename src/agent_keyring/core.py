from __future__ import annotations

import os
from enum import Enum

from agent_keyring.backends import REGISTRY
from agent_keyring.errors import BackendUnavailableError, SecretNotFoundError


class Scope(str, Enum):
    LOCAL = "local"    # this machine only (OS keychain)
    SHARED = "shared"  # synced across machines (Secret Manager)
    AUTO = "auto"      # get: local first, then shared. set: local.


_SCOPE_BACKEND = {Scope.LOCAL: "keychain", Scope.SHARED: "secret-manager"}


class AgentKeyring:
    """One facade so agents never care where a secret lives.

    Example:
        kr = AgentKeyring()
        key = kr.get("openai-api-key", scope="shared")
        kr.set("my-token", "abc", scope="local")
    """

    def __init__(self, *, project: str | None = None, service: str | None = None):
        self._project = project or os.environ.get("AGENT_KEYRING_GCP_PROJECT")
        self._service = service
        self._cache: dict[str, object] = {}

    def _backend(self, scope: Scope):
        backend_name = _SCOPE_BACKEND[scope]  # type: ignore[index]
        if backend_name in self._cache:
            return self._cache[backend_name]
        cls = REGISTRY[backend_name]
        if backend_name == "secret-manager":
            backend = cls(project=self._project)
        elif self._service:
            backend = cls(service=self._service)
        else:
            backend = cls()
        self._cache[backend_name] = backend
        return backend

    def backend_for(self, scope: str | Scope):
        return self._backend(Scope(scope))

    def get(self, key: str, scope: str | Scope = Scope.AUTO) -> str:
        scope = Scope(scope)
        if scope == Scope.AUTO:
            unavailable: list[str] = []
            for s in (Scope.LOCAL, Scope.SHARED):
                try:
                    v = self._backend(s).get(key)
                except BackendUnavailableError as e:
                    unavailable.append(str(e))
                    continue
                if v is not None:
                    return v
            if unavailable:
                raise BackendUnavailableError(
                    f"Secret {key!r} not found locally, and another store was "
                    f"unavailable: {'; '.join(unavailable)}"
                )
            raise SecretNotFoundError(f"Secret {key!r} not found (local or shared)")
        v = self._backend(scope).get(key)
        if v is None:
            raise SecretNotFoundError(f"Secret {key!r} not found in {scope.value}")
        return v

    def get_or_none(self, key: str, scope: str | Scope = Scope.AUTO) -> str | None:
        try:
            return self.get(key, scope)
        except (SecretNotFoundError, BackendUnavailableError):
            return None

    def set(self, key: str, value: str, scope: str | Scope = Scope.LOCAL) -> None:
        scope = Scope(scope)
        if scope == Scope.AUTO:
            scope = Scope.LOCAL
        self._backend(scope).set(key, value)

    def delete(self, key: str, scope: str | Scope = Scope.LOCAL) -> bool:
        scope = Scope(scope)
        if scope == Scope.AUTO:
            scope = Scope.LOCAL
        return bool(self._backend(scope).delete(key))

    def edit_target(self, scope: str | Scope = Scope.LOCAL, key: str | None = None) -> str | None:
        scope = Scope(scope)
        if scope == Scope.AUTO:
            scope = Scope.LOCAL
        return self._backend(scope).edit_url(key)
