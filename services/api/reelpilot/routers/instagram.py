import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from reelpilot.config import Settings, get_settings
from reelpilot.database import get_db
from reelpilot.limits import QuotaExceededError, consume_quota, enforce_api_limit
from reelpilot.models import Comment, ImportBatch, InstagramAccount, User
from reelpilot.schemas.instagram import (
    InstagramAccountResponse,
    InstagramConnectResponse,
    InstagramSyncResponse,
)
from reelpilot.security import get_current_user
from reelpilot.services.instagram import (
    InstagramAPIError,
    authorization_url,
    exchange_code,
    graph_get,
    graph_get_all,
)

router = APIRouter(prefix="/v1/instagram", tags=["instagram"])
logger = logging.getLogger(__name__)


@router.get("/connect", response_model=InstagramConnectResponse, dependencies=[Depends(enforce_api_limit)])
def connect(
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> InstagramConnectResponse:
    state = jwt.encode(
        {"sub": user.id, "workspace_id": user.workspace_id, "exp": datetime.now(UTC) + timedelta(minutes=10)},
        settings.auth_secret,
        algorithm="HS256",
    )
    try:
        return InstagramConnectResponse(authorization_url=authorization_url(settings, state))
    except InstagramAPIError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/callback")
async def callback(
    code: Annotated[str, Query(min_length=1)],
    state: Annotated[str, Query(min_length=1)],
    database: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        claims = jwt.decode(state, settings.auth_secret, algorithms=["HS256"])
        user_id, workspace_id = claims.get("sub"), claims.get("workspace_id")
        if not user_id or not workspace_id:
            raise ValueError("invalid state")
        token, expires_at = await exchange_code(settings, code)
        profile = await graph_get(settings, "/me", token, fields="id,username")
        instagram_id = profile.get("id")
        username = profile.get("username") or instagram_id
        if not instagram_id:
            raise InstagramAPIError("Instagram profile did not include an id")
    except (jwt.PyJWTError, ValueError, InstagramAPIError) as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Instagram connection failed") from exc

    account = database.scalar(select(InstagramAccount).where(InstagramAccount.workspace_id == workspace_id))
    if account is None:
        account = InstagramAccount(workspace_id=workspace_id, instagram_user_id=instagram_id, username=username, access_token=token)
        database.add(account)
    else:
        account.instagram_user_id = instagram_id
        account.username = username
        account.access_token = token
    account.account_type = profile.get("account_type")
    account.token_expires_at = expires_at
    database.commit()
    return RedirectResponse(f"{settings.web_origin}/?instagram=connected", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/account", response_model=InstagramAccountResponse, dependencies=[Depends(enforce_api_limit)])
def account(
    user: Annotated[User, Depends(get_current_user)], database: Annotated[Session, Depends(get_db)]
) -> InstagramAccountResponse:
    linked = database.scalar(select(InstagramAccount).where(InstagramAccount.workspace_id == user.workspace_id))
    if linked is None:
        return InstagramAccountResponse(connected=False)
    return InstagramAccountResponse(connected=True, username=linked.username, instagram_user_id=linked.instagram_user_id, account_type=linked.account_type, connected_at=linked.connected_at)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(enforce_api_limit)])
def disconnect(
    user: Annotated[User, Depends(get_current_user)], database: Annotated[Session, Depends(get_db)]
) -> None:
    linked = database.scalar(select(InstagramAccount).where(InstagramAccount.workspace_id == user.workspace_id))
    if linked is not None:
        database.delete(linked)
        database.commit()


@router.post("/sync-comments", response_model=InstagramSyncResponse, dependencies=[Depends(enforce_api_limit)])
async def sync_comments(
    user: Annotated[User, Depends(get_current_user)], database: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]
) -> InstagramSyncResponse:
    linked = database.scalar(select(InstagramAccount).where(InstagramAccount.workspace_id == user.workspace_id))
    if linked is None:
        raise HTTPException(status_code=409, detail="Connect an Instagram professional account first")
    if linked.token_expires_at:
        token_expires_at = linked.token_expires_at
        if token_expires_at.tzinfo is None:
            token_expires_at = token_expires_at.replace(tzinfo=UTC)
        if token_expires_at <= datetime.now(UTC):
            raise HTTPException(status_code=401, detail="Instagram access token expired; reconnect the account")
    try:
        media = await graph_get_all(settings, f"{linked.instagram_user_id}/media", linked.access_token, fields="id,caption,timestamp,media_type,comments_count", limit=25)
        imported: list[Comment] = []
        media_diagnostics: list[tuple[str | None, int | None, int]] = []
        for item in media:
            comment_rows = await graph_get_all(settings, f"{item['id']}/comments", linked.access_token, fields="id,text,username,like_count,timestamp", limit=100)
            if not comment_rows and item.get("comments_count"):
                expanded = await graph_get(
                    settings,
                    item["id"],
                    linked.access_token,
                    fields="comments.limit(100){id,text,username,like_count,timestamp}",
                )
                comment_rows = (expanded.get("comments") or {}).get("data", [])
            media_diagnostics.append((item.get("media_type"), item.get("comments_count"), len(comment_rows)))
            for row in comment_rows:
                imported.append(Comment(row_number=len(imported) + 1, text=(row.get("text") or "").strip(), username=row.get("username"), media_id=item["id"], like_count=int(row.get("like_count") or 0)))
        logger.info("Instagram sync checked media_count=%d comment_counts=%s", len(media), media_diagnostics)
    except (InstagramAPIError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    imported = [comment for comment in imported if comment.text]
    if not imported:
        reported_comment_media = 0
        reported_comment_total = 0
        for item in media:
            try:
                count = int(item.get("comments_count") or 0)
            except (TypeError, ValueError):
                count = 0
            if count:
                reported_comment_media += 1
                reported_comment_total += count
        if reported_comment_total:
            detail = (
                f"Instagram reports {reported_comment_total} comments across {reported_comment_media} media items, "
                "but returned no comment rows. Reconnect after confirming instagram_business_manage_comments "
                "and that this account owns the media."
            )
        else:
            detail = (
                f"Instagram returned {len(media)} media items, but no comment rows. Check that comments are on "
                "media owned by this account, that instagram_business_manage_comments is enabled, and reconnect "
                "after changing Meta permissions."
            )
        raise HTTPException(
            status_code=404,
            detail=detail,
        )
    try:
        consume_quota(database, user.workspace_id, "comments", len(imported), settings.max_comments_per_month)
    except QuotaExceededError as exc:
        database.rollback()
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "3600"}) from exc
    batch = ImportBatch(filename="instagram-live-sync", imported_count=len(imported), skipped_count=0, workspace_id=user.workspace_id, created_by_id=user.id, comments=imported)
    database.add(batch)
    database.commit()
    database.refresh(batch)
    return InstagramSyncResponse(import_id=batch.id, media_count=len(media), imported_count=len(imported), skipped_count=0)
