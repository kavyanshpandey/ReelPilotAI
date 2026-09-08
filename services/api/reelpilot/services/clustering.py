import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from reelpilot.models import Comment

QUESTION_WORDS = {
    "how",
    "what",
    "when",
    "where",
    "which",
    "why",
    "can",
    "should",
    "kitna",
    "kitni",
    "kya",
    "kaise",
    "kaunsa",
    "kab",
}

LABEL_RULES = (
    ({"budget", "cost", "kharcha", "price"}, "Trip budget & costs"),
    ({"camera", "lens", "settings", "export"}, "Camera & editing setup"),
    ({"safe", "safety", "solo"}, "Solo travel safety"),
    ({"permit", "permission"}, "Permits & trip planning"),
    ({"month", "season", "crowd", "time"}, "Best time to visit"),
    ({"hotel", "hotels", "stay"}, "Accommodation"),
)


@dataclass
class CandidateCluster:
    vectors: list[list[float]] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    similarities: list[float] = field(default_factory=list)

    @property
    def centroid(self) -> list[float]:
        dimensions = len(self.vectors[0])
        values = [sum(vector[index] for vector in self.vectors) for index in range(dimensions)]
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


def cosine(left: list[float], right: list[float]) -> float:
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def cluster_comments(
    comments: list[Comment], vectors: list[list[float]], provider: str
) -> list[CandidateCluster]:
    threshold = 0.68 if provider == "openai" else 0.30
    clusters: list[CandidateCluster] = []

    for comment, vector in sorted(
        zip(comments, vectors), key=lambda item: item[0].like_count, reverse=True
    ):
        matches = [(cosine(vector, cluster.centroid), cluster) for cluster in clusters]
        similarity, cluster = max(matches, default=(0.0, None), key=lambda item: item[0])
        if cluster is not None and similarity >= threshold:
            cluster.comments.append(comment)
            cluster.vectors.append(vector)
            cluster.similarities.append(similarity)
        else:
            clusters.append(
                CandidateCluster(vectors=[vector], comments=[comment], similarities=[1.0])
            )
    return clusters


def cluster_label(comments: list[Comment]) -> str:
    words = set(re.findall(r"[\w']+", " ".join(comment.text.lower() for comment in comments)))
    for keywords, label in LABEL_RULES:
        if words & keywords:
            return label
    representative = max(comments, key=lambda comment: comment.like_count).text.strip(" ?.!\n")
    return representative[:57] + ("…" if len(representative) > 57 else "")


def canonical_question(comments: list[Comment]) -> str:
    questions = [comment for comment in comments if is_question(comment.text)]
    representative = max(questions or comments, key=lambda comment: comment.like_count).text.strip()
    return representative if representative.endswith("?") else f"{representative.rstrip('.!')}?"


def is_question(text: str) -> bool:
    words = set(re.findall(r"[\w']+", text.lower()))
    return "?" in text or bool(words & QUESTION_WORDS)


def opportunity_score(cluster: CandidateCluster, largest_cluster: int, most_likes: int) -> float:
    frequency = len(cluster.comments) / max(largest_cluster, 1)
    engagement = sum(comment.like_count for comment in cluster.comments) / max(most_likes, 1)
    question_rate = sum(is_question(comment.text) for comment in cluster.comments) / len(
        cluster.comments
    )

    dated = [comment.source_created_at for comment in cluster.comments if comment.source_created_at]
    if dated:
        newest = max(date.astimezone(UTC) if date.tzinfo else date.replace(tzinfo=UTC) for date in dated)
        age_days = max(0, (datetime.now(UTC) - newest).days)
        recency = max(0.0, 1 - age_days / 90)
    else:
        recency = 0.5

    return round(100 * (0.45 * frequency + 0.20 * recency + 0.15 * engagement + 0.20 * question_rate), 1)


def signal_for(score: float, mention_count: int) -> str:
    if score >= 75 and mention_count >= 2:
        return "Strong signal"
    if score >= 55:
        return "Rising"
    return "Emerging"

