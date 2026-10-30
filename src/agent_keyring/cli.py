from __future__ import annotations

import argparse
import getpass
import subprocess
import sys

from agent_keyring import AgentKeyring
from agent_keyring.backends import REGISTRY
from agent_keyring.errors import AgentKeyringError


def _kr(args) -> AgentKeyring:
    return AgentKeyring(project=getattr(args, "project", None))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="agent-keyring",
        description="Secrets for humans and AI agents: local keychain + shared Secret Manager.",
    )
    p.add_argument("--project", help="GCP project for shared secrets (or AGENT_KEYRING_GCP_PROJECT)")
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

    sub.add_parser("backends", help="List available backends")

    args = p.parse_args(argv)
    kr = _kr(args)

    try:
        if args.cmd == "get":
            sys.stdout.write(kr.get(args.key, scope=args.scope))
            sys.stdout.write("\n")
        elif args.cmd == "set":
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
        elif args.cmd == "backends":
            for name in REGISTRY:
                print(name)
    except AgentKeyringError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
