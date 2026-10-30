import pytest

from agent_keyring import AgentKeyring, SecretNotFoundError
from agent_keyring.backends.secret_manager import _secret_id
from agent_keyring.core import Scope


class FakeBackend:
    name = "fake"
    kind = "local"

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def delete(self, key):
        return self.store.pop(key, None) is not None

    def list_keys(self):
        return sorted(self.store)

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


def test_swap_backend_by_instance():
    fake = FakeBackend()
    k = AgentKeyring(local_backend=fake, shared_backend=fake)
    k.set("s", "v", scope="shared")
    assert k.get("s", scope="local") == "v"  # same swapped-in store serves both scopes
    assert k.list_keys(scope="shared") == ["s"]
    assert k.backend_name("local") == "fake"


def test_swap_backend_by_env(monkeypatch):
    monkeypatch.setenv("AGENT_KEYRING_SHARED_BACKEND", "onepassword")
    k = AgentKeyring()
    assert k.backend_name("shared") == "onepassword"
    assert k.backend_name("local") == "keychain"  # default unchanged
    with pytest.raises(Exception) as e:
        k.get("x", scope="shared")
    assert "not implemented" in str(e.value)


def test_backends_info_metadata():
    from agent_keyring import backends_info

    info = {b["name"]: b for b in backends_info()}
    assert info["keychain"] == {"name": "keychain", "kind": "local", "implemented": True}
    assert info["secret-manager"]["kind"] == "shared"
    assert info["onepassword"]["implemented"] is False


def test_secret_id_sanitizes():
    assert _secret_id("openai-api-key") == "openai-api-key"  # valid IDs pass through
    assert _secret_id("a/b") != _secret_id("a-b")  # distinct keys never collide
    assert _secret_id("openai/api.key") != _secret_id("openai-api-key")
