from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretBackend(Protocol):
    name: str

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> bool: ...
    def edit_url(self, key: str | None = None) -> str | None:
        """URL or app hint for a human to edit secrets in this backend."""
        ...
