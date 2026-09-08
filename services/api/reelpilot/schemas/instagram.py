from datetime import datetime

from pydantic import BaseModel


class InstagramConnectResponse(BaseModel):
    authorization_url: str


class InstagramAccountResponse(BaseModel):
    connected: bool
    username: str | None = None
    instagram_user_id: str | None = None
    account_type: str | None = None
    connected_at: datetime | None = None


class InstagramSyncResponse(BaseModel):
    import_id: str
    media_count: int
    imported_count: int
    skipped_count: int
