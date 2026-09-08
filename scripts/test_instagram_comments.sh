#!/usr/bin/env bash
set -euo pipefail

# Replace only the value below. Do not commit this file with a real token.
IG_ACCESS_TOKEN="IGAATwoTiZBPdlBZAFlhc3JTbTE4VWFYZAElybE40ZAmxZAR2tNUUMtRWJNZAWUzek8yLWNWdnVlNEV1bzREcnNWTGhYUnVnbDRmSURfaGkzU1BIMVdOS011ZAGQzcEsxNVl1WF9obUJrRDZAPWS0zZAHladXBXNFlEWkZAHaDJJZAWRuOVVSQQZDZD"
IG_USER_ID="27882873984745351"
API_VERSION="v26.0"

if [[ "$IG_ACCESS_TOKEN" == "PASTE_GENERATED_TOKEN_HERE" || -z "$IG_ACCESS_TOKEN" ]]; then
  echo "Edit IG_ACCESS_TOKEN at the top of this script first."
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required. Install it with: brew install jq"
  exit 1
fi

base_url="https://graph.instagram.com/$API_VERSION"
media_json="$(mktemp)"
trap 'rm -f "$media_json"' EXIT

echo "Fetching media from Instagram..."
curl -fsS -G "$base_url/$IG_USER_ID/media" \
  -H "Authorization: Bearer $IG_ACCESS_TOKEN" \
  --data-urlencode "fields=id,media_type,username,comments_count" \
  --data-urlencode "limit=100" \
  > "$media_json"

echo "Media with comments_count greater than zero:"
jq -r '.data[] | select((.comments_count // 0) > 0) | [.id, .media_type, (.comments_count | tostring)] | @tsv' "$media_json" \
  | while IFS=$'\t' read -r media_id media_type comments_count; do
      echo
      echo "Media: $media_id | Type: $media_type | Reported comments: $comments_count"
      echo "Comments response:"
      curl -fsS -G "$base_url/$media_id/comments" \
        -H "Authorization: Bearer $IG_ACCESS_TOKEN" \
        --data-urlencode "fields=id,text" \
        --data-urlencode "limit=100" \
        | jq '{returned_rows: (.data | length), data: .data}'
    done
