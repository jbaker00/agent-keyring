import base64
import json

import pytest

from agent_keyring.backends.aws import AwsSecretsManagerBackend
from agent_keyring.backends.azure import AzureKeyVaultBackend
from agent_keyring.backends.oci import OciVaultBackend
from agent_keyring.errors import BackendUnavailableError


@pytest.fixture(autouse=True)
def fake_clis(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda c: f"/usr/bin/{c}")
    monkeypatch.setenv("AGENT_KEYRING_AZURE_VAULT", "testvault")
    monkeypatch.setenv("AGENT_KEYRING_OCI_VAULT_ID", "ocid1.vault.test")
    monkeypatch.setenv("AGENT_KEYRING_OCI_COMPARTMENT_ID", "ocid1.compartment.test")
    monkeypatch.setenv("AGENT_KEYRING_OCI_KEY_ID", "ocid1.key.test")


def test_azure_roundtrip_via_mocked_cli(monkeypatch):
    b = AzureKeyVaultBackend()
    calls = []
    store = {}

    def fake_run(args):
        calls.append(args)
        if "show" in args:
            return json.dumps({"value": store.get(args[args.index("--name") + 1])})
        if "set" in args:
            store[args[args.index("--name") + 1]] = args[args.index("--value") + 1]
            return "{}"
        if "list" in args:
            return json.dumps([{"name": k} for k in store])
        if "delete" in args:
            store.pop(args[args.index("--name") + 1], None)
            return ""
        return "{}"

    monkeypatch.setattr(b, "_run", fake_run)
    b.set("my key", "v1")
    assert b.get("my key") == "v1"
    assert b.list_keys()
    assert b.delete("my key") is True


def test_aws_get_parses_secret_string(monkeypatch):
    b = AwsSecretsManagerBackend()
    monkeypatch.setattr(b, "_run", lambda args: json.dumps("s3cr3t"))
    assert b.get("k") == "s3cr3t"


def test_oci_get_decodes_base64(monkeypatch):
    b = OciVaultBackend()
    payload = base64.b64encode("oci-value".encode()).decode()
    monkeypatch.setattr(b, "_run", lambda args: {
        "data": {"secret-bundle-content": {"content": payload}}})
    assert b.get("k") == "oci-value"


def test_missing_config_is_clear_error(monkeypatch):
    monkeypatch.delenv("AGENT_KEYRING_AZURE_VAULT")
    monkeypatch.setattr("shutil.which", lambda c: "/usr/bin/az")
    with pytest.raises(BackendUnavailableError, match="AGENT_KEYRING_AZURE_VAULT"):
        AzureKeyVaultBackend()
