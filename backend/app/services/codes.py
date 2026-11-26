"""Tracking codes like RS-7K2Q: 31 characters with no look-alikes (no 0/O, 1/I/L)."""

import secrets

ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
assert len(ALPHABET) == 31


def new_tracking_code(length: int = 4) -> str:
    return "RS-" + "".join(secrets.choice(ALPHABET) for _ in range(length))


def normalise_code(code: str) -> str:
    """Accept what people type: lower case, missing hyphen, O for 0 is NOT guessed."""
    c = code.strip().upper().replace(" ", "")
    if not c.startswith("RS-"):
        c = "RS-" + c.removeprefix("RS")
    return c
