import pytest

from agent_keyring import AgentKeyring, SecretNotFoundError
from agent_keyring.backends.secret_manager import _secret_id
from agent_keyring.core import Scope


class FakeBackend:
    name = "fake"

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def delete(self, key):
        return self.store.pop(key, None) is not None

    def edit_url(self, key=None):
        return "https://example.com/edit"


@pytest.fixture
def kr(monkeypatch):
    local, shared = FakeBackend(), FakeBackend()
    k = AgentKeyring()
    monkeypatch.setitem(k._cache, "keychain", local)
    monkeypatch.setitem(k._cache, "secret-manager", shared)
    k._local, k._shared = local, shared  # type: ignore[attr-defined]
    return k


def test_local_roundtrip(kr):
    kr.set("a", "1", scope="local")
    assert kr.get("a", scope="local") == "1"


def test_auto_prefers_local(kr):
    kr.set("k", "local-val", scope="local")
    kr._shared.set("k", "shared-val")
    assert kr.get("k", scope="auto") == "local-val"


def test_auto_falls_back_to_shared(kr):
    kr._shared.set("only-shared", "s")
    assert kr.get("only-shared") == "s"


def test_missing_raises(kr):
    with pytest.raises(SecretNotFoundError):
        kr.get("nope")


def test_delete(kr):
    kr.set("x", "y", scope="local")
    assert kr.delete("x", scope="local") is True
    assert kr.get_or_none("x", scope="local") is None


def test_secret_id_sanitizes():
    assert _secret_id("openai/api.key") == "openai-api-key"
    assert _secret_id("my key!") == "my-key"
