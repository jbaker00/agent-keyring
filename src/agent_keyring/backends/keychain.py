from __future__ import annotations

import platform

from agent_keyring.errors import BackendUnavailableError

DEFAULT_SERVICE = "agent-keyring"


class KeychainBackend:
    """Local secrets via the OS keychain.

    Uses the `keyring` library: macOS Keychain on Mac, Windows
    Credential Vault on Windows, Secret Service on Linux.
    Nothing leaves the machine — ideal for local-only keys.
    """

    name = "keychain"
    kind = "local"

    def __init__(self, service: str = DEFAULT_SERVICE):
        self.service = service
        try:
            import keyring  # noqa: F401
        except ImportError as e:
            raise BackendUnavailableError("`keyring` package not installed") from e

    def _kr(self):
        import keyring

        return keyring

    def get(self, key: str) -> str | None:
        return self._kr().get_password(self.service, key)

    def set(self, key: str, value: str) -> None:
        self._kr().set_password(self.service, key, value)

    def delete(self, key: str) -> bool:
        kr = self._kr()
        if kr.get_password(self.service, key) is None:
            return False
        kr.delete_password(self.service, key)
        return True

    def list_keys(self) -> list[str]:
        # The `keyring` API cannot enumerate items. The SwiftUI app lists
        # natively via the Security framework; CLI/Python callers get a
        # clear error instead of a misleading empty list.
        raise BackendUnavailableError(
            "The Python keyring API cannot list keychain items. "
            "Use the macOS app (native Security framework query) to browse local secrets."
        )

    def edit_url(self, key: str | None = None) -> str | None:
        if platform.system() == "Darwin":
            return "app:Keychain Access"
        if platform.system() == "Windows":
            return "app:Credential Manager (control /name Microsoft.CredentialManager)"
        return None
