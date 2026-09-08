from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from reelpilot.config import Settings, get_settings
from reelpilot.database import get_db
from reelpilot.limits import QuotaExceededError, consume_quota, enforce_api_limit
from reelpilot.models import Comment, ImportBatch, User
from reelpilot.schemas.imports import CommentImportResponse
from reelpilot.security import get_current_user
from reelpilot.services.comment_import import MAX_FILE_BYTES, CommentImportError, parse_comments_csv

router = APIRouter(
    prefix="/v1/imports", tags=["imports"], dependencies=[Depends(enforce_api_limit)]
)


@router.post("/comments-csv", response_model=CommentImportResponse)
async def import_comments_csv(
    file: Annotated[UploadFile, File()],
    database: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CommentImportResponse:
    filename = file.filename or "comments.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a .csv file",
        )

    content = await file.read(MAX_FILE_BYTES + 1)
    try:
        parsed = parse_comments_csv(filename, content)
    except CommentImportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    batch = ImportBatch(
        filename=parsed.filename,
        imported_count=parsed.imported_count,
        skipped_count=parsed.skipped_count,
        workspace_id=user.workspace_id,
        created_by_id=user.id,
    )
    batch.comments = [
        Comment(
            row_number=comment.row_number,
            text=comment.text,
            username=comment.username,
            media_id=comment.media_id,
            source_created_at=comment.created_at,
            like_count=comment.like_count,
        )
        for comment in parsed.comments
    ]
    try:
        consume_quota(
            database,
            user.workspace_id,
            "comments",
            parsed.imported_count,
            settings.max_comments_per_month,
        )
    except QuotaExceededError as exc:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": "3600"},
        ) from exc
    database.add(batch)
    database.commit()
    database.refresh(batch)
    return parsed.model_copy(update={"import_id": batch.id})
