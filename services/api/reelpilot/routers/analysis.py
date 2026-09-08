from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from reelpilot.config import Settings, get_settings
from reelpilot.database import get_db
from reelpilot.limits import QuotaExceededError, consume_quota, enforce_api_limit
from reelpilot.models import User
from reelpilot.schemas.analysis import AnalysisRequest, AnalysisResponse
from reelpilot.security import get_current_user
from reelpilot.services.analysis import (
    AnalysisNotFoundError,
    get_analysis,
    run_analysis,
    serialize_analysis,
)
from reelpilot.services.embeddings import get_embedding_provider

router = APIRouter(
    prefix="/v1/analysis-runs", tags=["analysis"], dependencies=[Depends(enforce_api_limit)]
)


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_analysis(
    request: AnalysisRequest,
    database: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
) -> AnalysisResponse:
    try:
        consume_quota(
            database,
            user.workspace_id,
            "analyses",
            1,
            settings.max_analyses_per_month,
        )
        analysis = run_analysis(
            database, request.import_id, get_embedding_provider(settings), user.workspace_id
        )
    except QuotaExceededError as exc:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": "3600"},
        ) from exc
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return serialize_analysis(analysis)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def read_analysis(
    analysis_id: str,
    database: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> AnalysisResponse:
    try:
        analysis = get_analysis(database, analysis_id)
        if analysis.import_batch.workspace_id != user.workspace_id:
            raise AnalysisNotFoundError("Analysis not found")
        return serialize_analysis(analysis)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
