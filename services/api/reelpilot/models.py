import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from reelpilot.database import Base, utc_now


def new_id() -> str:
    return str(uuid.uuid4())


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    imported_count: Mapped[int] = mapped_column(Integer)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="import_batch", cascade="all, delete-orphan"
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="import_batch", cascade="all, delete-orphan"
    )
    workspace: Mapped["Workspace | None"] = relationship(back_populates="imports")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    import_batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id", ondelete="CASCADE"))
    row_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    import_batch: Mapped[ImportBatch] = relationship(back_populates="comments")
    memberships: Mapped[list["ClusterMembership"]] = relationship(
        back_populates="comment", cascade="all, delete-orphan"
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    import_batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="processing")
    provider: Mapped[str] = mapped_column(String(50))
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    import_batch: Mapped[ImportBatch] = relationship(back_populates="analysis_runs")
    clusters: Mapped[list["CommentCluster"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )


class CommentCluster(Base):
    __tablename__ = "comment_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(120))
    canonical_question: Mapped[str] = mapped_column(Text)
    opportunity_score: Mapped[float] = mapped_column(Float)
    mention_count: Mapped[int] = mapped_column(Integer)
    total_likes: Mapped[int] = mapped_column(Integer)
    signal: Mapped[str] = mapped_column(String(30))
    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="clusters")
    memberships: Mapped[list["ClusterMembership"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )
    content_packs: Mapped[list["ContentPack"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )


class ClusterMembership(Base):
    __tablename__ = "cluster_memberships"

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey("comment_clusters.id", ondelete="CASCADE"), primary_key=True
    )
    comment_id: Mapped[str] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True
    )
    similarity: Mapped[float] = mapped_column(Float)
    cluster: Mapped[CommentCluster] = relationship(back_populates="memberships")
    comment: Mapped[Comment] = relationship(back_populates="memberships")


class ContentPack(Base):
    __tablename__ = "content_packs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    cluster_id: Mapped[str] = mapped_column(ForeignKey("comment_clusters.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(30))
    language: Mapped[str] = mapped_column(String(20))
    tone: Mapped[str] = mapped_column(String(30))
    hooks: Mapped[list[str]] = mapped_column(JSON)
    script_15: Mapped[str] = mapped_column(Text)
    script_30: Mapped[str] = mapped_column(Text)
    script_60: Mapped[str] = mapped_column(Text)
    caption: Mapped[str] = mapped_column(Text)
    cta: Mapped[str] = mapped_column(Text)
    hashtags: Mapped[list[str]] = mapped_column(JSON)
    cover_text: Mapped[str] = mapped_column(String(120))
    b_roll: Mapped[list[str]] = mapped_column(JSON)
    provider_response_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    cluster: Mapped[CommentCluster] = relationship(back_populates="content_packs")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    display_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True)
    workspace: Mapped["Workspace | None"] = relationship(
        back_populates="users", foreign_keys=[workspace_id]
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    users: Mapped[list[User]] = relationship(
        back_populates="workspace", foreign_keys=[User.workspace_id]
    )
    imports: Mapped[list[ImportBatch]] = relationship(back_populates="workspace")


class UsageCounter(Base):
    __tablename__ = "usage_counters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    analyses: Mapped[int] = mapped_column(Integer, default=0)
    generations: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), unique=True, index=True)
    instagram_user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255))
    account_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    access_token: Mapped[str] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
