from __future__ import annotations

import argparse
import getpass
import subprocess
import sys

from agent_keyring import AgentKeyring, backends_info
from agent_keyring.errors import AgentKeyringError


def _kr(args) -> AgentKeyring:
    return AgentKeyring(
        project=getattr(args, "project", None),
        local_backend=getattr(args, "local_backend", None),
        shared_backend=getattr(args, "shared_backend", None),
    )


def _gcloud(*argv: str) -> str:
    try:
        out = subprocess.run(["gcloud", *argv], capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except Exception:
        return ""


def _doctor(args) -> int:
    """Verify the own-account model: everything runs under the user's login."""
    ok = True
    try:
        import keyring

        print(f"local keychain : OK ({type(keyring.get_keyring()).__name__}, service 'agent-keyring')")
    except Exception as e:
        ok = False
        print(f"local keychain : FAIL ({e})")
    account = _gcloud("config", "get-value", "account")
    project = getattr(args, "project", None) or _gcloud("config", "get-value", "project")
    print(f"gcloud account : {account or 'NOT LOGGED IN — run: gcloud auth application-default login'}")
    print(f"gcloud project : {project or 'NOT SET — run: gcloud config set project <YOUR_PROJECT>'}")
    if not account or not project:
        ok = False
    else:
        try:
            from agent_keyring.backends.secret_manager import SecretManagerBackend

            backend = SecretManagerBackend(project=project)
            backend._client().list_secrets(request={"parent": backend._parent(), "page_size": 1})
            print("secret manager : OK (API reachable with your credentials, IAM permits list)")
        except Exception as e:
            ok = False
            print(f"secret manager : FAIL ({e})")
            print("  fix: gcloud services enable secretmanager.googleapis.com "
                  "and grant roles/secretmanager.admin on YOUR project")
    print("model          : own-account — secrets live in YOUR keychain and YOUR GCP project")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="agent-keyring",
        description="Secrets for humans and AI agents: local keychain + shared Secret Manager.",
    )
    p.add_argument("--project", help="GCP project for shared secrets (or AGENT_KEYRING_GCP_PROJECT)")
    p.add_argument("--local-backend", help="Local store name (default keychain, or AGENT_KEYRING_LOCAL_BACKEND)")
    p.add_argument("--shared-backend", help="Shared store name (default secret-manager, or AGENT_KEYRING_SHARED_BACKEND)")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("get", help="Print a secret to stdout (for agents to capture)")
    g.add_argument("key")
    g.add_argument("--scope", choices=["local", "shared", "auto"], default="auto")

    s = sub.add_parser("set", help="Store a secret (prompts without echo if no value given)")
    s.add_argument("key")
    s.add_argument("value", nargs="?")
    s.add_argument("--scope", choices=["local", "shared"], default="local")

    d = sub.add_parser("delete", help="Delete a secret")
    d.add_argument("key")
    d.add_argument("--scope", choices=["local", "shared"], default="local")

    e = sub.add_parser("edit", help="Open the human editor for a store (Keychain Access / Cloud Console)")
    e.add_argument("key", nargs="?")
    e.add_argument("--scope", choices=["local", "shared"], default="local")

    lst = sub.add_parser("list", help="List keys in a store (names only, never values)")
    lst.add_argument("--scope", choices=["local", "shared"], default="shared")

    sub.add_parser("backends", help="List available backends (kind + status)")
    sub.add_parser("doctor", help="Check local keychain + your own gcloud setup (no secrets printed)")

    args = p.parse_args(argv)
    kr = _kr(args)

    try:
        if args.cmd == "get":
            sys.stdout.write(kr.get(args.key, scope=args.scope))
            sys.stdout.write("\n")
        elif args.cmd == "set":
            if args.value is not None:
                print(
                    "warning: passing the value as an argument exposes it in shell "
                    "history and process listings; omit it to be prompted instead.",
                    file=sys.stderr,
                )
            value = args.value if args.value is not None else getpass.getpass(f"Value for {args.key!r}: ")
            kr.set(args.key, value, scope=args.scope)
            print(f"Stored {args.key!r} in {args.scope}.", file=sys.stderr)
        elif args.cmd == "delete":
            ok = kr.delete(args.key, scope=args.scope)
            print("Deleted." if ok else "Not found.", file=sys.stderr)
            return 0 if ok else 1
        elif args.cmd == "edit":
            target = kr.edit_target(scope=args.scope, key=args.key)
            if not target:
                print("No editor known for this platform/store.", file=sys.stderr)
                return 1
            print(target, file=sys.stderr)
            if target.startswith("app:") and sys.platform == "darwin":
                subprocess.run(["open", "-a", target[4:]], check=False)
            elif target.startswith("http"):
                subprocess.run(["open", target], check=False)
        elif args.cmd == "list":
            for key in kr.list_keys(scope=args.scope):
                print(key)
        elif args.cmd == "backends":
            for info in backends_info():
                status = "ready" if info["implemented"] else "planned"
                print(f"{info['name']:<18} kind={info['kind']:<7} {status}")
        elif args.cmd == "doctor":
            return _doctor(args)
    except AgentKeyringError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
