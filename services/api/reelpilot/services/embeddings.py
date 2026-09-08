import hashlib
import math
import os
import re
from collections import Counter
from itertools import pairwise
from typing import Protocol

from openai import OpenAI

from reelpilot.config import Settings

TOKEN_PATTERN = re.compile(r"[\w']+", re.UNICODE)

CANONICAL_TOKENS = {
    "budget": "budget",
    "cost": "budget",
    "costs": "budget",
    "kharcha": "budget",
    "price": "budget",
    "camera": "camera",
    "lens": "camera",
    "settings": "camera",
    "export": "camera",
    "safe": "safety",
    "safety": "safety",
    "solo": "safety",
    "permit": "permit",
    "permission": "permit",
    "month": "season",
    "season": "season",
    "time": "season",
    "crowd": "season",
    "hotel": "stay",
    "hotels": "stay",
    "stay": "stay",
}


class EmbeddingProvider(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbeddingProvider:
    name = "local"

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def _features(self, text: str) -> Counter[str]:
        tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
        canonical = [CANONICAL_TOKENS.get(token, token) for token in tokens]
        features: Counter[str] = Counter(f"word:{token}" for token in canonical)
        for category in set(canonical) & set(CANONICAL_TOKENS.values()):
            features[f"topic:{category}"] += 4
        for left, right in pairwise(canonical):
            features[f"pair:{left}:{right}"] += 1
        return features

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for feature, weight in self._features(text).items():
                digest = hashlib.sha256(feature.encode()).digest()
                index = int.from_bytes(digest[:4], "big") % self.dimensions
                vector[index] += float(weight)
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors


class OpenAIEmbeddingProvider:
    name = "openai"

    def __init__(self, model: str, dimensions: int) -> None:
        self.client = OpenAI()
        self.model = model
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
            encoding_format="float",
        )
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    use_openai = settings.embedding_provider == "openai" or (
        settings.embedding_provider == "auto" and bool(os.getenv("OPENAI_API_KEY"))
    )
    if use_openai:
        return OpenAIEmbeddingProvider(settings.embedding_model, settings.embedding_dimensions)
    return LocalEmbeddingProvider(settings.embedding_dimensions)
