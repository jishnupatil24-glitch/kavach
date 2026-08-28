"""
Seeded randomness, explicitly threaded -- never a module-level/global
Random instance. Same (seed, variable name) always produces the same
noise stream; different variables get independent streams derived from
one run seed so, e.g., temperature noise never accidentally correlates
with soil-N noise.
"""
from __future__ import annotations

import hashlib
import random


def make_stream(seed: int, salt: str) -> random.Random:
    """
    A deterministic, independent RNG stream for one named variable.

    Uses hashlib (not the builtin hash()) because Python randomizes
    str hashing per-process by default (PYTHONHASHSEED) -- builtin
    hash() would silently break cross-run reproducibility.
    """
    digest = hashlib.sha256(f"{seed}:{salt}".encode("utf-8")).digest()
    derived_seed = int.from_bytes(digest[:8], "big")
    return random.Random(derived_seed)


def bounded_gaussian(rng: random.Random, stddev: float, clip_stddevs: float) -> float:
    if stddev <= 0:
        return 0.0
    value = rng.gauss(0.0, stddev)
    limit = stddev * clip_stddevs
    return max(-limit, min(limit, value))
