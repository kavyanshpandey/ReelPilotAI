from pydantic import BaseModel


class UsageMetric(BaseModel):
    used: int
    limit: int
    remaining: int


class UsageResponse(BaseModel):
    month: str
    comments: UsageMetric
    analyses: UsageMetric
    generations: UsageMetric
