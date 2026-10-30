from __future__ import annotations

import re


def encode_key(key: str, *, allow_underscore: bool) -> str:
    """Map an arbitrary key name to a store-safe identifier without collisions.

    Names already valid pass through unchanged. Otherwise `_` is escaped as
    `__` and any other invalid char becomes `_xx_` (hex), so distinct keys
    can never alias to the same stored name.
    """
    valid = r"[a-zA-Z0-9_-]" if allow_underscore else r"[a-zA-Z0-9-]"
    if re.fullmatch(valid + "{1,255}", key):
        return key
    out: list[str] = []
    for ch in key:
        if ch == "_" and allow_underscore:
            out.append("__")
        elif ch.isascii() and (ch.isalnum() or ch == "-"):
            out.append(ch)
        elif ch == "_":
            out.append("_5f_")
        else:
            out.append(f"_{ord(ch):x}_")
    sid = "".join(out).strip("-")
    if not sid:
        raise ValueError(f"key {key!r} maps to an empty stored name")
    return sid[:255]
