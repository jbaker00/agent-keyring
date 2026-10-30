"""Stubs for future backends. Each raises until its SDK/CLI is wired up.

Planned: 1Password (op CLI / Connect), LastPass (lpass CLI),
Google Password Manager (no official API — human-edit link only),
Microsoft / Windows vault (covered by KeychainBackend via keyring).
"""
from __future__ import annotations

from agent_keyring.errors import BackendUnavailableError


class _Stub:
    def __init__(self, *a, **k):
        raise BackendUnavailableError(
            f"Backend '{self.name}' is not implemented yet. "
            "Use 'keychain' (local) or 'secret-manager' (shared) today."
        )


class OnePasswordBackend(_Stub):
    name = "onepassword"


class LastPassBackend(_Stub):
    name = "lastpass"


class ChromePasswordBackend(_Stub):
    name = "chrome-passwords"
