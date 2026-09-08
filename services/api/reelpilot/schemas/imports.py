from datetime import datetime

from pydantic import BaseModel, Field


class ImportedComment(BaseModel):
    row_number: int
    text: str
    username: str | None = None
    media_id: str | None = None
    created_at: datetime | None = None
    like_count: int = Field(default=0, ge=0)


class ImportWarning(BaseModel):
    row_number: int
    message: str


class CommentImportResponse(BaseModel):
    import_id: str | None = None
    filename: str
    imported_count: int
    skipped_count: int
    detected_columns: list[str]
    comments: list[ImportedComment]
    warnings: list[ImportWarning]
