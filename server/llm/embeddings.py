"""Local embedding provider.

The vector is a hashed bag of words and CJK bigrams. MatchAgent depends on
this interface, not on a hosted model. A later provider can replace it.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

DIMS = 256

_ALIASES = {
    "k8s": "kubernetes",
    "js": "javascript",
    "ts": "typescript",
    "pg": "postgresql",
    "postgres": "postgresql",
}


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one unit vector per input text."""


class HashEmbeddingProvider:
    def __init__(self, dims: int = DIMS) -> None:
        self.dims = dims

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_one(text) for text in texts]

    def embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dims
        for token in tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:2], "big") % self.dims
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def tokens(text: str) -> list[str]:
    folded = normalize_text(text)
    found: list[str] = []
    word: list[str] = []
    cjk: list[str] = []

    def flush_word() -> None:
        if len(word) >= 2:
            found.append("".join(word))
        word.clear()

    def flush_cjk() -> None:
        if len(cjk) >= 2:
            for index in range(len(cjk) - 1):
                found.append(cjk[index] + cjk[index + 1])
        cjk.clear()

    for char in folded:
        if "a" <= char <= "z" or char.isdigit() or char in "+#.":
            flush_cjk()
            word.append(char)
            continue
        flush_word()
        if "\u4e00" <= char <= "\u9fff":
            cjk.append(char)
        else:
            flush_cjk()
    flush_word()
    flush_cjk()
    return found


def normalize_text(value: str) -> str:
    chars = []
    for char in (value or "").strip().lower():
        if char.isspace():
            chars.append(" ")
        else:
            chars.append(char)
    return "".join(chars)


def canonical_skill(name: str) -> str:
    folded = normalize_text(name).replace(" ", "")
    return _ALIASES.get(folded, folded)


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))
