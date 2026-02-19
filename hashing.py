"""
hashing.py – Custom multi pass hash function used for password storage.

Produces an integer hash; passwords are never stored in plain text.
"""

import math

# ── Constants derived from e and ln ───────────────────────────────────────────
CONSTANTS = [
    int(math.exp(1) * 10),
    int(math.exp(2)),
    int(math.log(100) * 10),
    int(math.log(1000, 10)),
    int(math.exp(3) / 10),
    int(math.log(10000) * 5),
    int(math.log(100000, 10)),
]

_INITIAL = int(math.exp(5))
_MODULUS = 10**9 + 7


# ── Bit-mixing transforms ──────────────────────────────────────────────────────

def _t1(x: int, c: int) -> int:
    return ((x ^ c) + (x << 3) - (x >> 1)) % _MODULUS

def _t2(x: int, c: int) -> int:
    return ((x * c) ^ (x + c)) % _MODULUS

def _t3(x: int, c: int) -> int:
    return (((x + c) * (x ^ c)) + (x << 4) - (x >> 2)) % _MODULUS

def _t4(x: int, c: int) -> int:
    return ((x ^ (c << 3)) + (x * 17) - (c >> 2)) % _MODULUS


# ── Core hasher ───────────────────────────────────────────────────────────────

def _hash_string(s: str) -> int:
    """Single-pass hash of a string."""
    ascii_vals = [ord(ch) for ch in s]
    h = _INITIAL

    for i, v in enumerate(ascii_vals):
        h = _t1(h, v + CONSTANTS[i % len(CONSTANTS)])
    for i, v in enumerate(reversed(ascii_vals)):
        h = _t2(h, v + CONSTANTS[i % len(CONSTANTS)])
    for i, v in enumerate(ascii_vals):
        h = _t3(h, v + CONSTANTS[i % len(CONSTANTS)])
    for i, v in enumerate(reversed(ascii_vals)):
        h = _t4(h, v + CONSTANTS[i % len(CONSTANTS)])

    length = len(s)
    h = _t4(_t3(_t2(_t1(h, length), length), length), length)
    return h


def hash_password(raw: str, iterations: int = 5) -> int:
    """
    Iteratively hash *raw* for extra security.

    Parameters
    ----------
    raw:        Plain-text password string.
    iterations: Number of hashing rounds (default 5).

    Returns
    -------
    Integer hash suitable for database storage.
    """
    value: str | int = raw
    for _ in range(iterations):
        value = _hash_string(str(value))
    return value


# ── Backwards-compatible alias (used by DatabaseSQL / main) ───────────────────
FinalHasher = hash_password