from agent_keyring.backends.base import SecretBackend
from agent_keyring.backends.future import (
    ChromePasswordBackend,
    LastPassBackend,
    OnePasswordBackend,
)
from agent_keyring.backends.keychain import KeychainBackend
from agent_keyring.backends.secret_manager import SecretManagerBackend

REGISTRY = {
    "keychain": KeychainBackend,
    "secret-manager": SecretManagerBackend,
    "onepassword": OnePasswordBackend,
    "lastpass": LastPassBackend,
    "chrome-passwords": ChromePasswordBackend,
}

__all__ = [
    "SecretBackend",
    "KeychainBackend",
    "SecretManagerBackend",
    "OnePasswordBackend",
    "LastPassBackend",
    "ChromePasswordBackend",
    "REGISTRY",
]
