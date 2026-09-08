from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from reelpilot.config import Settings, get_settings
from reelpilot.database import get_db
from reelpilot.limits import enforce_api_limit
from reelpilot.models import UsageCounter, User
from reelpilot.schemas.usage import UsageMetric, UsageResponse
from reelpilot.security import get_current_user

router = APIRouter(
    prefix="/v1/usage", tags=["usage"], dependencies=[Depends(enforce_api_limit)]
)


@router.get("", response_model=UsageResponse)
def usage(
    database: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
) -> UsageResponse:
    month = datetime.now(UTC).strftime("%Y-%m")
    counter = database.scalar(
        select(UsageCounter).where(
            UsageCounter.workspace_id == user.workspace_id, UsageCounter.month == month
        )
    )
    values = {
        "comments": (counter.comments if counter else 0, settings.max_comments_per_month),
        "analyses": (counter.analyses if counter else 0, settings.max_analyses_per_month),
        "generations": (counter.generations if counter else 0, settings.max_generations_per_month),
    }
    metrics = {
        key: UsageMetric(used=used, limit=limit, remaining=max(0, limit - used))
        for key, (used, limit) in values.items()
    }
    return UsageResponse(month=month, **metrics)

