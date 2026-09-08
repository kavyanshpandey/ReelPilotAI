from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from reelpilot.database import utc_now
from reelpilot.models import AnalysisRun, ClusterMembership, CommentCluster, ImportBatch
from reelpilot.schemas.analysis import (
    AnalysisResponse,
    ClusterCommentResponse,
    ClusterResponse,
)
from reelpilot.services.clustering import (
    canonical_question,
    cluster_comments,
    cluster_label,
    opportunity_score,
    signal_for,
)
from reelpilot.services.embeddings import EmbeddingProvider


class AnalysisNotFoundError(ValueError):
    pass


def run_analysis(
    database: Session, import_id: str, provider: EmbeddingProvider, workspace_id: str | None = None
) -> AnalysisRun:
    query = select(ImportBatch).where(ImportBatch.id == import_id)
    if workspace_id is not None:
        query = query.where(ImportBatch.workspace_id == workspace_id)
    batch = database.scalar(
        query.options(selectinload(ImportBatch.comments))
    )
    if batch is None:
        raise AnalysisNotFoundError("Comment import not found")

    analysis = AnalysisRun(
        import_batch_id=batch.id,
        status="processing",
        provider=provider.name,
        comment_count=len(batch.comments),
    )
    database.add(analysis)
    database.flush()

    vectors = provider.embed([comment.text for comment in batch.comments])
    candidates = cluster_comments(batch.comments, vectors, provider.name)
    largest_cluster = max((len(cluster.comments) for cluster in candidates), default=1)
    most_likes = max((sum(comment.like_count for comment in cluster.comments) for cluster in candidates), default=1)

    scored = [
        (candidate, opportunity_score(candidate, largest_cluster, most_likes))
        for candidate in candidates
    ]
    for candidate, score in sorted(scored, key=lambda item: item[1], reverse=True):
        cluster = CommentCluster(
            analysis_run_id=analysis.id,
            label=cluster_label(candidate.comments),
            canonical_question=canonical_question(candidate.comments),
            opportunity_score=score,
            mention_count=len(candidate.comments),
            total_likes=sum(comment.like_count for comment in candidate.comments),
            signal=signal_for(score, len(candidate.comments)),
        )
        cluster.memberships = [
            ClusterMembership(comment=comment, similarity=round(similarity, 4))
            for comment, similarity in zip(candidate.comments, candidate.similarities)
        ]
        analysis.clusters.append(cluster)

    analysis.status = "completed"
    analysis.completed_at = utc_now()
    database.commit()
    return get_analysis(database, analysis.id)


def get_analysis(database: Session, analysis_id: str) -> AnalysisRun:
    analysis = database.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.id == analysis_id)
        .options(
            selectinload(AnalysisRun.clusters)
            .selectinload(CommentCluster.memberships)
            .selectinload(ClusterMembership.comment)
        )
    )
    if analysis is None:
        raise AnalysisNotFoundError("Analysis not found")
    return analysis


def serialize_analysis(analysis: AnalysisRun) -> AnalysisResponse:
    ranked = sorted(analysis.clusters, key=lambda cluster: cluster.opportunity_score, reverse=True)
    return AnalysisResponse(
        id=analysis.id,
        import_id=analysis.import_batch_id,
        status=analysis.status,
        provider=analysis.provider,
        comment_count=analysis.comment_count,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        clusters=[
            ClusterResponse(
                id=cluster.id,
                rank=rank,
                label=cluster.label,
                canonical_question=cluster.canonical_question,
                opportunity_score=cluster.opportunity_score,
                mention_count=cluster.mention_count,
                total_likes=cluster.total_likes,
                signal=cluster.signal,
                comments=[
                    ClusterCommentResponse(
                        id=membership.comment.id,
                        text=membership.comment.text,
                        username=membership.comment.username,
                        like_count=membership.comment.like_count,
                        similarity=membership.similarity,
                    )
                    for membership in sorted(
                        cluster.memberships,
                        key=lambda item: item.comment.like_count,
                        reverse=True,
                    )[:5]
                ],
            )
            for rank, cluster in enumerate(ranked, start=1)
        ],
    )
