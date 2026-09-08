from io import BytesIO

import pytest

from reelpilot.services.comment_import import CommentImportError, parse_comments_csv


def test_parses_supported_comment_columns() -> None:
    content = (
        b"username,comment,post_id,created_at,likes\n"
        b"neha,Trip ka budget kitna tha?,reel-1,2026-08-12T10:30:00+05:30,12\n"
        b"sam,Which camera did you use?,reel-1,2026-08-13,3\n"
    )

    result = parse_comments_csv("comments.csv", content)

    assert result.imported_count == 2
    assert result.skipped_count == 0
    assert result.comments[0].username == "neha"
    assert result.comments[0].like_count == 12
    assert result.comments[1].text == "Which camera did you use?"


def test_skips_invalid_rows_with_warnings() -> None:
    content = b"text,date,likes\n,2026-08-12,2\nValid question?,not-a-date,1\nAnother?,2026-08-12,4\n"

    result = parse_comments_csv("comments.csv", content)

    assert result.imported_count == 1
    assert result.skipped_count == 2
    assert len(result.warnings) == 2


def test_rejects_csv_without_comment_column() -> None:
    with pytest.raises(CommentImportError, match="Missing comment column"):
        parse_comments_csv("comments.csv", b"username,likes\nneha,4\n")


def test_rejects_non_utf8_csv() -> None:
    with pytest.raises(CommentImportError, match="UTF-8"):
        parse_comments_csv("comments.csv", BytesIO(b"text\n\xff\n").read())
