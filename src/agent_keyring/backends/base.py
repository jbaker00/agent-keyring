from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretBackend(Protocol):
    """Contract every store must implement so stores can be swapped.

    Two kinds exist:
    - ``local``  — lives on this machine (e.g. OS keychain). Never synced.
    - ``shared`` — synced across machines (e.g. Google Cloud Secret Manager).

    The UI and `AgentKeyring` only ever talk to this protocol. Adding or
    swapping a store means implementing these members and registering the
    class in `backends/__init__.py` — no caller changes.
    """

    name: str
    kind: str  # "local" | "shared"

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> bool: ...

    def list_keys(self) -> list[str]:
        """All keys in this store. May raise BackendUnavailableError if the
        store cannot enumerate (e.g. the Python `keyring` API has no list)."""
        ...

    def edit_url(self, key: str | None = None) -> str | None:
        """URL or app hint for a human to edit secrets in this backend."""
        ...
