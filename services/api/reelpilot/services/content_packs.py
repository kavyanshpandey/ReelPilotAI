from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from reelpilot.models import (
    AnalysisRun,
    ClusterMembership,
    CommentCluster,
    ContentPack,
    ImportBatch,
)
from reelpilot.schemas.content import ContentPackCreate, ContentPackResponse, ContentPackUpdate
from reelpilot.services.content_generation import PROMPT_VERSION, ContentGenerator


class ContentPackNotFoundError(ValueError):
    pass


def create_content_pack(
    database: Session,
    cluster_id: str,
    request: ContentPackCreate,
    generator: ContentGenerator,
    workspace_id: str | None = None,
) -> ContentPack:
    query = (
        select(CommentCluster)
        .join(CommentCluster.analysis_run)
        .join(AnalysisRun.import_batch)
        .where(CommentCluster.id == cluster_id)
        .options(
            selectinload(CommentCluster.memberships).selectinload(ClusterMembership.comment)
        )
    )
    if workspace_id is not None:
        query = query.where(ImportBatch.workspace_id == workspace_id)
    cluster = database.scalar(query)
    if cluster is None:
        raise ContentPackNotFoundError("Audience cluster not found")

    comments = [membership.comment.text for membership in cluster.memberships]
    generated = generator.generate(
        cluster.canonical_question, cluster.label, comments, request.language, request.tone
    )
    latest_version = database.scalar(
        select(func.max(ContentPack.version)).where(ContentPack.cluster_id == cluster.id)
    ) or 0
    content = generated.content
    pack = ContentPack(
        cluster_id=cluster.id,
        version=latest_version + 1,
        provider=generated.provider,
        model=generated.model,
        prompt_version=PROMPT_VERSION,
        language=request.language,
        tone=request.tone,
        hooks=content.hooks,
        script_15=content.script_15,
        script_30=content.script_30,
        script_60=content.script_60,
        caption=content.caption,
        cta=content.cta,
        hashtags=content.hashtags,
        cover_text=content.cover_text,
        b_roll=content.b_roll,
        provider_response_id=generated.response_id,
        input_tokens=generated.input_tokens,
        output_tokens=generated.output_tokens,
    )
    database.add(pack)
    database.commit()
    database.refresh(pack)
    return pack


def get_content_pack(database: Session, pack_id: str) -> ContentPack:
    pack = database.get(ContentPack, pack_id)
    if pack is None:
        raise ContentPackNotFoundError("Content pack not found")
    return pack


def update_content_pack(
    database: Session, pack_id: str, request: ContentPackUpdate
) -> ContentPack:
    pack = get_content_pack(database, pack_id)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(pack, field, value)
    database.commit()
    database.refresh(pack)
    return pack


def serialize_content_pack(pack: ContentPack) -> ContentPackResponse:
    return ContentPackResponse.model_validate(
        {
            column: getattr(pack, column)
            for column in ContentPackResponse.model_fields
        }
    )
