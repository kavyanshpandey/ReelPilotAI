from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from reelpilot.config import Settings, get_settings
from reelpilot.database import get_db
from reelpilot.limits import QuotaExceededError, consume_quota, enforce_api_limit
from reelpilot.models import User
from reelpilot.schemas.content import ContentPackCreate, ContentPackResponse, ContentPackUpdate
from reelpilot.security import get_current_user
from reelpilot.services.content_generation import get_content_generator
from reelpilot.services.content_packs import (
    ContentPackNotFoundError,
    create_content_pack,
    get_content_pack,
    serialize_content_pack,
    update_content_pack,
)

router = APIRouter(tags=["content packs"], dependencies=[Depends(enforce_api_limit)])


@router.post(
    "/v1/clusters/{cluster_id}/content-packs",
    response_model=ContentPackResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_content_pack(
    cluster_id: str,
    request: ContentPackCreate,
    database: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
) -> ContentPackResponse:
    try:
        consume_quota(
            database,
            user.workspace_id,
            "generations",
            1,
            settings.max_generations_per_month,
        )
        pack = create_content_pack(
            database, cluster_id, request, get_content_generator(settings), user.workspace_id
        )
    except QuotaExceededError as exc:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": "3600"},
        ) from exc
    except ContentPackNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return serialize_content_pack(pack)


@router.get("/v1/content-packs/{pack_id}", response_model=ContentPackResponse)
def read_content_pack(
    pack_id: str,
    database: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ContentPackResponse:
    try:
        pack = get_content_pack(database, pack_id)
        if pack.cluster.analysis_run.import_batch.workspace_id != user.workspace_id:
            raise ContentPackNotFoundError("Content pack not found")
        return serialize_content_pack(pack)
    except ContentPackNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/v1/content-packs/{pack_id}", response_model=ContentPackResponse)
def edit_content_pack(
    pack_id: str,
    request: ContentPackUpdate,
    database: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ContentPackResponse:
    try:
        pack = get_content_pack(database, pack_id)
        if pack.cluster.analysis_run.import_batch.workspace_id != user.workspace_id:
            raise ContentPackNotFoundError("Content pack not found")
        return serialize_content_pack(update_content_pack(database, pack_id, request))
    except ContentPackNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
