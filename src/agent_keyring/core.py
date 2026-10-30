from __future__ import annotations

import os
from enum import Enum

from agent_keyring.backends import BACKEND_INFO, create_backend
from agent_keyring.errors import BackendUnavailableError, SecretNotFoundError

BackendLike = str | object  # registry name, or a ready SecretBackend instance


class Scope(str, Enum):
    LOCAL = "local"    # this machine only (a "local"-kind backend)
    SHARED = "shared"  # synced across machines (a "shared"-kind backend)
    AUTO = "auto"      # get: local first, then shared. set: local.


_DEFAULT_BACKEND = {Scope.LOCAL: "keychain", Scope.SHARED: "secret-manager"}
_ENV_VAR = {Scope.LOCAL: "AGENT_KEYRING_LOCAL_BACKEND", Scope.SHARED: "AGENT_KEYRING_SHARED_BACKEND"}


class AgentKeyring:
    """One facade so agents never care where a secret lives.

    Stores are swappable per scope without code changes:

        kr = AgentKeyring()                                   # keychain + secret-manager
        kr = AgentKeyring(shared_backend="onepassword")       # future, once implemented
        AGENT_KEYRING_SHARED_BACKEND=onepassword              # same, via environment

    Tests and UIs may also pass ready backend instances instead of names.

    Example:
        key = kr.get("openai-api-key", scope="shared")
        kr.set("my-token", "abc", scope="local")
    """

    def __init__(
        self,
        *,
        project: str | None = None,
        service: str | None = None,
        local_backend: BackendLike | None = None,
        shared_backend: BackendLike | None = None,
    ):
        self._project = project or os.environ.get("AGENT_KEYRING_GCP_PROJECT")
        self._service = service
        self._cache: dict[str, object] = {}
        self._instances: dict[Scope, object] = {}
        self._names: dict[Scope, str] = {}
        for scope, chosen in ((Scope.LOCAL, local_backend), (Scope.SHARED, shared_backend)):
            if chosen is None:
                self._names[scope] = os.environ.get(_ENV_VAR[scope]) or _DEFAULT_BACKEND[scope]
            elif isinstance(chosen, str):
                self._names[scope] = chosen
            else:  # ready instance (tests, UI bridges)
                self._instances[scope] = chosen
                self._names[scope] = getattr(chosen, "name", scope.value)

    def backend_name(self, scope: str | Scope) -> str:
        return self._names[Scope(scope)]

    def _backend(self, scope: Scope):
        if scope in self._instances:
            return self._instances[scope]
        name = self._names[scope]
        if name in self._cache:
            return self._cache[name]
        backend = create_backend(name, project=self._project, service=self._service)
        self._cache[name] = backend
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

    def list_keys(self, scope: str | Scope = Scope.SHARED) -> list[str]:
        """Keys in one store. Raises BackendUnavailableError if that store
        cannot enumerate (notably local keychain via Python — the macOS
        app lists those natively)."""
        scope = Scope(scope)
        if scope == Scope.AUTO:
            scope = Scope.SHARED
        return list(self._backend(scope).list_keys())

    def edit_target(self, scope: str | Scope = Scope.LOCAL, key: str | None = None) -> str | None:
        scope = Scope(scope)
        if scope == Scope.AUTO:
            scope = Scope.LOCAL
        return self._backend(scope).edit_url(key)


def backends_info() -> list[dict]:
    """Registry metadata for CLIs/UIs: name, kind, implemented-today."""
    return [
        {"name": name, "kind": info["kind"], "implemented": info["implemented"]}
        for name, info in sorted(BACKEND_INFO.items())
    ]
