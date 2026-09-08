from datetime import datetime

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    import_id: str


class ClusterCommentResponse(BaseModel):
    id: str
    text: str
    username: str | None
    like_count: int
    similarity: float = Field(ge=0, le=1)


class ClusterResponse(BaseModel):
    id: str
    rank: int
    label: str
    canonical_question: str
    opportunity_score: float = Field(ge=0, le=100)
    mention_count: int
    total_likes: int
    signal: str
    comments: list[ClusterCommentResponse]


class AnalysisResponse(BaseModel):
    id: str
    import_id: str
    status: str
    provider: str
    comment_count: int
    created_at: datetime
    completed_at: datetime | None
    clusters: list[ClusterResponse]

