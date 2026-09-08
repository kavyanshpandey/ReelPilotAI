import csv
import io
from datetime import UTC, datetime

from reelpilot.schemas.imports import CommentImportResponse, ImportedComment, ImportWarning

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5_000

TEXT_COLUMNS = ("comment", "text", "comment_text", "message")
USERNAME_COLUMNS = ("username", "user", "author", "from")
MEDIA_COLUMNS = ("media_id", "post_id", "reel_id", "media")
DATE_COLUMNS = ("created_at", "timestamp", "date", "time")
LIKE_COLUMNS = ("like_count", "likes", "like")


class CommentImportError(ValueError):
    pass


def _find_column(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {name.strip().lower(): name for name in fieldnames}
    return next((normalized[name] for name in candidates if name in normalized), None)


def _parse_datetime(value: str) -> datetime | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    normalized = cleaned.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(cleaned, pattern).replace(tzinfo=UTC)
            except ValueError:
                continue
    raise ValueError("date must use ISO 8601, YYYY-MM-DD, DD/MM/YYYY, or MM/DD/YYYY")


def _parse_likes(value: str) -> int:
    cleaned = value.strip()
    if not cleaned:
        return 0
    likes = int(cleaned)
    if likes < 0:
        raise ValueError("like count cannot be negative")
    return likes


def parse_comments_csv(filename: str, content: bytes) -> CommentImportResponse:
    if len(content) > MAX_FILE_BYTES:
        raise CommentImportError("CSV file must be 5 MB or smaller")

    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CommentImportError("CSV file must be UTF-8 encoded") from exc

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise CommentImportError("CSV file must include a header row")

    fieldnames = [name.strip() for name in reader.fieldnames if name]
    text_column = _find_column(fieldnames, TEXT_COLUMNS)
    if text_column is None:
        supported = ", ".join(TEXT_COLUMNS)
        raise CommentImportError(f"Missing comment column. Use one of: {supported}")

    username_column = _find_column(fieldnames, USERNAME_COLUMNS)
    media_column = _find_column(fieldnames, MEDIA_COLUMNS)
    date_column = _find_column(fieldnames, DATE_COLUMNS)
    like_column = _find_column(fieldnames, LIKE_COLUMNS)

    comments: list[ImportedComment] = []
    warnings: list[ImportWarning] = []
    skipped_count = 0

    for row_number, row in enumerate(reader, start=2):
        if row_number > MAX_ROWS + 1:
            raise CommentImportError(f"CSV files are limited to {MAX_ROWS:,} data rows")

        text = (row.get(text_column) or "").strip()
        if not text:
            skipped_count += 1
            warnings.append(ImportWarning(row_number=row_number, message="Empty comment skipped"))
            continue

        try:
            created_at = _parse_datetime(row.get(date_column, "") or "") if date_column else None
            like_count = _parse_likes(row.get(like_column, "") or "") if like_column else 0
        except ValueError as exc:
            skipped_count += 1
            warnings.append(ImportWarning(row_number=row_number, message=str(exc)))
            continue

        comments.append(
            ImportedComment(
                row_number=row_number,
                text=text,
                username=(row.get(username_column) or "").strip() or None
                if username_column
                else None,
                media_id=(row.get(media_column) or "").strip() or None if media_column else None,
                created_at=created_at,
                like_count=like_count,
            )
        )

    if not comments:
        raise CommentImportError("No valid comments were found in the CSV file")

    return CommentImportResponse(
        filename=filename,
        imported_count=len(comments),
        skipped_count=skipped_count,
        detected_columns=fieldnames,
        comments=comments,
        warnings=warnings[:100],
    )
